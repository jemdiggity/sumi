#!/usr/bin/env python3
"""Local chat design pilot: native Codex JSONL -> replayable browser SSE."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
import uuid
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "live_review", HERE.parent / "live-review/server.py"
)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ChatPool(review.Pool):
    validator = HERE / "validate.mjs"
    page_instructions = "Preserve chat APIs, streaming, session history, composer, and window.SumiScene get/set. Do not change backend paths or request/response contracts."
    initial_title = "Initial Sumi agent chat"
    run_prefix = "chat-ui"
    task_id = "LF-34"
    app_name = "Sumi chat review"
    worker_context = """The annotation toolbar is Agentation, injected by /assets/review.js after index.html.
It is NOT the activity inspector. Toolbar changes (including keybindings) require
coordinator work outside index.html; return blocked for them.
Chat SSE event shape: {type, turn, item:{id,type,text,command,aggregated_output}}.
The turn is on the EVENT, not item. IDs may repeat across turns. Reasoning items
contain only provider-emitted summaries; never fabricate missing thinking.
/chat/state returns {model,models:[{id,name,efforts}],conversations:[{id,title,status,model,effort}]}.
/chat/send accepts {conversation,message,model,effort}. Model/effort apply to the next turn.
/chat/events?id=... emits chat.user, native Codex events, chat.done; chat.user includes model/effort.
SumiScene preserves browser state. Keep working behavior and drafts across refreshes.
The coordinator runs real-browser fixtures for turn details, open-state persistence,
model selection, thinking indicator, and skins before publication. Those fixtures
protect existing behavior; you still must verify the requested new interaction.
"""

    def __init__(self, *args, browser_module=None, **kwargs):
        self.browser_module = (
            browser_module
            or HERE.parents[1]
            / ".playground/live-tools/node_modules/playwright/index.mjs"
        )
        super().__init__(*args, **kwargs)

    def check(self, ws):
        structural = super().check(ws)
        # Historical candidates may predate current behavior. Apply the browser
        # contract to the combined preview, not an unmerged historical branch.
        if ws != self.repo and not ws.name.startswith("merge-"):
            return structural
        result = subprocess.run(
            [
                "node",
                str(HERE / "validate-browser.mjs"),
                str(self.browser_module),
                str(ws / "index.html"),
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        if result.returncode:
            raise RuntimeError(
                "Browser behavior check failed: "
                + (result.stdout + result.stderr)[-2500:]
            )
        return structural + "\n" + result.stdout


class Chats:
    def __init__(self, root, model="gpt-6-luna"):
        self.root = root
        self.model = model
        self.models = [
            {"id": model, "name": "Luna", "efforts": ["low", "medium", "high"]}
        ]
        try:
            cached = json.loads((Path.home() / ".codex/models_cache.json").read_text())
            available = [
                {
                    "id": m["slug"],
                    "name": m["display_name"],
                    "efforts": [
                        e["effort"]
                        for e in m["supported_reasoning_levels"]
                        if e["effort"] != "ultra"
                    ],
                }
                for m in cached["models"]
                if m["slug"] in ("gpt-6-luna", "gpt-6-sol", "gpt-6-astra")
                and m.get("visibility") == "list"
            ]
            if available:
                self.models = available
        except (OSError, KeyError, ValueError):
            pass
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.processes = {}
        self.closed = False
        self.file = root / "conversations.json"
        self.rows = json.loads(self.file.read_text()) if self.file.exists() else {}
        for row in self.rows.values():
            if row["status"] == "running":
                row["status"] = "interrupted"
                row["events"].append(
                    {"type": "chat.done", "status": "interrupted", "turn": row["turn"]}
                )
        self.save()

    def save(self):
        review.atomic(self.file, self.rows)

    def state(self):
        with self.lock:
            return {
                "model": self.model,
                "models": self.models,
                "conversations": [
                    {k: v for k, v in row.items() if k != "events"}
                    for row in self.rows.values()
                ],
            }

    def emit(self, ident, event):
        with self.changed:
            row = self.rows[ident]
            event["turn"] = row["turn"]
            row["events"].append(event)
            if event["type"] == "thread.started":
                row["thread"] = event["thread_id"]
            self.save()
            self.changed.notify_all()

    def send(self, data):
        text = data.get("message", "")
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            raise ValueError("Write a message (maximum 16,000 characters).")
        with self.lock:
            if self.closed:
                raise ValueError("Server is shutting down.")
            if any(r["status"] == "running" for r in self.rows.values()):
                raise ValueError(
                    "An agent is already working. Stop it or wait before sending."
                )
            ident = data.get("conversation")
            if ident is not None and ident not in self.rows:
                raise ValueError("Unknown conversation.")
            previous = self.rows.get(ident, {})
            model = data.get("model", previous.get("model", self.model))
            effort = data.get("effort", previous.get("effort", "low"))
            choice = next((m for m in self.models if m["id"] == model), None)
            if not choice or effort not in choice["efforts"]:
                raise ValueError("Unsupported model or reasoning effort.")
            if not ident:
                ident = uuid.uuid4().hex[:12]
                self.rows[ident] = {
                    "id": ident,
                    "title": text.strip()[:60],
                    "thread": None,
                    "status": "idle",
                    "turn": 0,
                    "events": [],
                    "created": review.stamp(),
                }
            row = self.rows[ident]
            row["model"], row["effort"] = model, effort
            row["turn"] += 1
            row["status"] = "running"
            row["stop_requested"] = False
            self.emit(
                ident,
                {"type": "chat.user", "text": text, "model": model, "effort": effort},
            )
            threading.Thread(target=self.run, args=(ident, text), daemon=True).start()
            return {"id": ident}

    def stop(self, ident):
        with self.lock:
            if ident not in self.rows:
                raise ValueError("Unknown conversation.")
            self.rows[ident]["stop_requested"] = True
            process = self.processes.get(ident)
            if process:
                self.terminate(process)
            self.save()

    @staticmethod
    def terminate(process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def run(self, ident, text):
        workspace = self.root / "workspaces" / ident
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "AGENTS.md").write_text(
            "You are the live agent in a chat UI design prototype. Answer conversationally and concisely. "
            "Use tools only when the user asks for work needing them. Work only in this disposable workspace. "
            "Do not inspect unrelated directories or start other agents. Do not edit the chat UI or review service.\n"
        )
        with self.lock:
            selected_model = self.rows[ident].get("model", self.model)
            selected_effort = self.rows[ident].get("effort", "low")
        args = [
            "codex",
            "-a",
            "never",
            "exec",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-s",
            "workspace-write",
            "--json",
            "-m",
            selected_model,
            "-c",
            f'model_reasoning_effort="{selected_effort}"',
            "-c",
            "features.multi_agent=false",
        ]
        with self.lock:
            thread = self.rows[ident]["thread"]
            turn = self.rows[ident]["turn"]
        if thread:
            args += ["resume", thread, "-"]
        else:
            args += ["-"]
        started = time.monotonic()
        completed = False
        failed = False
        process = None
        timer = None
        try:
            with (workspace / f"turn-{turn}.stderr").open("w") as err, (
                workspace / f"turn-{turn}.jsonl"
            ).open("w") as log:
                process = subprocess.Popen(
                    args,
                    cwd=workspace,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=err,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
                with self.lock:
                    self.processes[ident] = process
                    if self.rows[ident]["stop_requested"]:
                        self.terminate(process)

                def timeout():
                    self.terminate(process)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

                timer = threading.Timer(300, timeout)
                timer.daemon = True
                timer.start()
                process.stdin.write(text)
                process.stdin.close()
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    completed |= event.get("type") == "turn.completed"
                    failed |= event.get("type") in ("turn.failed", "error")
                    self.emit(ident, event)
                code = process.wait()
                failed |= code != 0
                if code and not self.rows[ident]["stop_requested"]:
                    self.emit(
                        ident,
                        {
                            "type": "chat.error",
                            "message": f"Codex exited with code {code}. See local turn-{turn}.stderr for diagnostics.",
                        },
                    )
        except Exception as e:
            failed = True
            self.emit(ident, {"type": "chat.error", "message": str(e)})
        finally:
            if timer:
                timer.cancel()
            if process and process.poll() is None:
                self.terminate(process)
            with self.lock:
                self.processes.pop(ident, None)
                row = self.rows[ident]
                row["status"] = (
                    "stopped"
                    if row["stop_requested"]
                    else ("idle" if completed and not failed else "failed")
                )
                self.emit(
                    ident,
                    {
                        "type": "chat.done",
                        "status": row["status"],
                        "elapsed": round(time.monotonic() - started, 2),
                    },
                )

    def close(self):
        with self.lock:
            self.closed = True
            for ident in list(self.processes):
                self.stop(ident)


class Handler(review.Handler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/chat/state":
            return self.respond(200, self.server.chats.state())
        if path == "/chat/events":
            ident = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            chats = self.server.chats
            with chats.lock:
                if ident not in chats.rows:
                    return self.respond(404, {"error": "Unknown conversation"})
            try:
                cursor = max(0, int(self.headers.get("Last-Event-ID", "0")))
            except ValueError:
                cursor = 0
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while not chats.closed:
                    with chats.changed:
                        events = list(chats.rows[ident]["events"][cursor:])
                        if not events:
                            chats.changed.wait(timeout=10)
                    for event in events:
                        cursor += 1
                        self.wfile.write(
                            f"id: {cursor}\ndata: {json.dumps(event)}\n\n".encode()
                        )
                    if not events:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                self.close_connection = True
            return
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/chat/"):
            return super().do_POST()
        import hmac

        if not hmac.compare_digest(
            self.headers.get("X-Sumi-Token", ""), self.server.pool.token
        ):
            return self.respond(403, {"error": "Invalid local session token"})
        origin = self.headers.get("Origin")
        if origin and origin not in (
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        ):
            return self.respond(403, {"error": "Wrong origin"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Object required")
            if self.path == "/chat/send":
                return self.respond(202, self.server.chats.send(data))
            if self.path == "/chat/stop":
                self.server.chats.stop(data.get("conversation"))
                return self.respond(200, {"ok": True})
            return self.respond(404, {"error": "Unknown action"})
        except (ValueError, TypeError) as error:
            return self.respond(400, {"error": str(error)})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--dom-module", type=Path, required=True)
    p.add_argument("--formatter", type=Path)
    p.add_argument("--port", type=int, default=8771)
    p.add_argument("--browser-module", type=Path)
    a = p.parse_args()
    pool = ChatPool(
        a.root / "review",
        HERE / "index.html",
        a.bundle,
        a.registry,
        a.dom_module,
        formatter=a.formatter,
        browser_module=a.browser_module,
    )
    chats = Chats(a.root / "chat")
    server = review.ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    server.pool, server.chats = pool, chats
    threading.Thread(target=pool.schedule, daemon=True).start()

    def close(*_):
        chats.close()
        pool.close()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, close)
    signal.signal(signal.SIGINT, close)
    print(f"Sumi agent chat: http://127.0.0.1:{a.port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        chats.close()
        pool.close()
        server.server_close()


if __name__ == "__main__":
    main()
