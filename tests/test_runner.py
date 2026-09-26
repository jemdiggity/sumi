import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from sumi_runner import Factory, Zellij, atomic_json, task_index
from mux_adapters import ADAPTERS

CLI = Path(__file__).resolve().parents[1] / 'bin/sumi'


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.tasks = [dict(id=k, title=k, status='ready', depends_on=[],
                           acceptance=['Produce a result'], evidence=[]) for k in ('A', 'B')]
        atomic_json(self.root / '.sumi/tasks.json', self.tasks)
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@localhost', 'commit', '-qm', 'Seed')
        self.factory = Factory(self.root)
        fake = self.root / 'fake-bin'
        fake.mkdir()
        binary = fake / 'codex'
        binary.write_text('''#!/usr/bin/env python3
import json,os,pathlib,time,sys
print(json.dumps({'type':'thread.started','thread_id':'test-session-'+pathlib.Path.cwd().name}),flush=True)
started=time.time()
time.sleep(1)
pathlib.Path('worker-result.json').write_text(json.dumps({'cwd':os.getcwd(),'start':started,'end':time.time()}))
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Fixture complete'}}),flush=True)
sys.exit(int(os.environ.get('FIXTURE_EXIT','0')))
''')
        binary.chmod(0o755)
        self.env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'])

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def process(self, *args, env=None):
        return subprocess.Popen([sys.executable, str(CLI), '--root', str(self.root), *args],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=env or self.env)

    def test_atomic_claim(self):
        workers = [self.process('prepare', 'A') for _ in range(2)]
        for worker in workers:
            worker.communicate(timeout=10)
        self.assertEqual(sorted(p.returncode for p in workers), [0, 1])
        self.assertEqual(len(self.factory.records()), 1)

    def test_run_uses_recorded_mux_and_preserves_legacy_records(self):
        calls = []

        class OtherMux:
            def __init__(self, session):
                self.session = session

            def open(self, run, executable):
                calls.append((self.session, run['id']))
                return 'opaque-workspace'

        with patch.dict(ADAPTERS, {'fixture': OtherMux}):
            prepared = Factory(self.root, session='other-session', mux='fixture').prepare('A')
            # A later invocation's default must not change a prepared run's backend.
            result = self.factory.start(prepared['id'])
            self.assertEqual(result['workspace_mux'], 'fixture')
            self.assertEqual(result['workspace_id'], 'opaque-workspace')
            self.assertEqual(calls, [('other-session', prepared['id'])])
        legacy = self.factory.prepare('B')
        legacy.pop('workspace_mux')
        self.factory.save(legacy)
        with patch.object(Zellij, 'open', return_value='9') as launch:
            self.factory.start(legacy['id'])
        launch.assert_called_once()

    def test_dependencies_and_graph_errors(self):
        self.tasks[0]['depends_on'] = ['B']
        atomic_json(self.factory.tasks, self.tasks)
        with self.assertRaisesRegex(ValueError, 'Unfinished'):
            self.factory.prepare('A')
        self.tasks[1]['depends_on'] = ['A']
        with self.assertRaisesRegex(ValueError, 'cycle'):
            task_index(self.tasks)
        self.tasks[1]['depends_on'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'Missing'):
            task_index(self.tasks)
        parent = dict(id='P', title='group', status='ready', depends_on=['B'], children=[self.tasks[0]])
        self.tasks[0]['depends_on'] = []
        self.tasks[1]['depends_on'] = []
        atomic_json(self.factory.tasks, [parent, self.tasks[1]])
        with self.assertRaisesRegex(ValueError, 'Unfinished'):
            self.factory.prepare('A')

    def test_parallel_workers_and_resume(self):
        runs = [self.factory.prepare(k) for k in ('A', 'B')]
        with patch.object(Zellij, 'open', return_value='9'):
            for run in runs:
                self.factory.start(run['id'])
            with self.assertRaisesRegex(ValueError, 'start only'):
                self.factory.start(runs[0]['id'])
        workers = [self.process('_worker', r['id']) for r in runs]
        for worker in workers:
            out, err = worker.communicate(timeout=15)
            self.assertEqual(worker.returncode, 0, out + err)
        results = [json.loads((Path(r['worktree']) / 'worker-result.json').read_text()) for r in runs]
        self.assertNotEqual(results[0]['cwd'], results[1]['cwd'])
        self.assertLess(max(r['start'] for r in results), min(r['end'] for r in results))
        states = [self.factory.read(r['id']) for r in runs]
        self.assertTrue(all(r['state'] == 'exited' and r['session_id'] for r in states))
        self.assertTrue(all(t['status'] == 'blocked' for t in json.loads(self.factory.tasks.read_text())))
        resumed = self.factory.prepare('A', states[0], 'Review your result')
        self.assertEqual(resumed['worktree'], runs[0]['worktree'])
        self.assertEqual(resumed['session_id'], states[0]['session_id'])
        self.assertNotEqual(resumed['id'], states[0]['id'])
        duplicate = self.process('_worker', runs[0]['id'])
        duplicate.communicate(timeout=5)
        self.assertEqual(duplicate.returncode, 1)

    def test_failure_and_lost_worker(self):
        run = self.factory.prepare('A')
        with patch.object(Zellij, 'open', side_effect=RuntimeError('mux unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'mux unavailable'):
                self.factory.start(run['id'])
        self.assertEqual(self.factory.read(run['id'])['state'], 'failed')
        run = self.factory.prepare('B')
        with patch.object(Zellij, 'open', return_value='9'):
            self.factory.start(run['id'])
        worker = self.process('_worker', run['id'], env=dict(self.env, FIXTURE_EXIT='7'))
        worker.communicate(timeout=10)
        state = self.factory.read(run['id'])
        self.assertEqual(state['state'], 'failed')
        self.assertEqual(state['exit_code'], 7)
        state['state'] = 'running'
        self.factory.save(state)
        self.assertEqual(self.factory.reconcile(run['id'])['state'], 'interrupted')
        self.assertTrue(Path(state['worktree']).exists())

    def test_orphan_keeps_worktree_reserved(self):
        run = self.factory.prepare('A')
        with patch.object(Zellij, 'open', return_value='9'):
            self.factory.start(run['id'])
        worker = self.process('_worker', run['id'])
        deadline = time.monotonic() + 5
        while not self.factory.read(run['id']).get('session_id'):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.02)
        worker.kill()
        worker.communicate(timeout=5)
        state = self.factory.reconcile(run['id'])
        self.assertEqual(state['state'], 'orphaned')
        with self.assertRaisesRegex(ValueError, 'already has'):
            self.factory.prepare('A', state, 'Retry')
        while self.factory.reconcile(run['id'])['state'] == 'orphaned':
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        self.assertEqual(self.factory.read(run['id'])['state'], 'interrupted')

    def test_cancel_preparation_preserves_files(self):
        run = self.factory.prepare('A')
        process = self.process('cancel', run['id'])
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.factory.read(run['id'])['state'], 'cancelled')
        self.assertTrue(Path(run['worktree']).is_dir())
        self.assertNotEqual(self.factory.prepare('A')['id'], run['id'])

    def test_startup_without_session_can_be_requeued(self):
        run = self.factory.prepare('A')
        with patch.object(Zellij, 'open', return_value='9'):
            self.factory.start(run['id'])
        run = self.factory.read(run['id'])
        run['started_at'] = '2000-01-01T00:00:00+00:00'
        self.factory.save(run)
        self.assertEqual(self.factory.reconcile(run['id'])['state'], 'interrupted')
        process = self.process('task', 'A', '--status', 'ready', '--evidence', 'Retry a launch that never created a Codex session')
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.factory.prepare('A')['state'], 'prepared')


if __name__ == '__main__':
    unittest.main()
