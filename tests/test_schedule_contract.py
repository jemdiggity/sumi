"""Shared observable CLI contract. Set SUMI_NATIVE_BIN to test Rust + interoperability."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = [sys.executable, str(ROOT / 'bin/sumi')]
NATIVE = os.environ.get('SUMI_NATIVE_BIN')
ENGINES = [PYTHON] + ([[str(Path(NATIVE).resolve())]] if NATIVE else [])


class ScheduleContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sumi contract ')
        self.root = Path(self.temp.name)
        self.children = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            try:
                child.communicate(timeout=6)
            except subprocess.TimeoutExpired:
                child.kill(); child.communicate()
        self.temp.cleanup()

    def cli(self, engine, *args, check=True):
        p = subprocess.run(engine + ['--root', str(self.root), 'schedule', *args],
                           capture_output=True, text=True, timeout=10)
        if check:
            self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def spawn(self, engine, *args):
        p = subprocess.Popen(engine + ['--root', str(self.root), 'schedule', *args],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.children.append(p)
        return p

    def records(self):
        return [json.loads(p.read_text()) for p in self.root.glob('.sumi/schedule-runs/*/run.json')]

    def wait_for(self, predicate):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.03)
        self.fail('Timed out waiting for scheduler')

    def test_lifecycle_literal_arguments_and_history_switch(self):
        for index, engine in enumerate(ENGINES):
            other = ENGINES[(index + 1) % len(ENGINES)]
            name = f'job{index}'
            literal = 'space $HOME `touch unexpected` ; *'
            self.cli(engine, 'add', name, '--every', '1d', '--', sys.executable, '-c',
                     'import sys; print(sys.argv[1]); print(sys.stdin.read())', literal)
            self.cli(other, 'pause', name)
            record = json.loads(self.cli(engine, 'run', name).stdout)
            self.assertEqual(Path(record['stdout']).read_text(), literal + '\n\n')
            listing = json.loads(self.cli(other, 'list').stdout)
            item = next(i for i in listing if i['id'] == name)
            self.assertFalse(item['enabled']); self.assertIsNone(item['next_due'])
            self.assertEqual(item['last_result']['run_id'], record['run_id'])
            self.cli(other, 'resume', name)
            self.assertIsNotNone(next(i for i in json.loads(self.cli(engine, 'list').stdout) if i['id'] == name)['next_due'])
            self.cli(engine, 'remove', name)
            self.assertEqual(len(json.loads(self.cli(other, 'runs', name).stdout)), 1)

    def test_invalid_inputs_preserve_state_and_failures_preserve_logs(self):
        for index, engine in enumerate(ENGINES):
            for bad in ('0s', '1é', '999999999999999999999d'):
                self.assertNotEqual(self.cli(engine, 'add', 'bad', '--every', bad, '--', '/bin/echo', check=False).returncode, 0)
            self.cli(engine, 'add', 'add', '--every', '1d', '--', sys.executable, '-c',
                     'import sys; print("failure", file=sys.stderr); sys.exit(7)')
            for action in ('run', 'remove'):
                self.assertEqual(self.cli(engine, action, 'add', '--', 'unexpected', check=False).returncode, 2)
            failed = self.cli(engine, 'run', 'add', check=False)
            self.assertEqual(failed.returncode, 1)
            run = json.loads(failed.stdout)
            self.assertEqual(run['exit_code'], 7)
            self.assertEqual(Path(run['stderr']).read_text(), 'failure\n')
            self.cli(engine, 'remove', 'add')
            config = self.root / '.sumi/schedules.json'
            config.write_text('{broken')
            self.assertNotEqual(self.cli(engine, 'add', 'x', '--every', '1s', '--', '/bin/echo', check=False).returncode, 0)
            self.assertEqual(config.read_text(), '{broken')
            config.unlink()

    def test_service_catchup_live_edits_and_cross_engine_exclusion(self):
        for index, engine in enumerate(ENGINES):
            other = ENGINES[(index + 1) % len(ENGINES)]
            name = f'service{index}'
            self.cli(engine, 'add', name, '--every', '1d', '--', sys.executable, '-c', 'import time; time.sleep(60)')
            # Make one schedule overdue without spending a day waiting. Shared format fixture.
            config = self.root / '.sumi/schedules.json'
            items = json.loads(config.read_text()); items[-1]['anchor'] = 0
            config.write_text(json.dumps(items))
            server = self.spawn(engine, 'serve')
            self.wait_for(lambda: any(r['schedule_id'] == name and r['state'] == 'running' for r in self.records()))
            for args in [('run', name), ('serve',), ('remove', name)]:
                self.assertNotEqual(self.cli(other, *args, check=False).returncode, 0)
            self.cli(other, 'pause', name)  # Configuration remains editable during execution.
            server.send_signal(signal.SIGINT); server.communicate(timeout=6)
            self.assertEqual(server.returncode, 130)
            self.assertEqual(next(r for r in self.records() if r['schedule_id'] == name)['state'], 'interrupted')
            listing = next(i for i in json.loads(self.cli(other, 'list').stdout) if i['id'] == name)
            self.assertFalse(listing['running']); self.assertFalse(listing['enabled'])
            self.cli(other, 'remove', name)

    def test_crash_recovery_across_engines(self):
        for index, engine in enumerate(ENGINES):
            other = ENGINES[(index + 1) % len(ENGINES)]
            name = f'crash{index}'
            marker = self.root / f'release{index}'
            script = 'import pathlib,time,sys\np=pathlib.Path(sys.argv[1])\nwhile not p.exists(): time.sleep(.05)'
            self.cli(engine, 'add', name, '--every', '1d', '--', sys.executable, '-c', script, str(marker))
            worker = self.spawn(engine, 'run', name)
            self.wait_for(lambda: any(r['schedule_id'] == name and r['state'] == 'running' for r in self.records()))
            worker.kill(); worker.communicate(timeout=6)
            try:
                blocked = self.cli(other, 'run', name, check=False)
                self.assertNotEqual(blocked.returncode, 0)
                self.assertIn('recovery', blocked.stderr)
            finally:
                marker.touch()
            # The OS reaps the orphan. Serve will reconcile then wait (not catch up repeatedly).
            record = next(r for r in self.records() if r['schedule_id'] == name)
            def gone():
                try: os.killpg(record['pgid'], 0); return False
                except ProcessLookupError: return True
            self.wait_for(gone)
            server = self.spawn(other, 'serve')
            self.wait_for(lambda: next(r for r in self.records() if r['schedule_id'] == name)['state'] == 'interrupted')
            server.send_signal(signal.SIGINT); server.communicate(timeout=6)
            self.assertEqual(len([r for r in self.records() if r['schedule_id'] == name]), 1)
            self.cli(other, 'remove', name)

    @unittest.skipUnless(NATIVE, 'Set SUMI_NATIVE_BIN for standalone binary verification')
    def test_native_needs_no_checkout_python_or_toolchain(self):
        binary = self.root / 'sumi'
        shutil.copy2(NATIVE, binary)
        env = {'PATH': '/no-tools-here', 'HOME': str(self.root)}
        base = [str(binary), '--root', str(self.root), 'schedule']
        for args in [('add', 'standalone', '--every', '1s', '--', '/bin/echo', 'standalone'), ('run', 'standalone')]:
            p = subprocess.run(base + list(args), cwd=self.root, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(Path(json.loads(p.stdout)['stdout']).read_text(), 'standalone\n')


if __name__ == '__main__': unittest.main()
