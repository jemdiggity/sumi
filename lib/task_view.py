"""Read-only, live task views shared by terminal multiplexers."""
import curses
import json
from pathlib import Path
import textwrap

TASKS = Path(__file__).resolve().parent.parent / '.sumi/tasks.json'
CLOSED = {'done', 'superseded'}


def flatten(tasks, depth=0):
    if not isinstance(tasks, list):
        raise ValueError('Expected a list of tasks')
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get('title'), str):
            raise ValueError('Each task needs a title')
        yield task, depth
        yield from flatten(task.get('children', []), depth + 1)


def read_tasks(path):
    # Reopen every tick: atomic replacement by the runner must be picked up too.
    return list(flatten(json.loads(path.read_text())))


def partition(entries):
    opened = [(t, d) for t, d in entries if t.get('status') not in CLOSED]
    closed = [(t, d) for t, d in entries if t.get('status') in CLOSED]
    opened.sort(key=lambda entry: entry[0].get('status') != 'active')
    return opened, closed


def clean(value):
    return ''.join(c for c in str(value) if c.isprintable())


def task_lines(entries, width):
    lines = []
    for task, depth in entries:
        status = clean(task.get('status', 'proposed'))
        active = status == 'active'
        indent = '  ' * min(depth, max(0, (width - 12) // 2))
        label = f'{">" if active else "·"} {clean(task.get("id", ""))} {clean(task["title"])}'
        lines.extend((line, active) for line in textwrap.wrap(
            label, width, initial_indent=indent, subsequent_indent=indent + '  '))
        lines.append((indent + '  ' + status, active))
        lines.append(('', False))
    return lines or [('No tasks in this view.', False)]


def display(screen, path=TASKS):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.timeout(1000)
    entries, error = [], ''
    view, offsets = 0, [0, 0]
    while True:
        try:
            entries = read_tasks(path)
            error = ''
        except (OSError, ValueError) as exc:
            error = 'Read error (last good data): ' + clean(exc)
        height, width = screen.getmaxyx()
        content_width = max(4, width - 2)
        opened, closed = partition(entries)
        active = sum(t.get('status') == 'active' for t, _ in opened)
        header = [
            (f'TASKS  {len(opened)} open · {len(closed)} closed', True),
            ('[1 Open]  2 Done' if view == 0 else '1 Open  [2 Done]', True),
            (error or f'{active} active · live / 1s', bool(error)),
            ('─' * content_width, False),
        ]
        lines = task_lines((opened, closed)[view], content_width)
        body_height = max(0, height - len(header) - 2)
        offsets[view] = min(offsets[view], max(0, len(lines) - body_height))
        offset = offsets[view]
        screen.erase()

        def draw(row, text, bold=False):
            if row >= height:
                return
            try:
                screen.addnstr(row, 1, text, max(0, width - 2),
                               curses.A_BOLD if bold else curses.A_NORMAL)
            except curses.error:
                pass

        for row, (text, bold) in enumerate(header):
            draw(row, text, bold)
        for row, (text, bold) in enumerate(lines[offset:offset + body_height], len(header)):
            draw(row, text, bold)
        draw(max(0, height - 2), 'Tab views · j/k scroll · g/G ends')
        screen.refresh()
        key = screen.getch()
        if key in (ord('q'), 27):
            return
        if key in (9, curses.KEY_BTAB, curses.KEY_LEFT, curses.KEY_RIGHT):
            view = 1 - view
        elif key in (ord('1'), ord('2')):
            view = key - ord('1')
        elif key in (ord('j'), curses.KEY_DOWN):
            offsets[view] += 1
        elif key in (ord('k'), curses.KEY_UP):
            offsets[view] = max(0, offset - 1)
        elif key == curses.KEY_NPAGE:
            offsets[view] += max(1, body_height)
        elif key == curses.KEY_PPAGE:
            offsets[view] = max(0, offset - max(1, body_height))
        elif key in (ord('g'), curses.KEY_HOME):
            offsets[view] = 0
        elif key in (ord('G'), curses.KEY_END):
            offsets[view] = len(lines)
