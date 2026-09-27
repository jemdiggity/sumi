import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import contextlib
import io
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import sumi_cli as cli
import sumi_workspace as workspace
from sumi_runner import atomic_json


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.environment = patch.dict(os.environ, {'SUMI_HOME': str(self.home / '.sumi')})
        self.environment.start()
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.environment.stop()
        self.temp.cleanup()

    def test_preferences_default_save_and_corruption(self):
        self.assertEqual(cli.preferences(), {'mux': 'zellij'})
        args = argparse.Namespace(action='config', preferred_mux='tmux')
        cli.handle(args)
        self.assertEqual(cli.preferences()['mux'], 'tmux')
        atomic_json(cli.user_dir() / 'config.json', {'mux': 'invalid'})
        with self.assertRaises(ValueError):
            cli.preferences()

    def test_default_launch_dispatch_and_remember_mux(self):
        args = argparse.Namespace(action=None, root=self.root, mux='cmux', session=None, detach=True)
        with patch('sumi_workspace.launch', return_value=['cmux', 'attach']) as launch:
            self.assertTrue(cli.handle(args))
            self.assertEqual(launch.call_args.args[:2], (self.root.resolve(), 'cmux'))
        args.mux = None
        with patch('sumi_workspace.launch', return_value=None) as launch:
            cli.handle(args)
            self.assertEqual(launch.call_args.args[1], 'cmux')
        self.assertNotEqual(cli.session_name(self.root / 'a', 'cmux'), cli.session_name(self.root / 'b', 'cmux'))
        args.mux = 'tmux'
        with patch('sumi_workspace.launch', side_effect=RuntimeError('missing tool')):
            with self.assertRaises(RuntimeError):
                cli.handle(args)
        self.assertEqual(cli.preferences()['mux'], 'cmux')

    @contextlib.contextmanager
    def skill_fixtures(self):
        tools = self.root / 'tools'
        sources = [tools / 'skills' / name for name in ['sample-one', 'sample-two']]
        for source in sources:
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text(f'# {source.name}\nTemporary test skill.\n')
        with patch.object(cli, 'TOOLS', tools), \
                patch('sumi_cli.Path.home', return_value=self.home), \
                patch.dict(os.environ, {'CODEX_HOME': str(self.home / '.codex')}):
            yield sources

    def test_skill_install_is_idempotent_and_preserves_conflicts(self):
        args = argparse.Namespace(operation='install', root=self.root, agent='all', scope='user')
        with self.skill_fixtures() as sources:
            cli.skills(args)
            cli.skills(args)
            for agent in ['codex', 'claude']:
                for source in sources:
                    dest = cli.skill_paths(agent, 'user', self.root) / source.name
                    self.assertTrue(dest.is_symlink())
                    self.assertEqual(dest.resolve(), source.resolve())
            conflict = self.home / '.claude/skills' / sources[0].name
            conflict.unlink()
            conflict.mkdir()
            (conflict / 'SKILL.md').write_text('Personal skill')
            with self.assertRaisesRegex(ValueError, 'Skill already exists:'):
                cli.skills(args)
            self.assertEqual((conflict / 'SKILL.md').read_text(), 'Personal skill')

    def test_project_skills_do_not_touch_user_scope(self):
        args = argparse.Namespace(operation='install', root=self.root, agent='codex', scope='project')
        with self.skill_fixtures() as sources:
            cli.skills(args)
            for source in sources:
                dest = self.root / '.agents/skills' / source.name
                self.assertTrue(dest.is_symlink())
                self.assertEqual(dest.resolve(), source.resolve())
            self.assertFalse((self.home / '.agents').exists())
            self.assertFalse((self.home / '.claude').exists())
            self.assertFalse((self.home / '.codex').exists())

    def test_native_layout_roles_and_safe_commands(self):
        root = self.root / "project space'; echo unsafe"
        layout = workspace.native_layout(root, 'test')
        surfaces = []
        def walk(node):
            if 'pane' in node:
                surfaces.extend(node['pane']['surfaces'])
            else:
                for child in node['children']:
                    walk(child)
        walk(layout)
        self.assertEqual(len(surfaces), 8)
        self.assertEqual(sum(s['focus'] for s in surfaces), 1)
        import shlex
        for surface in surfaces:
            self.assertIn(f'SUMI_ROOT={root}', shlex.split(surface['command']))
        kdl = workspace.zellij_layout(root, 'test')
        self.assertIn('stacked=true', kdl)
        self.assertIn('Weekly allowance remaining', kdl)

    def test_native_reopen_uses_existing_workspace(self):
        calls = []
        def fake(args, check=True):
            calls.append(args)
            data = {'workspaces': [{'id': 'existing-id', 'title': 'sumi-test'}]} if 'list-workspaces' in args else {}
            return subprocess.CompletedProcess(args, 0, json.dumps(data), '')
        with patch('sumi_workspace.run', side_effect=fake), patch('sumi_workspace.sys.platform', 'darwin'):
            workspace.start_native('cmux', self.root, 'sumi-test', False)
        self.assertTrue(any('select-workspace' in call for call in calls))
        self.assertFalse(any('new-workspace' in call for call in calls))

    def test_native_creation_sends_layout_and_respects_detach(self):
        calls = []
        def fake(args, check=True):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, '{"workspaces": []}', '')
        with patch('sumi_workspace.run', side_effect=fake), patch('sumi_workspace.sys.platform', 'darwin'):
            workspace.start_native('cmux', self.root, 'sumi-test', True)
        creation = next(c for c in calls if 'new-workspace' in c)
        self.assertEqual(creation[creation.index('--focus') + 1], 'false')
        self.assertEqual(json.loads(creation[creation.index('--layout') + 1]),
                         workspace.native_layout(self.root, 'sumi-test'))

    def test_native_access_denial_is_reported_without_settings_changes(self):
        calls = []
        def fake(args, check=True):
            calls.append(args)
            return subprocess.CompletedProcess(args, 1, '', 'Access denied')
        with patch('sumi_workspace.run', side_effect=fake), patch('sumi_workspace.sys.platform', 'darwin'):
            with self.assertRaisesRegex(RuntimeError, 'No access setting was changed'):
                workspace.start_native('cmux', self.root, 'sumi-test', True)
        self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
