"""Layout adapters. Shared pane programs own content; multiplexers own geometry."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

from sumi_cli import TOOLS, user_dir


def run(args, check=True):
    result = subprocess.run([str(a) for a in args], text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'Failed: {args[0]}')
    return result


def executable(mux, config):
    overrides = config.get('executables', {})
    candidate = overrides.get(mux)
    if not candidate:
        if mux == 'cmux-app':
            candidate = next((str(p) for p in [
                Path('/Applications/cmux.app/Contents/Resources/bin/cmux'),
                Path.home() / 'Applications/cmux.app/Contents/Resources/bin/cmux'] if p.is_file()), None)
        elif mux == 'cmux':
            candidates = [shutil.which('cmux-tui'), shutil.which('cmux'),
                          str(TOOLS / '.playground/cmux/bin/cmux'),
                          '/Applications/cmux.app/Contents/Resources/bin/cmux-tui',
                          str(Path.home() / 'Applications/cmux.app/Contents/Resources/bin/cmux-tui')]
            candidate = next((p for p in candidates if p and os.access(p, os.X_OK)
                              and 'resource client' in run([p, '--help'], check=False).stdout), None)
        else:
            candidate = shutil.which(mux)
    if not candidate or not os.access(candidate, os.X_OK):
        raise ValueError(f'{mux} is not installed. Install it or set executables.{mux} in ~/.sumi/config.json.')
    if mux == 'cmux' and 'resource client' not in run([candidate, '--help']).stdout:
        raise ValueError('This cmux executable is the macOS app CLI. Use --mux cmux-app, or set executables.cmux to the cmux TUI binary.')
    return candidate


def pane_command(root, mux, session, role):
    return ['/usr/bin/env', f'SUMI_ROOT={root}', f'SUMI_MUX={mux}', f'SUMI_SESSION={session}',
            sys.executable, str(TOOLS / 'bin/sumi-pane'), role]


def zellij_layout(root, session):
    q = lambda value: json.dumps(str(value))
    def pane(name, role, options=''):
        cmd = pane_command(root, 'zellij', session, role)
        return f'pane name={q(name)} {options} command={q(cmd[0])} {{ args {" ".join(map(q, cmd[1:]))}; }}'
    return f'''layout {{
 cwd {q(root)}
 new_tab_template {{
  pane
  pane size=1 borderless=true {{ plugin location="zellij:compact-bar"; }}
 }}
 pane split_direction="vertical" {{
  pane size="17%" {{
   {pane('Tasks', 'tasks', 'size="65%"')}
   {pane('Agent sessions', 'sessions', 'size="35%"')}
  }}
  {pane('Agent / shell', 'shell', 'size="43%" focus=true')}
  pane size="40%" {{
   pane stacked=true size="60%" {{
    {pane('Markdown', 'markdown')}
    {pane('Diff', 'diff')}
    {pane('Terminal / nvim', 'terminal', 'expanded=true')}
   }}
   {pane('CPU', 'cpu', 'size="18%"')}
   {pane('Weekly allowance remaining', 'usage', 'size="22%"')}
  }}
 }}
 pane size=1 borderless=true {{ plugin location="zellij:compact-bar"; }}
}}
'''


def start_zellij(binary, root, session):
    base = [binary, '--config', str(TOOLS / 'config/zellij.kdl')]
    sessions = run([binary, 'list-sessions', '--short', '--no-formatting'], check=False)
    if session not in sessions.stdout.splitlines():
        layout = user_dir() / 'workspaces' / session / 'layout.kdl'
        layout.parent.mkdir(parents=True, exist_ok=True)
        layout.write_text(zellij_layout(root, session))
        run([*base, 'attach', '--create-background', session])
        try:
            for _ in range(50):
                result = run([*base, '--session', session, 'action', 'list-panes', '--json'], check=False)
                if result.returncode == 0 and json.loads(result.stdout or '[]'):
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('Zellij did not become ready')
            run([*base, '--session', session, 'action', 'override-layout', str(layout)])
        except Exception:
            run([binary, 'kill-session', session], check=False)
            raise
    return [*base, 'attach', session]


def start_tmux(binary, root, session):
    base = [binary, '-L', session]
    if run([*base, 'has-session', '-t', session], check=False).returncode == 0:
        return [*base, 'attach-session', '-t', session]
    def call(*args):
        return run([*base, *args]).stdout.strip()
    def command(role):
        return shlex.join(pane_command(root, 'tmux', session, role))
    main = call('-f', '/dev/null', 'new-session', '-d', '-s', session, '-n', 'Sumi',
                '-x', '180', '-y', '50', '-c', root, '-P', '-F', '#{pane_id}', command('shell'))
    try:
        call('set-option', '-g', 'remain-on-exit', 'on')
        call('set-option', '-g', 'mouse', 'on')
        call('set-option', '-g', 'prefix', 'C-g')
        call('bind-key', 'C-g', 'send-prefix')
        call('set-option', '-s', 'extended-keys', 'always')
        call('set-option', '-s', 'extended-keys-format', 'csi-u')
        call('set-option', '-s', 'terminal-features[10]', 'xterm-ghostty:extkeys')
        call('bind-key', '-n', 'S-Enter', 'send-keys', '-H', '1b', '5b', '31', '33', '3b', '32', '75')
        call('set-option', '-g', 'pane-border-status', 'top')
        call('set-option', '-g', 'pane-border-format', ' #{pane_title} ')
        def split(target, direction, percent, role, before=False):
            return call('split-window', direction, *(['-b'] if before else []), '-d', '-t', target,
                        '-l', f'{percent}%', '-c', root, '-P', '-F', '#{pane_id}', command(role))
        tasks = split(main, '-h', 17, 'tasks', True)
        artifacts = split(main, '-h', 48, 'open')
        sessions = split(tasks, '-v', 35, 'sessions')
        cpu = split(artifacts, '-v', 40, 'cpu')
        usage = split(cpu, '-v', 55, 'usage')
        for pane, title in [(main, 'Agent / shell'), (tasks, 'Tasks'), (sessions, 'Agent sessions'),
                            (artifacts, 'Artifacts · F1/F2/F3'), (cpu, 'CPU'), (usage, 'Weekly allowance')]:
            call('select-pane', '-t', pane, '-T', title)
        call('select-pane', '-t', main)
    except Exception:
        run([*base, 'kill-session', '-t', session], check=False)
        raise
    return [*base, 'attach-session', '-t', session]


def start_cmux(binary, root, session):
    base = [binary, '--session', session]
    run([*base, 'server', 'ensure'])
    def api(*args):
        data = json.loads(run([*base, '--json', *args]).stdout)
        return data.get('value', data) if isinstance(data, dict) else data
    existing = next((w for w in api('workspace', 'list') if w['name'] == session), None)
    if existing:
        api('workspace', existing['id'], 'focus')
        return [*base, 'attach']
    first = api('workspace', 'create', '--name', session)
    workspace = first['workspace_id']
    try:
        def split(seed, direction, ratio):
            return api('pane', seed['pane_id'], 'split', direction, '--ratio', str(ratio))
        main = split(first, '--right', .17)
        artifacts = split(main, '--right', 43 / 83)
        sessions = split(first, '--down', .65)
        cpu = split(artifacts, '--down', .60)
        usage = split(cpu, '--down', .45)
        for seed, title, roles in [
                (first, 'Tasks', [('Tasks', 'tasks')]),
                (main, 'Agent / shell', [('Agent / shell', 'shell')]),
                (sessions, 'Agent sessions', [('Agent sessions', 'sessions')]),
                (artifacts, 'Artifacts', [('Markdown', 'markdown'), ('Diff', 'diff'), ('Terminal', 'terminal')]),
                (cpu, 'CPU', [('CPU', 'cpu')]), (usage, 'Weekly allowance', [('Weekly allowance', 'usage')])]:
            api('pane', seed['pane_id'], 'rename', '--name', title)
            for name, role in roles:
                tab = api('pane', seed['pane_id'], 'run', '--on-exit', 'keep', '--',
                          *pane_command(root, 'cmux', session, role))
                api('tab', tab['tab_id'], 'rename', '--name', name)
            api('tab', seed['tab_id'], 'close')
        api('pane', main['pane_id'], 'focus')
    except Exception:
        run([*base, 'workspace', workspace, 'close'], check=False)
        raise
    return [*base, 'attach']


def native_layout(root, session):
    def pane(*roles):
        return {'pane': {'surfaces': [dict(type='terminal', name=name, cwd=str(root),
            command=shlex.join(pane_command(root, 'cmux-app', session, role)),
            focus=role == 'shell') for name, role in roles]}}
    def split(direction, ratio, a, b):
        return dict(direction=direction, split=ratio, children=[a, b])
    left = split('vertical', .65, pane(('Tasks', 'tasks')), pane(('Agent sessions', 'sessions')))
    right = split('vertical', .60, pane(('Markdown', 'markdown'), ('Diff', 'diff'), ('Terminal', 'terminal')),
                  split('vertical', .45, pane(('CPU', 'cpu')), pane(('Weekly allowance', 'usage'))))
    return split('horizontal', .17, left,
                 split('horizontal', 43 / 83, pane(('Agent / shell', 'shell')), right))


def start_native(binary, root, session, detach):
    if sys.platform != 'darwin':
        raise ValueError('cmux-app requires macOS')
    run(['open', *(['-g'] if detach else []), '-a', 'cmux'])
    for _ in range(50):
        response = run([binary, '--json', 'list-workspaces'], check=False)
        if response.returncode == 0:
            break
        if 'Access denied' in response.stderr or 'Access denied' in response.stdout:
            raise RuntimeError('cmux restricts socket access to its own terminals. Run sumi inside cmux, or enable local automation in cmux Settings. No access setting was changed.')
        time.sleep(.1)
    else:
        raise RuntimeError('cmux app did not become available; enable its CLI/socket access in Settings')
    data = json.loads(response.stdout)
    workspaces = data.get('workspaces', []) if isinstance(data, dict) else data
    existing = next((w for w in workspaces if w.get('title', w.get('name')) == session), None)
    if existing:
        if not detach:
            run([binary, 'select-workspace', '--workspace', existing.get('id', existing.get('ref'))])
    else:
        run([binary, '--json', 'new-workspace', '--name', session, '--cwd', root,
             '--focus', 'false' if detach else 'true',
             '--layout', json.dumps(native_layout(root, session))])
    return None


def launch(root, mux, session, config, detach):
    binary = executable(mux, config)
    if mux == 'tmux' and not shutil.which('tmux'):
        raise ValueError('tmux is required for the artifact tabs')
    from sumi_runner import atomic_json
    task_file = root / '.sumi/tasks.json'
    if not task_file.exists():
        legacy = root / 'tasks.json'
        if legacy.exists():
            raise ValueError(f'Move {legacy} to {task_file} before launching')
        atomic_json(task_file, [])
    os.environ.update(SUMI_ROOT=str(root), SUMI_MUX=mux, SUMI_SESSION=session)
    for key in ('ZELLIJ', 'ZELLIJ_SESSION_NAME', 'TMUX'):
        os.environ.pop(key, None)
    if mux == 'zellij':
        return start_zellij(binary, root, session)
    if mux == 'tmux':
        return start_tmux(binary, root, session)
    if mux == 'cmux':
        return start_cmux(binary, root, session)
    return start_native(binary, root, session, detach)
