import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from agent_activity import CODEX_BUSY_REGEX, CODEX_IDLE_REGEX, run_activity, pane_activity


class ActivityTest(unittest.TestCase):
    def test_codex_spinner_frames_keep_busy(self):
        for prefix in ('', '• ', '● ', '◦ ', '○ ', '· ', '∙ ', '⠋ ', '⠙ ', '  ◦ '):
            text = prefix + 'Working (26s • esc to interrupt) · 1 background terminal running'
            self.assertEqual(pane_activity(text, busy_regex=CODEX_BUSY_REGEX)['activity'], 'busy', prefix)
        self.assertEqual(pane_activity('User says Working (esc to interrupt)',
                                      busy_regex=CODEX_BUSY_REGEX)['activity'], 'unknown')

    def test_turn_events_and_process_result_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            run = dict(id='A', directory=directory, state='running')
            path.write_text(json.dumps(dict(type='turn.started')) + '\n')
            self.assertEqual(run_activity(run)['activity'], 'busy')
            # No new output does not turn busy into idle.
            self.assertEqual(run_activity(run)['activity'], 'busy')
            with path.open('a') as out:
                out.write(json.dumps(dict(type='turn.completed')) + '\n')
                out.write('{"type":')  # partial writer record is ignored
            self.assertEqual(run_activity(run)['activity'], 'idle')
            run['state'] = 'exited'
            self.assertEqual(run_activity(run)['activity'], 'finished')

    def test_tail_is_ten_lines_and_missing_data_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            run = dict(id='A', directory=directory, state='running')
            self.assertEqual(run_activity(run)['activity'], 'unknown')
            event = dict(type='item.completed', item=dict(type='agent_message',
                         text='\n'.join(str(i) for i in range(20))))
            (Path(directory) / 'events.jsonl').write_text(json.dumps(event) + '\n')
            self.assertEqual(run_activity(run)['lines'], [str(i) for i in range(10, 20)])

    def test_screen_heuristics_never_treat_silence_as_idle(self):
        self.assertEqual(pane_activity('quiet prompt')['activity'], 'unknown')
        self.assertEqual(pane_activity('Working (esc to interrupt)', busy_regex='esc to interrupt')['activity'], 'busy')
        self.assertEqual(pane_activity('Approve? [y/n]', waiting_regex=r'Approve\?')['activity'], 'waiting')
        self.assertEqual(pane_activity('Working Approve?', busy_regex='Working', waiting_regex='Approve')['activity'], 'unknown')

    def test_codex_completion_is_idle_unless_busy_or_waiting(self):
        def activity(text, **kwargs):
            return pane_activity(text, idle_regex=CODEX_IDLE_REGEX,
                                 busy_regex='esc to interrupt', waiting_regex=r'Approve\?',
                                 **kwargs)['activity']
        for marker in ('Worked for 16m 21s · 09:19', '  Worked for 2s',
                       'Worked for 1h 2m 3s · 09:19:00'):
            self.assertEqual(activity(marker + '\n› Ask Codex to do anything'), 'idle')
        marker = 'Worked for 16m 21s · 09:19'
        self.assertEqual(activity(marker + '\n• Working (2s • esc to interrupt)'), 'busy')
        self.assertEqual(activity(marker + '\nApprove?'), 'waiting')
        self.assertEqual(activity('User quoted "' + marker + '"'), 'unknown')
        self.assertEqual(activity('Worked for something'), 'unknown')
        long_response = marker + '\n' + '\n'.join(['response line'] * 15)
        self.assertEqual(activity(long_response, lines=20), 'idle')
        self.assertEqual(activity(long_response), 'unknown')


if __name__ == '__main__':
    unittest.main()
