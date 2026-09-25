# Sumi agent chat — LF-34

An interactive design prototype backed by real native Codex sessions. Open
http://127.0.0.1:8771/. This is a reviewable first design, not an approved final UI.

- Quiet conversation sidebar, main chat, and collapsible activity inspector.
- Send, follow up, start a new conversation, and Stop. Enter sends; Shift+Enter adds a line.
- Each conversation owns a disposable workspace and persistent Codex thread ID.
  Each turn starts `codex exec --json` (or `exec resume <thread>`) using existing
  CLI authentication. It is not a continuously running model process.
- Defaults to GPT-6 Luna, low reasoning effort; model/effort selectors apply to the next turn. The installed model catalog and official
  model guidance identify Luna as the efficient tier; exact account pricing was
  not established. No automatic fallback to a more expensive model.
- Real JSONL events are forwarded through replayable SSE. This CLI emits agent
  message items, not token-by-token text deltas. There is no simulated typing.
- Native commands, completed responses, usage, and raw events are visible. Basic
  bold, inline code, and fenced code are rendered safely using DOM text nodes.
- Conversation history is server-persisted; drafts and selection are browser-local.
  SSE reconnects replay missed events using Last-Event-ID. One chat turn at a time.
- The Agentation toolbar feeds a separate six-worker Luna/JJ UI review pool.
  Saving a UI annotation starts work automatically, as in the prior pilot.
  The chat agent cannot modify the UI; reviewer workers only edit index.html.
- Published UI revisions automatically load while preserving comment-tool mode.
  Reloads defer during a running selected chat, focused composer, or annotation
  draft. Original review links remain pinned. Historical HTML uses today's backend.

Runtime stays under `.playground/chat-agent/`: `chat/conversations.json`, per-chat
workspaces and raw turn logs, plus `review/` containing the independent JJ repo,
review database, and original revisions. No credentials are written into source.
The local server binds to loopback and requires the per-instance token for POSTs.
Codex uses workspace-write with approvals disabled and a five-minute turn timeout.

## Run

Dependencies: Python 3, Node, JJ, signed-in Codex CLI, and the existing review
bundle dependencies (React, Agentation, esbuild, linkedom, pinned Prettier).
See the adjacent live-review README for dependency setup.

```sh
node experiments/live-review/build.mjs /path/to/review-dependencies "$PWD/.playground/chat-agent/review.js"
python3 experiments/agent-chat/server.py \
  --root "$PWD/.playground/chat-agent" \
  --bundle "$PWD/.playground/chat-agent/review.js" \
  --registry "$PWD/.playground/external-runs" \
  --dom-module /path/to/linkedom/esm/index.js \
  --formatter /path/to/prettier/bin/prettier.cjs
```

Source seeds a new review repository only. Existing repositories serve published
revisions, so edits to the source file require a checked publication. Bundle
changes are picked up on the next page load. Bebop on port 8770 remains separate.

## Verification

```sh
python3 experiments/agent-chat/test_server.py
node experiments/agent-chat/validate.mjs /path/to/linkedom/esm/index.js experiments/agent-chat/index.html
SUMI_PLAYWRIGHT=/path/to/playwright/index.mjs node experiments/agent-chat/test-browser.mjs
```

The browser test uses real Luna calls and leaves its conversation as evidence.
It exercises initial reply, resumed memory, file/tool use, token reporting, draft
and conversation restoration, and cancellation. Existing pool and live-reload
regressions cover integration and publication guards. This prototype does not
provide rich Markdown, attachments, permissions UI, or concurrent chat execution yet.

References: [Codex JSONL and resume](https://learn.chatgpt.com/docs/non-interactive-mode),
[available model guidance](https://learn.chatgpt.com/docs/models).

See [Luna review audit](LUNA-REVIEW.md) for the failed feedback implementations and
their repairs. Combined publications now require a real Chromium behavior check:

```sh
node experiments/agent-chat/validate-browser.mjs /path/to/playwright/index.mjs experiments/agent-chat/index.html
```

Pass `--browser-module /path/to/playwright/index.mjs` to the server; the default
is `.playground/live-tools/node_modules/playwright/index.mjs` in this repository.
Playwright and its Chromium browser must be installed for publication.
Escape dismisses an annotation draft first, then exits commenting mode.
