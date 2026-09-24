import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'setup.sh'


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tools = Path(self.temp.name)
        for name in ('git', 'delta', 'nvim', 'less'):
            self.executable(name, '#!/bin/sh\nexit 0\n')
        self.executable('uname', '#!/bin/sh\necho Linux\n')
        (self.tools / 'python3').symlink_to(sys.executable)
        (self.tools / 'bash').symlink_to('/bin/bash')
        self.env = dict(os.environ, PATH=str(self.tools))

    def tearDown(self):
        self.temp.cleanup()

    def executable(self, name, text):
        path = self.tools / name
        path.write_text(text)
        path.chmod(0o755)

    def run_setup(self, *args):
        return subprocess.run(['/bin/bash', str(SCRIPT), *args], env=self.env,
                              text=True, capture_output=True)

    def test_missing_check_and_dry_run_have_no_install_side_effect(self):
        self.assertEqual(self.run_setup('--check').returncode, 1)
        result = self.run_setup('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('brew install glow', result.stdout)
        self.assertFalse((self.tools / 'glow').exists())

    def test_install_missing_only_then_idempotent(self):
        target = shlex.quote(str(self.tools / 'glow'))
        log = shlex.quote(str(self.tools / 'brew.calls'))
        self.executable('brew', '#!/bin/sh\n' + f'echo "$*" >> {log}\n'
                        + f"printf '#!/bin/sh\\nexit 0\\n' > {target}\n/bin/chmod +x {target}\n")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.tools / 'brew.calls').read_text(), 'install glow\n')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((self.tools / 'brew.calls').read_text(), 'install glow\n')

    def test_mux_selection_and_unavailable_platform(self):
        self.executable('glow', '#!/bin/sh\nexit 0\n')
        self.assertEqual(self.run_setup('--check').returncode, 0)
        self.assertEqual(self.run_setup('--mux', 'tmux', '--check').returncode, 1)
        result = self.run_setup('--mux', 'tmux', '--dry-run')
        self.assertIn('brew install tmux', result.stdout)
        self.assertEqual(self.run_setup('--mux', 'cmux', '--dry-run').returncode, 2)
        self.assertEqual(self.run_setup('--mux', 'superlogical').returncode, 2)
