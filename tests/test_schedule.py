import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from sumi_schedule import Scheduler, interval, lock
from sumi_runner import atomic_json

BIN = Path(__file__).resolve().parents[1] / 'bin/sumi'


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sumi schedule ')
        self.root = Path(self.temp.name)
        self.now = 1000
        self.s = Scheduler(self.root, clock=lambda: self.now)
        self.children = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(BIN), '--root', str(self.root), 'schedule', *args],
                              capture_output=True, text=True, timeout=10)

    def spawn(self, *args):
        child = subprocess.Popen([sys.executable, str(BIN), '--root', str(self.root), 'schedule', *args],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.children.append(child)
        return child

    def wait_for(self, predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.03)
        self.fail('Timed out waiting for subprocess state')

    def add(self, name='sample', command=None):
        return self.s.edit('add', name, '10s', command or [sys.executable, '-c', 'print("hello")'])

    def test_cli_literal_arguments_and_lifecycle(self):
        literal = 'space $HOME `touch unexpected` ; *'
        added = self.cli('add', 'sample', '--every', '24h', '--', sys.executable, '-c',
                         'import sys; print(sys.argv[1]); print(sys.stdin.read())', literal)
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertEqual(self.cli('pause', 'sample').returncode, 0)
        result = self.cli('run', 'sample')
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(Path(record['stdout']).read_text(), literal + '\n\n')
        self.assertFalse(self.root.joinpath('unexpected').exists())
        listing = json.loads(self.cli('list').stdout)
        self.assertFalse(listing[0]['enabled'])
        self.assertIsNone(listing[0]['next_due'])
        self.assertEqual(self.cli('resume', 'sample').returncode, 0)
        self.assertEqual(self.cli('remove', 'sample').returncode, 0)
        self.assertEqual(len(json.loads(self.cli('runs', 'sample').stdout)), 1)
        self.assertEqual(json.loads(self.cli('list').stdout), [])

    def test_due_order_catchup_completion_and_new_generation(self):
        self.add('b'); self.add('a')
        self.assertIsNone(self.s.run())
        self.now = 9000
        self.assertEqual(self.s.run()['schedule_id'], 'a')
        self.assertEqual(self.s.run()['schedule_id'], 'b')
        self.assertIsNone(self.s.run())
        self.now += 10
        self.assertEqual(self.s.run()['schedule_id'], 'a')
        self.s.edit('remove', 'a')
        self.add('a')
        self.assertIsNone(self.s.latest(self.s.load()[-1], self.s.records()))

    def test_pause_resume_and_manual_run_use_completion_anchor(self):
        self.add()
        self.s.edit('pause', 'sample')
        self.now += 100
        self.assertIsNone(self.s.run())
        self.s.run('sample')
        self.assertFalse(self.s.load()[0]['enabled'])
        self.now += 5
        self.s.edit('resume', 'sample')
        self.now += 9
        self.assertIsNone(self.s.run())
        self.now += 1
        self.assertIsNotNone(self.s.run())

    def test_failure_missing_command_and_corrupt_config(self):
        self.add('fail', [sys.executable, '-c', 'import sys; print("bad", file=sys.stderr); sys.exit(7)'])
        result = self.cli('run', 'fail')
        self.assertEqual(result.returncode, 1)
        record = json.loads(result.stdout)
        self.assertEqual(record['exit_code'], 7)
        self.assertEqual(Path(record['stderr']).read_text(), 'bad\n')
        self.add('missing', ['/no/such/sumi-executable'])
        self.assertEqual(self.s.run('missing')['state'], 'failed')
        self.add('good')
        self.assertEqual(self.s.run('good')['state'], 'succeeded')
        self.s.definitions.write_text('{broken')
        with self.assertRaises(ValueError):
            self.s.edit('pause', 'good')
        self.assertEqual(self.s.definitions.read_text(), '{broken')
        for value in ('0s', '-1h', '1.5h', 'daily', '1w', '999999999999999999999d'):
            with self.assertRaises(ValueError):
                interval(value)

    def test_project_lock_excludes_manual_and_second_server(self):
        self.add()
        with lock(self.s.runtime / 'execution.lock'):
            result = self.cli('run', 'sample')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('busy', result.stderr)
        with lock(self.s.runtime / 'serve.lock'):
            result = self.cli('serve')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('busy', result.stderr)

    def test_serve_observes_edits_and_interrupts_command(self):
        self.add('long', [sys.executable, '-c', 'import time; time.sleep(60)'])
        self.s.edit('pause', 'long')
        server = self.spawn('serve')
        time.sleep(.2)
        self.assertEqual(self.s.records(), [])
        with self.s.config_lock():
            values = self.s.load()
            values[0]['enabled'] = True
            atomic_json(self.s.definitions, values)
        self.wait_for(lambda: any(r['state'] == 'running' for r in self.s.records()))
        self.assertNotEqual(self.cli('remove', 'long').returncode, 0)
        self.assertNotEqual(self.cli('run', 'long').returncode, 0)
        server.send_signal(signal.SIGINT)
        server.communicate(timeout=5)
        self.assertEqual(self.s.records()[0]['state'], 'interrupted')
        self.assertEqual(server.returncode, 130)

    def test_crashed_launcher_blocks_live_child_then_recovers(self):
        self.add('long', [sys.executable, '-c', 'import time; time.sleep(60)'])
        launcher = self.spawn('run', 'long')
        self.wait_for(lambda: any(r['state'] == 'running' for r in self.s.records()))
        record = self.s.records()[0]
        launcher.kill(); launcher.communicate(timeout=5)
        try:
            with self.assertRaisesRegex(RuntimeError, 'needs recovery'):
                self.s.run('long')
        finally:
            os.killpg(record['pgid'], signal.SIGKILL)
        # Orphan reaping depends on the OS; a dead group allows reconciliation.
        from unittest.mock import patch
        with patch('sumi_schedule.group_alive', return_value=False):
            with lock(self.s.runtime / 'execution.lock'):
                self.s.reconcile()
        self.assertEqual(self.s.records()[0]['state'], 'interrupted')
        self.assertIsNone(self.s.run())

    def test_uncertain_launch_never_retries_automatically(self):
        item = self.add()
        record = dict(run_id='a'*32, generation=item['generation'], schedule_id='sample',
                      started=self.now, ended=None, state='starting', pgid=None)
        self.s.save_run(record)
        with self.assertRaisesRegex(RuntimeError, 'ownership is uncertain'):
            self.s.run('sample')
        self.assertEqual(len(self.s.records()), 1)


if __name__ == '__main__':
    unittest.main()
