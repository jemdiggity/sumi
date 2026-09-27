"""Local task/run control: Git owns files; agent and mux adapters provide execution and views."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from agent_activity import run_activity, pane_activity
from mux_adapters import Zellij, get_mux  # Zellij alias retained for existing integrations/tests


LIVE = {'starting', 'running'}
RESERVED = LIVE | {'preparing', 'prepared', 'orphaned'}


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def command(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'Command failed: {args[0]}')
    return result.stdout.strip()


@contextmanager
def lease(path):
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield stream


def leased(path):
    try:
        with lease(path):
            return False
    except BlockingIOError:
        return True


def task_index(tasks):
    index, ancestors = {}, {}
    def walk(nodes, parents):
        for task in nodes:
            key = task['id']
            if key in index:
                raise ValueError(f'Duplicate task ID: {key}')
            index[key], ancestors[key] = task, parents
            walk(task.get('children', []), parents + [key])
    walk(tasks, [])
    edges = {key: set(d for node in [key, *ancestors[key]]
                      for d in index[node].get('depends_on', [])) for key in index}
    visiting, visited = set(), set()
    def visit(key):
        if key not in index:
            raise ValueError(f'Missing dependency: {key}')
        if key in visiting:
            raise ValueError(f'Dependency cycle at {key}')
        if key in visited:
            return
        visiting.add(key)
        for dep in edges[key]:
            visit(dep)
        visiting.remove(key)
        visited.add(key)
    for key in index:
        visit(key)
    return index, ancestors, edges


class Factory:
    def __init__(self, root, session='sumi-zellij', mux='zellij'):
        self.root = Path(root).resolve()
        self.state = self.root / '.playground/runs'
        self.state.mkdir(parents=True, exist_ok=True)
        self.tasks = self.root / '.sumi/tasks.json'
        self.session = session
        self.mux = mux
        get_mux(mux, session)  # reject unavailable backends before reserving tasks
        self.executable = Path(__file__).resolve().parent.parent / 'bin/sumi'

    @contextmanager
    def lock(self):
        with (self.state / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def read(self, run_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
            raise ValueError('Invalid run ID')
        return json.loads((self.state / run_id / 'run.json').read_text())

    def records(self):
        return [json.loads(p.read_text()) for p in sorted(self.state.glob('*/run.json'))]

    def worktree_lock(self, run):
        key = hashlib.sha256(run['worktree'].encode()).hexdigest()[:24]
        return self.state / ('.worktree-' + key + '.lock')

    def save(self, run):
        run['updated_at'] = now()
        atomic_json(Path(run['directory']) / 'run.json', run)

    def eligible(self, task_id, allow_blocked=False):
        tasks = json.loads(self.tasks.read_text())
        index, ancestors, edges = task_index(tasks)
        task = index[task_id]
        if task.get('children'):
            raise ValueError('Launch leaf tasks, not groups')
        if task['status'] not in ({'ready', 'proposed', 'blocked'} if allow_blocked else {'ready', 'proposed'}):
            raise ValueError(f'{task_id} is {task["status"]}, not ready to launch')
        for parent in ancestors[task_id]:
            if index[parent]['status'] in ('blocked', 'done', 'superseded'):
                raise ValueError(f'Ancestor {parent} is {index[parent]["status"]}')
        for dep in edges[task_id]:
            if index[dep]['status'] != 'done':
                raise ValueError(f'Unfinished dependency: {dep}')
        if not task.get('acceptance'):
            raise ValueError('Task needs concrete acceptance criteria')
        return task

    def task_run_state(self, run):
        """Project run state to the canonical queue while holding the shared lock."""
        tasks = json.loads(self.tasks.read_text())
        index, _, _ = task_index(tasks)
        task = index[run['task_id']]
        if run['state'] in LIVE:
            task.update(status='active', active_run=run['id'])
            task.pop('blocked_reason', None)
        elif task.get('active_run') == run['id']:
            task.pop('active_run', None)
            task['status'] = 'blocked'
            task['blocked_reason'] = ('Run exited; awaiting review' if run['state'] == 'exited'
                                      else f'Run {run["state"]}; inspect {run["id"]}')
            task['last_run'] = run['id']
        atomic_json(self.tasks, tasks)

    def prepare(self, task_id, previous=None, followup=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
            raise ValueError('Task IDs must contain only letters, digits, hyphens, underscores')
        with self.lock():
            task = self.eligible(task_id, allow_blocked=previous is not None)
            if any(r['task_id'] == task_id and r['state'] in RESERVED for r in self.records()):
                raise ValueError(f'{task_id} already has a prepared or live run')
            if previous and (previous['state'] in RESERVED or not previous.get('session_id')):
                raise ValueError('Resume requires a finished run with a captured Codex session ID')
            if previous and leased(self.worktree_lock(previous)):
                raise ValueError('Previous worker still owns this worktree')
            run_id = task_id + '-' + uuid.uuid4().hex[:8]
            directory = self.state / run_id
            directory.mkdir()
            base = command(['git', 'rev-parse', 'HEAD'], self.root)
            worktree = self.root / '.playground/worktrees' / run_id
            branch = 'sumi/' + run_id
            if previous:
                worktree, branch, base = Path(previous['worktree']), previous['branch'], previous['base']
            run = dict(id=run_id, task_id=task_id, task=task, agent='codex', root=str(self.root),
                       directory=str(directory), worktree=str(worktree), branch=branch, base=base,
                       state='preparing', created_at=now(), workspace_session=self.session, workspace_mux=self.mux)
            if previous:
                run.update(previous_run=previous['id'], session_id=previous['session_id'])
            self.save(run)
            try:
                if not previous:
                    command(['git', 'worktree', 'add', '-b', branch, str(worktree), base], self.root)
                prompt = (f'Task {task_id}: {task["title"]}\n\nAcceptance:\n' +
                          '\n'.join('- ' + a for a in task['acceptance']) +
                          '\n\nWork only in this worktree and on this task. Do not change branches, merge, '
                          'push, launch other agents, or modify .sumi/tasks.json or shared orchestration state. '
                          'Other workers are running in separate worktrees. Leave changes uncommitted for '
                          'coordinator review. Report changed files, validation, and unresolved issues.\n')
                if followup:
                    prompt += '\nFollow-up:\n' + followup + '\n'
                (directory / 'prompt.md').write_text(prompt)
                run['state'] = 'prepared'
            except Exception as error:
                run.update(state='failed', error=str(error))
                self.save(run)
                raise
            self.save(run)
            return run

    def start(self, run_id):
        # Commit intent under the lock, then release before the spawned worker needs it.
        with self.lock():
            run = self.read(run_id)
            if run['state'] != 'prepared':
                raise ValueError(f'Run is {run["state"]}; start only accepts prepared runs')
            self.eligible(run['task_id'], allow_blocked='previous_run' in run)
            run.update(state='starting', started_at=now())
            self.save(run)
            self.task_run_state(run)
        try:
            tab = get_mux(run.get('workspace_mux', 'zellij'), run['workspace_session']).open(run, self.executable)
        except Exception as error:
            with self.lock():
                run = self.read(run_id)
                # An uncertain launch must not overwrite a worker that already claimed it.
                if run['state'] == 'starting':
                    run.update(state='failed', error=str(error))
                    self.save(run)
                    self.task_run_state(run)
            raise
        with self.lock():
            run = self.read(run_id)
            run['workspace_id'] = tab
            self.save(run)
        return run

    def reconcile(self, run_id):
        with self.lock():
            run = self.read(run_id)
            if run['state'] in LIVE | {'orphaned'}:
                if not leased(Path(run['directory']) / 'worker.lock'):
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(run['started_at'])).total_seconds()
                    if run['state'] != 'starting' or age > 30:
                        busy = leased(self.worktree_lock(run))
                        run.update(state='orphaned' if busy else 'interrupted',
                                   error='Worker supervisor lost; worktree still busy' if busy else
                                   'No worker lease; process exited without a final record')
                        self.save(run)
            self.task_run_state(run)
            return run

    def worker(self, run_id):
        run = self.read(run_id)
        with lease(Path(run['directory']) / 'worker.lock'), lease(self.worktree_lock(run)) as worktree_lease:
            with self.lock():
                run = self.read(run_id)
                if run['state'] != 'starting':
                    raise ValueError('Run has already been claimed; use resume for another attempt')
                binary = shutil.which('codex')
                if not binary:
                    run.update(state='failed', error='codex not found on PATH')
                    self.save(run)
                    self.task_run_state(run)
                    return 1
                args = [binary, '-a', 'never', 'exec', '-s', 'workspace-write', '--json']
                if run.get('previous_run'):
                    args += ['resume', run['session_id']]
                args += ['-']
                run.update(state='running', pid=os.getpid(), command=args)
                self.save(run)
                self.task_run_state(run)
            print(f'{run_id}\nWorktree: {run["worktree"]}\nStarting Codex…', flush=True)
            directory = Path(run['directory'])
            env = dict(os.environ)
            for key in ('ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE'):
                env.pop(key, None)
            proc = None
            interrupted = False
            def stop(signum, frame):
                nonlocal interrupted
                interrupted = True
                if proc and proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
            old_handlers = {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
            code, error = 1, None
            try:
                with (directory / 'prompt.md').open() as prompt, (directory / 'stderr.log').open('w') as errors, (directory / 'events.jsonl').open('w') as events:
                    proc = subprocess.Popen(args, cwd=run['worktree'], env=env, stdin=prompt,
                                            stdout=subprocess.PIPE, stderr=errors, text=True,
                                            start_new_session=True, pass_fds=(worktree_lease.fileno(),))
                    for line in proc.stdout:
                        events.write(line)
                        events.flush()
                        try:
                            event = json.loads(line)
                        except ValueError:
                            print(line.rstrip(), flush=True)
                            continue
                        if event.get('type') == 'thread.started':
                            with self.lock():
                                current = self.read(run_id)
                                current['session_id'] = event['thread_id']
                                self.save(current)
                        item = event.get('item', {})
                        if item.get('type') == 'agent_message' and event.get('type') == 'item.completed':
                            print(item.get('text', ''), flush=True)
                            (directory / 'result.md').write_text(item.get('text', '') + '\n')
                        elif item.get('type') == 'command_execution' and event.get('type') == 'item.started':
                            print('> ' + item.get('command', ''), flush=True)
                        elif event.get('type') in ('error', 'turn.failed'):
                            print(json.dumps(event), flush=True)
                    code = proc.wait()
            except Exception as exc:
                error = str(exc)
                if proc and proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            finally:
                for s, handler in old_handlers.items():
                    signal.signal(s, handler)
                with self.lock():
                    run = self.read(run_id)
                    run.update(state='interrupted' if interrupted else ('exited' if code == 0 else 'failed'),
                               exit_code=code, finished_at=now())
                    if error:
                        run['error'] = error
                    self.save(run)
                    self.task_run_state(run)
            print(f'\nRun {run["state"]} (exit {code}). Results await review.\n'
                  f'Inspect: {self.executable} inspect {run_id}', flush=True)
            return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, help='Canonical project checkout (auto-detected from Git)')
    parser.add_argument('--session')
    parser.add_argument('--mux', choices=['zellij', 'tmux', 'cmux', 'cmux-app'], help='Workspace UI (default: saved preference or zellij)')
    parser.add_argument('--detach', action='store_true', help='Create the workspace without attaching')
    sub = parser.add_subparsers(dest='action')
    from sumi_cli import add_commands, handle
    add_commands(sub)
    p = sub.add_parser('prepare', help='Reserve a task and create its worktree')
    p.add_argument('task_id')
    p.add_argument('--agent', choices=['codex'], default='codex')
    for name in ('start', 'inspect', 'focus', 'cancel', '_worker'):
        p = sub.add_parser(name)
        p.add_argument('run_id')
    sub.add_parser('runs', help='Reconcile and list recorded runs as JSON')
    for name in ('activity', 'tail'):
        p = sub.add_parser(name, help='Read managed agent activity and recent output')
        p.add_argument('run_id')
        p.add_argument('--lines', type=int, default=10)
        p.add_argument('--follow', action='store_true')
    p = sub.add_parser('peek', help='Capture any Zellij terminal; optional regex gives only a heuristic')
    p.add_argument('pane_id')
    p.add_argument('--lines', type=int, default=10)
    p.add_argument('--busy-regex', default='esc to interrupt',
                   help='Busy indicator (default: Codex esc-to-interrupt marker)')
    p.add_argument('--waiting-regex')
    p.add_argument('--follow', action='store_true')
    p = sub.add_parser('resume', help='Prepare a new attempt in the same worktree and Codex conversation')
    p.add_argument('run_id')
    p.add_argument('--prompt', required=True)
    p = sub.add_parser('task', help='Coordinator-only task outcome after review')
    p.add_argument('task_id')
    p.add_argument('--status', choices=['ready', 'blocked', 'done'], required=True)
    p.add_argument('--evidence', required=True)
    argv = sys.argv[1:]
    schedule_command = None
    # The command after -- belongs to the scheduled executable, not Sumi.
    if '--' in argv:
        split = argv.index('--')
        head = argv[:split]
        if 'schedule' in head and 'add' in head:
            schedule_command = argv[split + 1:]
            argv = head
    args = parser.parse_args(argv)
    if args.action == 'schedule':
        args.schedule_command = schedule_command
    try:
        if handle(args):
            return
        args.session = args.session or (os.environ.get('SUMI_SESSION')
                                       if os.environ.get('SUMI_MUX', 'zellij') == 'zellij' else None) or 'sumi-zellij'
        args.mux = args.mux or 'zellij'
        root = args.root or Path(command(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'])).parent
        factory = Factory(root, args.session, args.mux)
        if args.action in ('activity', 'tail', 'peek'):
            if args.lines < 1 or args.lines > 200:
                raise ValueError('--lines must be between 1 and 200')
            try:
                if args.action == 'peek' and args.follow:
                    # Zellij sends whole changed viewports; cropping is local.
                    from contextlib import closing
                    with closing(get_mux(args.mux, args.session).updates(args.pane_id)) as updates:
                        for event in updates:
                            if event.get('event') == 'pane_closed':
                                result = dict(pane_id=args.pane_id, activity='unknown',
                                              source='pane-closed', lines=[])
                            elif event.get('event') == 'pane_update':
                                result = pane_activity('\n'.join(event['viewport']),
                                                       args.lines, args.busy_regex,
                                                       args.waiting_regex)
                                result['pane_id'] = args.pane_id
                            else:
                                continue
                            if sys.stdout.isatty():
                                print('\033[H\033[2J', end='')
                            print(json.dumps(result), flush=True)
                    return
                while True:
                    if args.action == 'peek':
                        text = get_mux(args.mux, args.session).capture(args.pane_id)
                        result = pane_activity(text, args.lines, args.busy_regex, args.waiting_regex)
                        result['pane_id'] = args.pane_id
                    else:
                        result = run_activity(factory.reconcile(args.run_id), args.lines)
                    if args.follow and sys.stdout.isatty():
                        print('\033[H\033[2J', end='')
                    if args.action == 'tail':
                        print(f'{result["run_id"]}: {result["activity"]}\n' + '\n'.join(result['lines']), flush=True)
                    else:
                        print(json.dumps(result, indent=2), flush=True)
                    if not args.follow:
                        return
                    time.sleep(1)
            except KeyboardInterrupt:
                return
        elif args.action == 'prepare':
            result = factory.prepare(args.task_id)
        elif args.action == 'start':
            result = factory.start(args.run_id)
        elif args.action == '_worker':
            sys.exit(factory.worker(args.run_id))
        elif args.action == 'cancel':
            with factory.lock():
                result = factory.read(args.run_id)
                if result['state'] not in ('preparing', 'prepared'):
                    raise ValueError('Cancel only accepts unstarted preparations; it never kills a live worker')
                result.update(state='cancelled', finished_at=now())
                factory.save(result)
        elif args.action == 'resume':
            previous = factory.reconcile(args.run_id)
            result = factory.prepare(previous['task_id'], previous, args.prompt)
        elif args.action == 'runs':
            result = [factory.reconcile(r['id']) for r in factory.records()]
            for run in result:
                run['activity'] = run_activity(run, 1)['activity']
        elif args.action in ('inspect', 'focus'):
            result = factory.reconcile(args.run_id)
            try:
                tabs = get_mux(result.get('workspace_mux', 'zellij'), result['workspace_session']).workspaces()
            except (RuntimeError, OSError) as error:
                tabs = []
                result['workspace_error'] = str(error)
            matching = [t for t in tabs if t.get('name') == result['id']]
            result['workspace_present'] = bool(matching)
            if args.action == 'focus':
                if not matching:
                    raise ValueError('Workspace missing; files and run record remain. Use resume to prepare another attempt.')
                get_mux(result.get('workspace_mux', 'zellij'), result['workspace_session']).focus(matching[0]['id'])
            else:
                result['git_status'] = (command(['git', 'status', '--short'], result['worktree'])
                                        if Path(result['worktree']).exists() else 'Worktree missing')
                path = Path(result['directory']) / 'result.md'
                result['result'] = path.read_text() if path.exists() else None
        elif args.action == 'task':
            with factory.lock():
                if any(r['task_id'] == args.task_id and r['state'] in RESERVED for r in factory.records()):
                    raise ValueError('Task has a prepared or live run; review after it finishes')
                tasks = json.loads(factory.tasks.read_text())
                task = task_index(tasks)[0][args.task_id]
                task.update(status=args.status)
                task.pop('active_run', None)
                task.pop('blocked_reason', None)
                if args.status == 'blocked':
                    task['blocked_reason'] = args.evidence
                task.setdefault('evidence', []).append(args.evidence)
                atomic_json(factory.tasks, tasks)
                result = task
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        parser.exit(1, f'sumi: {error}\n')
