"""Durable review threads; jobs remain immutable submissions within a thread."""

import json
import uuid
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class ReviewThreads:
    def init_threads(self):
        self.db.executescript(
            """
          CREATE TABLE IF NOT EXISTS review_threads(id TEXT PRIMARY KEY, root_job TEXT NOT NULL, disposition TEXT NOT NULL DEFAULT 'open');
          CREATE TABLE IF NOT EXISTS review_actions(id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL);
        """
        )
        for row in self.db.execute(
            "SELECT id,payload FROM jobs ORDER BY created"
        ).fetchall():
            payload = json.loads(row["payload"])
            ident = payload.get("thread_id") or row["id"]
            self.db.execute(
                "INSERT OR IGNORE INTO review_threads VALUES (?,?,?)",
                (ident, row["id"], "open"),
            )
            if not payload.get("thread_id"):
                payload["thread_id"] = ident
                self.db.execute(
                    "UPDATE jobs SET payload=? WHERE id=?",
                    (json.dumps(payload), row["id"]),
                )
        self.db.commit()

    def attach_thread(self, job, payload):
        ident = payload.get("thread_id") or job
        if (
            payload.get("thread_id")
            and not self.db.execute(
                "SELECT 1 FROM review_threads WHERE id=?", (ident,)
            ).fetchone()
        ):
            raise ValueError("Unknown review thread")
        payload["thread_id"] = ident
        self.db.execute(
            "INSERT OR IGNORE INTO review_threads VALUES (?,?,?)", (ident, job, "open")
        )
        self.db.execute(
            "UPDATE review_threads SET disposition=? WHERE id=?", ("open", ident)
        )
        return payload

    def threads(self):
        with self.lock:
            result = []
            jobs = self.db.execute("SELECT * FROM jobs ORDER BY created").fetchall()
            grouped = {}
            for job in jobs:
                payload = json.loads(job["payload"])
                grouped.setdefault(payload.get("thread_id", job["id"]), []).append(
                    (job, payload)
                )
            for row in self.db.execute("SELECT * FROM review_threads").fetchall():
                entries = grouped.get(row["id"], [])
                if not entries:
                    continue
                original, payload = entries[0]
                latest, _ = entries[-1]
                state = latest["status"]
                state = (
                    "ready"
                    if state in ("published", "answered")
                    else (
                        "attention"
                        if state in ("failed", "needs attention", "interrupted")
                        else "working"
                    )
                )
                terminal = {
                    "published",
                    "answered",
                    "failed",
                    "needs attention",
                    "interrupted",
                }
                if any(job["status"] not in terminal for job, _ in entries):
                    state = "working"
                elif row["disposition"] in ("accepted", "reopened"):
                    state = row["disposition"]
                messages = []
                for job, p in entries:
                    outcome = json.loads(job["result"])
                    messages.append(
                        {
                            "id": job["id"] + "-user",
                            "role": "you",
                            "text": p["annotation"]["comment"],
                            "created": job["created"],
                            "revision": job["revision"],
                        }
                    )
                    if outcome.get("reply") or outcome.get("error"):
                        messages.append(
                            {
                                "id": job["id"] + "-agent",
                                "role": "agent",
                                "text": outcome.get("reply") or outcome["error"],
                                "created": outcome.get("finished_at", job["created"]),
                                "revision": outcome.get("published"),
                                "status": job["status"],
                            }
                        )
                for action in self.db.execute(
                    "SELECT * FROM review_actions WHERE thread_id=?", (row["id"],)
                ).fetchall():
                    messages.append(
                        {
                            "id": action["id"],
                            "role": "you",
                            "text": action["body"],
                            "created": action["created"],
                        }
                    )
                messages.sort(key=lambda m: m["created"])
                result.append(
                    {
                        "id": row["id"],
                        "title": payload["annotation"]["comment"],
                        "annotation": payload["annotation"],
                        "revision": original["revision"],
                        "scene": payload.get("scene", {}),
                        "status": state,
                        "job_status": latest["status"],
                        "messages": messages,
                        "created": original["created"],
                    }
                )
            return sorted(result, key=lambda t: t["created"])

    def thread_action(self, data):
        if not isinstance(data, dict):
            raise ValueError("Expected thread action object")
        ident, action = data.get("thread_id"), data.get("action")
        with self.lock:
            thread = next((t for t in self.threads() if t["id"] == ident), None)
            if not thread:
                raise ValueError("Unknown review thread")
            if action == "reply":
                text, request_id = data.get("message"), data.get("request_id")
                if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                    raise ValueError("Reply must contain 1–8000 characters")
                if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100:
                    raise ValueError("A reply request ID is required")
                # Retry the same request without duplicating work, including after publication.
                annotation = dict(
                    thread["annotation"], id="reply-" + request_id, comment=text
                )
                history = [
                    {
                        "role": m["role"],
                        "text": m["text"],
                        "revision": m.get("revision"),
                    }
                    for m in thread["messages"]
                ]
                return {
                    "id": self.submit(
                        {
                            "thread_id": ident,
                            "revision": data.get("revision"),
                            "scene": data.get("scene", {}),
                            "annotation": annotation,
                            "review_thread": {
                                "original_revision": thread["revision"],
                                "original_comment": thread["title"],
                                "messages": history[-40:],
                            },
                        }
                    )
                }
            if action not in ("accept", "reopen"):
                raise ValueError("Unknown thread action")
            if thread["status"] == "working":
                raise ValueError(
                    "Wait for the active agent before changing review status"
                )
            disposition = "accepted" if action == "accept" else "reopened"
            current = self.db.execute(
                "SELECT disposition FROM review_threads WHERE id=?", (ident,)
            ).fetchone()[0]
            if current != disposition:
                self.db.execute(
                    "UPDATE review_threads SET disposition=? WHERE id=?",
                    (disposition, ident),
                )
                self.db.execute(
                    "INSERT INTO review_actions VALUES (?,?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        ident,
                        action,
                        (
                            "Accepted this change."
                            if action == "accept"
                            else "Reopened for further review."
                        ),
                        now(),
                    ),
                )
                self.db.commit()
            return {"status": disposition}

    def eligible_jobs(self):
        active_threads = {
            json.loads(
                self.db.execute(
                    "SELECT payload FROM jobs WHERE id=?", (ident,)
                ).fetchone()[0]
            ).get("thread_id", ident)
            for ident in self.active
        }
        selected = []
        for row in self.db.execute(
            "SELECT * FROM jobs WHERE status='queued' ORDER BY created"
        ).fetchall():
            if len(selected) >= self.workers - len(self.active):
                break
            thread = json.loads(row["payload"]).get("thread_id", row["id"])
            if thread in active_threads:
                continue
            active_threads.add(thread)
            selected.append(row)
        return selected

    def prior_thread_messages(self, thread_id, job_id):
        messages = []
        with self.lock:
            for row in self.db.execute(
                "SELECT * FROM jobs ORDER BY created"
            ).fetchall():
                if row["id"] == job_id:
                    break
                payload = json.loads(row["payload"])
                if payload.get("thread_id") != thread_id:
                    continue
                messages.append(
                    {"role": "you", "text": payload["annotation"]["comment"]}
                )
                result = json.loads(row["result"])
                if result.get("reply") or result.get("error"):
                    messages.append(
                        {
                            "role": "agent",
                            "text": result.get("reply") or result["error"],
                        }
                    )
        return messages[-40:]
