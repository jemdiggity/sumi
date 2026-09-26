"""User-facing workspace launcher, preferences, and skill installation."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime

TOOLS = Path(__file__).resolve().parent.parent
MUXES = ['zellij', 'tmux', 'cmux', 'cmux-app']


def user_dir():
    return Path(os.environ.get('SUMI_HOME', Path.home() / '.sumi')).expanduser()


def preferences():
    path = user_dir() / 'config.json'
    value = json.loads(path.read_text()) if path.exists() else {'mux': 'zellij'}
    if not isinstance(value, dict) or value.get('mux', 'zellij') not in MUXES:
        raise ValueError(f'Invalid mux preference in {path}')
    overrides = value.get('executables', {})
    if not isinstance(overrides, dict) or any(not isinstance(p, str) for p in overrides.values()):
        raise ValueError(f'executables in {path} must map mux names to paths')
    return value


def project_root(root=None):
    if root:
        path = root.expanduser().resolve()
    else:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
        path = Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()
    if not path.is_dir():
        raise ValueError(f'Project directory does not exist: {path}')
    return path


def session_name(root, mux):
    # Preserve the existing Sumi lab session; other projects never share a server.
    if root == TOOLS and mux == 'zellij':
        return 'sumi-zellij'
    slug = re.sub(r'[^a-zA-Z0-9_-]', '-', root.name)[:24] or 'project'
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:8]
    return f'sumi-{slug}-{digest}-{mux}'


def add_commands(sub):
    sub.add_parser('open', help='Open or reattach to the project workspace (default command)')
    p = sub.add_parser('config', help='Show preferences or save a default mux in ~/.sumi')
    p.add_argument('--mux', choices=MUXES, dest='preferred_mux')
    p = sub.add_parser('skills', help='Install/list bundled skills for Codex and Claude')
    p.add_argument('operation', choices=['install', 'list'], nargs='?', default='list')
    p.add_argument('--agent', choices=['codex', 'claude', 'all'], default='all')
    p.add_argument('--scope', choices=['user', 'project'], default='user')
    p = sub.add_parser('install', help='Put a sumi symlink in ~/.local/bin (no shell edits)')
    p.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')


def link(source, target):
    if target.is_symlink() and target.resolve() == source.resolve():
        return 'linked'
    if target.exists() or target.is_symlink():
        raise ValueError(f'Will not overwrite {target}; move it aside before installing')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source.resolve(), target_is_directory=source.is_dir())
    return 'installed'


def skill_paths(agent, scope, root):
    base = root if scope == 'project' else Path.home()
    return base / ('.agents/skills' if agent == 'codex' else '.claude/skills')


def same_skill(left, right):
    def files(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return left.is_dir() and files(left) == files(right)


def skills(args):
    root = project_root(args.root)
    agents = ['codex', 'claude'] if args.agent == 'all' else [args.agent]
    pending = []
    for agent in agents:
        for source in sorted((TOOLS / 'skills').iterdir()):
            if not (source / 'SKILL.md').is_file():
                continue
            dest = skill_paths(agent, args.scope, root) / source.name
            pending.append((agent, source, dest))
    legacy = []
    if args.scope == 'user' and 'codex' in agents:
        for agent, source, dest in pending:
            old = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills' / source.name
            if agent == 'codex' and old.exists() and old.resolve() != dest.resolve():
                if args.operation == 'install' and not same_skill(old, source):
                    raise ValueError(f'Legacy skill differs from Sumi: {old}; preserved. Reconcile it before installing.')
                legacy.append(old)
    # Preflight the entire install, so a collision never leaves a partial install.
    if args.operation == 'install':
        for _, source, dest in pending:
            if (dest.exists() or dest.is_symlink()) and not (
                    dest.is_symlink() and dest.resolve() == source.resolve()):
                raise ValueError(f'Skill already exists: {dest}; preserved. Move it aside to use the Sumi version.')
    if args.operation == 'install' and legacy:
        backup = user_dir() / 'skill-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True)
        for old in legacy:
            shutil.move(str(old), str(backup / old.name))
        print(f'Moved identical legacy Codex copies to {backup} to avoid duplicate skills.')
    for agent, source, dest in pending:
        state = link(source, dest) if args.operation == 'install' else (
            'linked' if dest.is_symlink() and dest.resolve() == source.resolve() else
            'existing' if dest.exists() else 'not installed')
        print(f'{agent}: {source.name}: {state} ({dest})')
    if args.operation == 'install':
        print('Skills are linked to this checkout; changes stay in sync. Start a new agent session to discover them.')


def handle(args):
    from sumi_runner import atomic_json, lease
    if args.action == 'skills':
        skills(args)
    elif args.action == 'install':
        dest = args.bin_dir.expanduser() / 'sumi'
        print(f'{link(TOOLS / "bin/sumi", dest)}: {dest}')
        if str(dest.parent) not in os.environ.get('PATH', '').split(os.pathsep):
            print(f'Add {dest.parent} to PATH to run sumi from any directory.')
    elif args.action == 'config':
        config = preferences()
        if args.preferred_mux:
            config['mux'] = args.preferred_mux
            atomic_json(user_dir() / 'config.json', config)
        print(json.dumps(config, indent=2))
    elif args.action in (None, 'open'):
        from sumi_workspace import launch
        config = preferences()
        mux = args.mux or config.get('mux', 'zellij')
        root = project_root(args.root)
        session = args.session or session_name(root, mux)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', session):
            raise ValueError('Session names may contain letters, digits, hyphens and underscores')
        user_dir().mkdir(parents=True, exist_ok=True)
        with lease(user_dir() / (session + '.lock')):
            attach = launch(root, mux, session, config, args.detach)
            config['mux'] = mux
            atomic_json(user_dir() / 'config.json', config)
        if attach and not args.detach:
            os.execvpe(attach[0], attach, os.environ)
        print(f'Sumi workspace ready: {session} ({mux})')
    else:
        return False
    return True
