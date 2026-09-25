import importlib.util, json, tempfile, unittest, os, threading
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "live_server", Path(__file__).with_name("server.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.args = (
            self.root / "runtime",
            Path(__file__).with_name("bebop.html"),
            self.root / "bundle.js",
            self.root / "registry",
            Path(os.environ["SUMI_DOM_MODULE"]),
            2,
        )
        self.pool = mod.Pool(*self.args)

    def tearDown(self):
        self.pool.close()
        self.pool.db.close()
        self.tmp.cleanup()

    def payload(self, text="Make it quieter"):
        return {
            "revision": self.pool.getmeta("current"),
            "annotation": {"id": "a", "comment": text, "elementPath": "h1"},
            "scene": {"search": "Jet", "filter": "crew"},
        }

    def test_idempotency_and_edited_snapshot(self):
        payload = self.payload()
        job = self.pool.submit(payload)
        self.assertEqual(job, self.pool.submit(payload))
        other = self.pool.submit(self.payload("Change the title"))
        self.assertNotEqual(job, other)
        self.assertEqual(len(self.pool.state()["jobs"]), 2)

    def test_restart_preserves_queue_and_marks_interrupted(self):
        job = self.pool.submit(self.payload())
        self.pool.update(job, "working")
        self.pool.setmeta("paused", "true")
        self.pool.close()
        self.pool.db.close()
        self.pool = mod.Pool(*self.args)
        self.assertTrue(self.pool.state()["paused"])
        self.assertEqual(self.pool.state()["jobs"][0]["status"], "interrupted")

    def test_reject_unknown_revision_and_empty_comment(self):
        p = self.payload()
        p["revision"] = "nope"
        with self.assertRaises(ValueError):
            self.pool.submit(p)
        with self.assertRaises(ValueError):
            self.pool.submit(self.payload("  "))

    def test_clean_candidate_is_published(self):
        initial = self.pool.getmeta("current")
        job = self.pool.submit(self.payload())
        row = self.pool.db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()

        def good(ws, *_):
            p = ws / "index.html"
            p.write_text(
                p.read_text().replace("</footer>", "<small>Queue test</small></footer>")
            )
            return json.dumps({"outcome": "changed", "summary": "Small footer change"})

        self.pool.model = good
        self.pool.execute(row)
        self.assertNotEqual(self.pool.getmeta("current"), initial)
        self.assertEqual(self.pool.state()["jobs"][0]["status"], "published")
        self.assertFalse(
            self.pool.conflicts(self.pool.root / "workspaces" / ("merge-" + job))
        )

    def test_overlapping_changes_use_reconciliation(self):
        base = self.args[1].read_text()
        payload = self.payload("First title tweak")
        first = self.pool.submit(payload)
        payload["annotation"]["id"] = "second"
        payload["annotation"]["comment"] = "Second title tweak"
        second = self.pool.submit(payload)
        phases = []

        def model(ws, prompt, job, phase):
            phases.append(phase)
            text = base.replace(
                "<title>",
                "<title>"
                + ("A B " if phase == "reconcile" else "A " if job == first else "B "),
            )
            (ws / "index.html").write_text(text)
            return json.dumps({"outcome": "changed", "summary": "Title changed"})

        self.pool.model = model
        for job in [first, second]:
            self.pool.execute(
                self.pool.db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            )
        self.assertIn("reconcile", phases)
        self.assertTrue(
            all(j["status"] == "published" for j in self.pool.state()["jobs"])
        )
        self.assertIn(
            "<title>A B ", self.pool.revision(self.pool.getmeta("current"))["html"]
        )

    def test_bad_worker_preserves_published_revision(self):
        initial = self.pool.getmeta("current")
        job = self.pool.submit(self.payload())
        row = self.pool.db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()

        def broken(ws, *_):
            (ws / "index.html").write_text(
                "<html><body><script>broken(</script></body></html>"
            )
            return json.dumps({"outcome": "changed", "summary": "bad test candidate"})

        self.pool.model = broken
        self.pool.execute(row)
        self.assertEqual(self.pool.getmeta("current"), initial)
        self.assertEqual(self.pool.state()["jobs"][0]["status"], "failed")

    def test_claimed_edit_without_diff_fails(self):
        original = self.pool.getmeta("current")
        job = self.pool.submit(self.payload())
        self.pool.model = lambda *_: json.dumps(
            {"outcome": "changed", "summary": "I changed it"}
        )
        self.pool.execute(
            self.pool.db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        )
        result = self.pool.state()["jobs"][0]
        self.assertEqual(result["status"], "failed")
        self.assertIn("no changes", result["error"])
        self.assertEqual(self.pool.getmeta("current"), original)

    def test_clean_job_passes_slow_repair_and_new_head_is_preserved(self):
        base = self.args[1].read_text()
        ids = []
        for name in ["first", "slow", "clean"]:
            payload = self.payload(name)
            payload["annotation"]["id"] = name
            ids.append(self.pool.submit(payload))
        first, slow, clean = ids
        repairing = threading.Event()
        release = threading.Event()

        def model(ws, prompt, job, phase):
            if phase.startswith("reconcile"):
                self.assertEqual(job, slow)
                context = self.pool.root / "contexts" / slow / "0"
                self.assertIn("<title>A ", (context / "current.html").read_text())
                self.assertIn("<title>B ", (context / "candidate.html").read_text())
                self.assertIn("|||||||", (ws / "index.html").read_text())
                repairing.set()
                if not release.wait(10):
                    raise RuntimeError("Test did not release slow reconciler")
                text = base.replace("<title>", "<title>A B ")
            elif job == clean:
                text = base.replace(
                    "</footer>", "<small>Clean change survives</small></footer>"
                )
            else:
                text = base.replace(
                    "<title>", "<title>" + ("A " if job == first else "B ")
                )
            (ws / "index.html").write_text(text)
            return json.dumps({"outcome": "changed", "summary": "Implemented"})

        self.pool.model = model

        def run(job):
            with self.pool.lock:
                row = self.pool.db.execute(
                    "SELECT * FROM jobs WHERE id=?", (job,)
                ).fetchone()
            self.pool.execute(row)

        run(first)
        thread = threading.Thread(target=run, args=(slow,))
        thread.start()
        try:
            self.assertTrue(
                repairing.wait(5), "Slow worker never reached reconciliation"
            )
            run(clean)
            status = {j["id"]: j["status"] for j in self.pool.state()["jobs"]}
            self.assertEqual(status[clean], "published")
            self.assertEqual(status[slow], "reconciling")
        finally:
            release.set()
            thread.join(10)
        self.assertFalse(thread.is_alive())
        result = self.pool.revision(self.pool.getmeta("current"))["html"]
        self.assertIn("<title>A B ", result)
        self.assertIn("Clean change survives", result)
        self.assertTrue(
            all(j["status"] == "published" for j in self.pool.state()["jobs"])
        )

    @unittest.skipUnless(
        os.environ.get("SUMI_FORMATTER"), "Pinned Prettier path required"
    )
    def test_formatter_handles_ignored_workspace_and_noop_stays_failure(self):
        self.pool.formatter = Path(os.environ["SUMI_FORMATTER"])
        ignored_root = Path(__file__).resolve().parents[2] / ".playground"
        ignored_root.mkdir(exist_ok=True)
        compact = self.args[1].read_text().replace("\n", " ")
        with tempfile.TemporaryDirectory(dir=ignored_root) as directory:
            ws = Path(directory)
            (ws / "index.html").write_text(compact)
            self.pool.normalize(ws)
            self.assertLess(
                max(map(len, (ws / "index.html").read_text().splitlines())), 300
            )
        self.pool.jj(["new", "@"], self.pool.repo)
        (self.pool.repo / "index.html").write_text(compact)
        self.pool.publish(self.pool.repo)
        job = self.pool.submit(self.payload())

        def no_edit(ws, *_):
            self.assertLess(
                max(map(len, (ws / "index.html").read_text().splitlines())), 300
            )
            return json.dumps({"outcome": "changed", "summary": "Unsupported claim"})

        self.pool.model = no_edit
        self.pool.execute(
            self.pool.db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        )
        result = self.pool.state()["jobs"][0]
        self.assertEqual(result["status"], "failed")
        self.assertIn("no changes", result["error"])


if __name__ == "__main__":
    unittest.main()
