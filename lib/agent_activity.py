"""Read bounded output tails; distinguish provider events from screen guesses."""
from collections import deque
import json
from pathlib import Path
import re

CODEX_IDLE_REGEX = r'(?m)^\s*Worked for (?:\d+(?:\.\d+)?[hms]\s*)+(?:[·•]\s*\d{1,2}:\d{2}(?::\d{2})?)?\s*$'


def event_tail(path, limit=256 * 1024):
    if not path.exists():
        return []
    with path.open('rb') as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - limit))
        data = stream.read(limit)
    if size > limit:
        data = data.partition(b'\n')[2]  # discard a possibly truncated first record
    events = []
    for line in data.decode(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # writers may be part way through a JSON line
        if isinstance(event, dict):
            events.append(event)
    return events


def run_activity(run, lines=10):
    events = event_tail(Path(run['directory']) / 'events.jsonl')
    output = deque(maxlen=lines)
    activity = 'unknown'
    for event in events:
        kind = event.get('type')
        if kind in ('turn.started', 'item.started'):
            activity = 'busy'
        elif kind == 'turn.completed':
            activity = 'idle'
        elif kind in ('turn.failed', 'error'):
            activity = 'failed'
        item = event.get('item') or {}
        text = ''
        if item.get('type') == 'command_execution':
            if kind == 'item.started':
                text = '> ' + item.get('command', '')
            else:
                text = item.get('aggregated_output', '')
        elif kind == 'item.completed':
            text = item.get('text', '')
        if kind in ('turn.failed', 'error'):
            text = json.dumps(event)
        output.extend(text.splitlines())
    state = run['state']
    if state != 'running':
        activity = {'exited': 'finished', 'failed': 'failed', 'interrupted': 'interrupted',
                    'orphaned': 'unknown', 'starting': 'starting', 'prepared': 'not started',
                    'preparing': 'preparing', 'cancelled': 'cancelled'}.get(state, 'unknown')
    return dict(run_id=run['id'], activity=activity, source='codex-events+run-state',
                run_state=state, lines=list(output))


def pane_activity(text, lines=10, busy_regex=None, waiting_regex=None, idle_regex=None):
    tail = text.rstrip().splitlines()[-lines:]
    sample = '\n'.join(tail)
    busy = bool(busy_regex and re.search(busy_regex, sample, re.I))
    waiting = bool(waiting_regex and re.search(waiting_regex, sample, re.I))
    activity = 'unknown' if busy == waiting else ('busy' if busy else 'waiting')
    # A prior completion can remain visible while a new turn is running.
    if not busy and not waiting and idle_regex and re.search(idle_regex, sample, re.I):
        activity = 'idle'
    return dict(activity=activity, source='screen-regex-heuristic', lines=tail,
                note='A screen match is a hint, not a reliable lifecycle event. Silence is unknown.')
