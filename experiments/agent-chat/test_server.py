import importlib.util
import json
import io
from unittest.mock import Mock
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "chat_server", Path(__file__).with_name("server.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chats = mod.Chats(self.root)

    def tearDown(self):
        self.chats.close()
        self.tmp.cleanup()

    def test_concurrent_send_rejected_and_restart_recovers(self):
        with patch.object(mod.threading.Thread, "start"):
            ident = self.chats.send({"message": "hello"})["id"]
            with self.assertRaises(ValueError):
                self.chats.send({"message": "duplicate"})
        self.chats.emit(ident, {"type": "thread.started", "thread_id": "test-thread"})
        restored = mod.Chats(self.root)
        self.assertEqual(restored.rows[ident]["thread"], "test-thread")
        self.assertEqual(restored.rows[ident]["status"], "interrupted")
        self.assertEqual(restored.rows[ident]["events"][-1]["type"], "chat.done")
        with patch.object(mod.threading.Thread, "start"):
            restored.send({"conversation": ident, "message": "continue"})
        self.assertEqual(restored.rows[ident]["turn"], 2)
        restored.close()

    def test_invalid_inputs_never_start_process(self):
        with patch.object(mod.subprocess, "Popen") as launch:
            for payload in (
                {"message": ""},
                {"message": []},
                {"message": "x" * 16001},
                {"message": "hello", "conversation": "absent"},
            ):
                with self.assertRaises(ValueError):
                    self.chats.send(payload)
            launch.assert_not_called()

    def test_nonzero_exit_is_failed_even_after_completion_event(self):
        with patch.object(mod.threading.Thread, "start"):
            ident = self.chats.send({"message": "hello"})["id"]
            process = Mock()
            process.stdin = io.StringIO()
            process.stdout = io.StringIO('{"type":"turn.completed","usage":{}}\n')
            process.wait.return_value = 1
            process.poll.return_value = 1
            with patch.object(mod.subprocess, "Popen", return_value=process):
                self.chats.run(ident, "hello")
        self.assertEqual(self.chats.rows[ident]["status"], "failed")
        self.assertEqual(self.chats.rows[ident]["events"][-1]["status"], "failed")

    def test_selected_model_and_effort_reach_resume_command(self):
        self.chats.models = [
            {"id": "gpt-6-luna", "name": "Luna", "efforts": ["low", "high"]}
        ]
        with patch.object(mod.threading.Thread, "start"):
            ident = self.chats.send(
                {"message": "hello", "model": "gpt-6-luna", "effort": "high"}
            )["id"]
            self.chats.rows[ident]["thread"] = "saved-thread"
            process = Mock()
            process.stdin = io.StringIO()
            process.stdout = io.StringIO('{"type":"turn.completed","usage":{}}\n')
            process.wait.return_value = 0
            process.poll.return_value = 0
            with patch.object(mod.subprocess, "Popen", return_value=process) as launch:
                self.chats.run(ident, "hello")
            argv = launch.call_args.args[0]
            self.assertIn('model_reasoning_effort="high"', argv)
            self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-luna")
            self.assertEqual(argv[-3:], ["resume", "saved-thread", "-"])
        self.assertEqual(self.chats.rows[ident]["events"][0]["effort"], "high")
        with self.assertRaises(ValueError):
            self.chats.send({"message": "hello", "model": "unknown"})
        with self.assertRaises(ValueError):
            self.chats.send({"message": "hello", "effort": "invented"})

    def test_stop_before_process_launch_is_persisted(self):
        with patch.object(mod.threading.Thread, "start"):
            ident = self.chats.send({"message": "hello"})["id"]
        self.chats.stop(ident)
        self.assertTrue(
            json.loads((self.root / "conversations.json").read_text())[ident][
                "stop_requested"
            ]
        )


if __name__ == "__main__":
    unittest.main()
