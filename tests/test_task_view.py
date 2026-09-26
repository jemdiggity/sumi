import curses
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from task_view import display, flatten, partition, read_tasks
from sumi_runner import atomic_json


class TaskViewTest(unittest.TestCase):
    def test_nested_counts_and_active_first(self):
        entries = list(flatten([
            dict(id='P', title='Parent', status='blocked', children=[
                dict(id='A', title='Working', status='active'),
                dict(id='D', title='Done', status='done')]),
            dict(id='S', title='Replaced', status='superseded'),
        ]))
        opened, closed = partition(entries)
        self.assertEqual([t['id'] for t, _ in opened], ['A', 'P'])
        self.assertEqual([t['id'] for t, _ in closed], ['D', 'S'])
        self.assertEqual(opened[0][1], 1)

    def test_live_atomic_save_views_and_invalid_save_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / '.sumi/tasks.json'
            tasks = [dict(id='A', title='Build widget', status='active')]
            atomic_json(path, tasks)
            frames = []

            class Screen:
                def timeout(self, value):
                    self.timeout_ms = value

                def getmaxyx(self):
                    return 18, 54

                def erase(self):
                    self.rows = {}

                def addnstr(self, row, col, text, width, attr):
                    self.rows[row] = text[:width]

                def refresh(self):
                    frames.append('\n'.join(self.rows.values()))

                def getch(self):
                    if len(frames) == 1:
                        tasks[0]['status'] = 'done'
                        atomic_json(path, tasks)
                        return -1  # timer tick, no user input
                    if len(frames) == 2:
                        return 9  # switch to Done
                    if len(frames) == 3:
                        path.write_text('{')
                        return -1
                    if len(frames) == 4:
                        atomic_json(path, [])
                        return -1
                    return ord('q')

            screen = Screen()
            with patch('task_view.curses.curs_set'):
                display(screen, path)
            self.assertEqual(screen.timeout_ms, 1000)
            self.assertIn('1 open · 0 closed', frames[0])
            self.assertIn('> A Build widget', frames[0])
            self.assertIn('0 open · 1 closed', frames[1])
            self.assertNotIn('Build widget', frames[1])
            self.assertIn('[2 Done]', frames[2])
            self.assertIn('Build widget', frames[2])
            self.assertIn('Read error', frames[3])
            self.assertIn('Build widget', frames[3])
            self.assertIn('0 open · 0 closed', frames[4])
            self.assertNotIn('Read error', frames[4])

    def test_missing_file_is_not_an_empty_queue(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                read_tasks(Path(root) / '.sumi/tasks.json')


if __name__ == '__main__':
    unittest.main()
