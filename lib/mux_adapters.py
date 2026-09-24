"""Mux adapters own views; task and agent lifecycle state lives in the runner.

Adapter contract: open(run, executable), workspaces(), focus(id), capture(id),
and updates(id). IDs are opaque outside the adapter. Capabilities are explicit.
"""
import json
from pathlib import Path
import subprocess
import sys


def command(args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


class Zellij:
    capabilities = {"workspaces", "capture", "stream"}

    def __init__(self, session):
        self.session = session

    def action(self, *args):
        return command(['zellij', '--session', self.session, 'action', *args])

    def updates(self, pane_id):
        """Yield native viewport events, owning the subscriber's lifetime."""
        process = subprocess.Popen(
            ['zellij', '--session', self.session, 'subscribe',
             '--pane-id', pane_id, '--format', 'json'],
            stdout=subprocess.PIPE, text=True)
        try:
            for line in process.stdout:
                yield json.loads(line)
            if process.wait():
                raise RuntimeError('Zellij pane subscription failed; see stderr above')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def open(self, run, executable):
        q = lambda s: json.dumps(str(s))
        layout = Path(run['directory']) / 'workspace.kdl'
        layout.write_text('layout {\n pane split_direction="vertical" {\n'
                          f'  pane name="{run["task_id"]} / Codex" size="75%" command={q(sys.executable)} {{\n'
                          f'   args {q(executable)} "--root" {q(run["root"])} "_worker" {q(run["id"])};\n'
                          '  }\n  pane name="Worktree shell"\n }\n'
                          ' pane size=1 borderless=true { plugin location="zellij:compact-bar"; }\n}\n')
        return self.action('new-tab', '--no-focus', '--name', run['id'],
                           '--cwd', run['worktree'], '--layout', str(layout))

    def workspaces(self):
        return [dict(id=tab['tab_id'], name=tab['name'])
                for tab in json.loads(self.action('list-tabs', '--json'))]

    def capture(self, pane_id):
        return self.action('dump-screen', '--pane-id', pane_id)

    def focus(self, tab):
        self.action('go-to-tab-by-id', str(tab))


ADAPTERS = {'zellij': Zellij}


def get_mux(name, session):
    try:
        adapter = ADAPTERS[name]
    except KeyError:
        raise ValueError(f'Mux adapter {name!r} is not implemented. Available: ' + ', '.join(ADAPTERS))
    return adapter(session)
