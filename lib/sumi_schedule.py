"""Local interval scheduler; no agent, shell, or multiplexer dependency."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

from sumi_runner import atomic_json


ACTIVE = {'starting', 'running'}
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')


def interval(value):
    match = re.fullmatch(r'([1-9][0-9]*)([smhd])', value)
    if not match:
        raise ValueError('Interval must be a positive integer followed by s, m, h, or d')
    seconds = int(match[1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[match[2]]
    if seconds > 315360000:
        raise ValueError('Interval must not exceed ten years')
    return seconds


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


@contextmanager
def lock(path, blocking=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            raise RuntimeError(f'Scheduler is busy ({path.name})') from None
        yield


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Scheduler:
    def __init__(self, root, clock=time.time):
        self.root = Path(root).resolve()
        self.definitions = self.root / '.sumi/schedules.json'
        self.runtime = self.root / '.sumi/schedule-runs'
        self.clock = clock

    def config_lock(self):
        return lock(self.runtime / 'config.lock', blocking=True)

    def load(self):
        values = json.loads(self.definitions.read_text()) if self.definitions.exists() else []
        if not isinstance(values, list):
            raise ValueError(f'Invalid schedule definitions: {self.definitions}')
        seen = set()
        for item in values:
            try:
                valid = (isinstance(item, dict) and isinstance(item['id'], str)
                         and NAME.fullmatch(item['id']) and item['id'] not in seen
                         and isinstance(item['generation'], str)
                         and re.fullmatch(r'[a-f0-9]{32}', item['generation'])
                         and isinstance(item['enabled'], bool)
                         and isinstance(item['anchor'], (int, float))
                         and math.isfinite(item['anchor']) and 0 <= item['anchor'] < 1e11
                         and isinstance(item['every'], str)
                         and interval(item['every'])
                         and isinstance(item['command'], list) and item['command']
                         and all(isinstance(s, str) and '\0' not in s for s in item['command'])
                         and item['command'][0])
            except (KeyError, TypeError, ValueError, OverflowError):
                valid = False
            if not valid:
                raise ValueError(f'Invalid schedule definitions: {self.definitions}; file preserved')
            seen.add(item['id'])
        return values

    def records(self):
        result = []
        for path in sorted(self.runtime.glob('*/run.json')):
            try:
                record = json.loads(path.read_text())
                if (record['state'] not in ACTIVE | {'succeeded', 'failed', 'interrupted'}
                        or record['run_id'] != path.parent.name
                        or not isinstance(record['started'], (int, float))):
                    raise ValueError('Invalid run record')
                result.append(record)
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f'Cannot read run record {path}; preserve it for recovery') from error
        return result

    def save_run(self, record):
        atomic_json(self.runtime / record['run_id'] / 'run.json', record)

    def reconcile(self):
        # Caller owns execution.lock: no live Sumi launcher can race this check.
        for record in self.records():
            if record['state'] not in ACTIVE:
                continue
            pgid = record.get('pgid')
            if pgid is None or group_alive(pgid):
                raise RuntimeError(
                    f'Run {record["run_id"]} needs recovery: '
                    f'{"launch ownership is uncertain" if pgid is None else "process group " + str(pgid) + " still exists"}. '
                    f'Inspect {self.runtime / record["run_id"]}. Stop any surviving command; '
                    'if launch ownership is uncertain, verify it is stopped before manually '
                    'marking run.json interrupted with an ended timestamp. No new run was launched.')
            record.update(state='interrupted', ended=self.clock(), exit_code=None,
                          error='Launcher exited before recording completion')
            self.save_run(record)

    @staticmethod
    def latest(item, records):
        runs = [r for r in records if r['generation'] == item['generation']]
        return max(runs, key=lambda r: (r['started'], r['run_id']), default=None)

    def due_at(self, item, records):
        latest = self.latest(item, records)
        ended = latest.get('ended') if latest else None
        return max(item['anchor'], ended or item['anchor']) + interval(item['every'])

    def edit(self, operation, name, every=None, command=None):
        if not NAME.fullmatch(name):
            raise ValueError('Schedule ID must use 1–64 letters, digits, underscores, or hyphens; start with a letter or digit')
        with self.config_lock():
            items = self.load()
            item = next((i for i in items if i['id'] == name), None)
            if operation == 'add':
                if item:
                    raise ValueError(f'Schedule already exists: {name}')
                interval(every)
                if not command or not command[0] or any('\0' in arg for arg in command):
                    raise ValueError('Provide a command after --')
                item = dict(id=name, generation=uuid.uuid4().hex, every=every,
                            command=command, enabled=True, anchor=self.clock())
                items.append(item)
            else:
                if item is None:
                    raise ValueError(f'Unknown schedule: {name}')
                if operation == 'remove':
                    if any(r['generation'] == item['generation'] and r['state'] in ACTIVE
                           for r in self.records()):
                        raise ValueError('Cannot remove a running or unreconciled schedule; run serve to reconcile it first')
                    items.remove(item)
                else:
                    item['enabled'] = operation == 'resume'
                    if item['enabled']:
                        item['anchor'] = self.clock()
            atomic_json(self.definitions, items)
            return item

    def listing(self):
        with self.config_lock():
            records = self.records()
            return [dict(id=i['id'], enabled=i['enabled'], every=i['every'],
                         command=i['command'], next_due=stamp(self.due_at(i, records)) if i['enabled'] else None,
                         running=bool(self.latest(i, records) and self.latest(i, records)['state'] in ACTIVE),
                         last_result=self.latest(i, records)) for i in self.load()]

    def run(self, name=None):
        with lock(self.runtime / 'execution.lock'):
            self.reconcile()
            proc = None
            record = None
            try:
                with self.config_lock():
                    items, records = self.load(), self.records()
                    if name is not None:
                        item = next((i for i in items if i['id'] == name), None)
                        if item is None:
                            raise ValueError(f'Unknown schedule: {name}')
                    else:
                        due = [i for i in items if i['enabled'] and self.due_at(i, records) <= self.clock()]
                        item = min(due, key=lambda i: (self.due_at(i, records), i['id']), default=None)
                        if item is None:
                            return None
                    run_id = uuid.uuid4().hex
                    directory = self.runtime / run_id
                    directory.mkdir(parents=True)
                    record = dict(run_id=run_id, schedule_id=item['id'], generation=item['generation'],
                                  command=item['command'], project=str(self.root), started=self.clock(),
                                  ended=None, state='starting', exit_code=None, pgid=None,
                                  stdout=str(directory / 'stdout.log'), stderr=str(directory / 'stderr.log'))
                    self.save_run(record)  # Persist intent before spawning; ambiguity fails closed.
                    with open(record['stdout'], 'wb') as out, open(record['stderr'], 'wb') as err:
                        proc = subprocess.Popen(item['command'], cwd=self.root, stdin=subprocess.DEVNULL,
                                                stdout=out, stderr=err, start_new_session=True)
                    record.update(state='running', pgid=proc.pid)
                    self.save_run(record)
                code = proc.wait()
                # A command must not leave background descendants modifying this project.
                self.stop_group(proc)
                record.update(state='succeeded' if code == 0 else 'failed', exit_code=code)
            except KeyboardInterrupt:
                if proc is not None:
                    self.stop_group(proc)
                if record is not None:
                    if proc is None and record['state'] == 'starting':
                        raise  # Preserve uncertain launch intent for explicit recovery.
                    record.update(state='interrupted', exit_code=proc.returncode)
                    record['ended'] = self.clock()
                    self.save_run(record)
                raise
            except OSError as error:
                if record is None:
                    raise
                if proc is not None:
                    self.stop_group(proc)
                record.update(state='failed', exit_code=None, error=str(error))
            finally:
                if proc is not None and proc.poll() is None:
                    self.stop_group(proc)
            record['ended'] = self.clock()
            self.save_run(record)
            return record

    @staticmethod
    def stop_group(proc):
        if not group_alive(proc.pid):
            proc.wait()
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                proc.poll()
                if not group_alive(proc.pid):
                    break
                time.sleep(.05)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # Delivery of SIGKILL is not proof that every descendant has exited.
        # Keep the durable run active if ownership cannot safely be released.
        deadline = time.monotonic() + 2
        while group_alive(proc.pid) and time.monotonic() < deadline:
            proc.poll()
            time.sleep(.05)
        if group_alive(proc.pid):
            raise RuntimeError(f'Process group {proc.pid} survived cleanup; run requires recovery. '
                               'Inspect the run logs and stop surviving processes before retrying.')
        proc.wait()

    def serve(self):
        with lock(self.runtime / 'serve.lock'):
            print(f'Scheduling commands in {self.root}. Ctrl+C to stop.', flush=True)
            while True:
                try:
                    record = self.run()
                except RuntimeError as error:
                    if str(error) != 'Scheduler is busy (execution.lock)':
                        raise
                    record = None
                if record:
                    print(json.dumps(record), flush=True)
                else:
                    time.sleep(.5)


def add_commands(sub):
    parser = sub.add_parser('schedule', help='Schedule local noninteractive commands')
    actions = parser.add_subparsers(dest='schedule_action', required=True)
    p = actions.add_parser('add')
    # Keep options before the -- command separator; argparse REMAINDER would
    # swallow --every after the ID, so parse the command separately in main.
    p.add_argument('schedule_id')
    p.add_argument('--every', required=True)
    for action in ('pause', 'resume', 'remove', 'run'):
        p = actions.add_parser(action)
        p.add_argument('schedule_id')
    actions.add_parser('list')
    actions.add_parser('serve')
    p = actions.add_parser('runs')
    p.add_argument('schedule_id', nargs='?')


def handle(args):
    from sumi_cli import project_root
    scheduler = Scheduler(project_root(args.root))
    action = args.schedule_action
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    try:
        if action in ('add', 'pause', 'resume', 'remove'):
            result = scheduler.edit(action, args.schedule_id, getattr(args, 'every', None),
                                    getattr(args, 'schedule_command', None))
        elif action == 'list':
            result = scheduler.listing()
        elif action == 'runs':
            result = sorted((r for r in scheduler.records() if not args.schedule_id or
                             r['schedule_id'] == args.schedule_id), key=lambda r: r['started'], reverse=True)[:20]
        elif action == 'run':
            result = scheduler.run(args.schedule_id)
            print(json.dumps(result, indent=2))
            raise SystemExit(0 if result['state'] == 'succeeded' else 1)
        else:
            scheduler.serve()
            return
        print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    finally:
        signal.signal(signal.SIGTERM, previous)
