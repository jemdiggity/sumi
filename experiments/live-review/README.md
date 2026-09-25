# Cowboy Bebop: live annotation → Luna pool → JJ preview

LF-30. Local interactive pilot, explicitly authorized by Jeremy on 2026-09-25:
comments on this page start work automatically. This overrides the earlier
manual-dispatch preference **only for this new pilot**. Existing prototype and
Agentation sessions are untouched.

Open http://127.0.0.1:8770/. Use Agentation at bottom right to select an element
and save a comment. The left panel shows queue/worker/publication state. Saving
sends immediately; editing creates a new immutable job. Delivery retries are
idempotent. Removing a browser annotation does not cancel already dispatched
work. Pause new work stops dispatch; active jobs continue. No external publishing.

Six on-demand native gpt-6-luna/medium worker slots, not prewarmed conversations.
Every job gets its own JJ workspace based on the exact revision annotated.
Comments include annotation metadata and the explorer's search/filter/detail
scene. Original links restore that scene. Repository mutations are serialized;
workers never concurrently edit the same working directory. All raw results,
failed attempts, and originals are retained.

The coordinator combines a candidate with the latest published revision in a
separate integration workspace. Conflicts or failed combined checks trigger one
bounded Luna reconciliation pass in that workspace. If checks still fail, the
last published preview stays available and the job shows failed. Successful
publication is a proposed fix, not reviewer acceptance. A new-revision link
appears without reloading the page being annotated. Plain questions/no file
change produce an answer without publishing an unnecessary revision.

React is used only for the Agentation toolbar. Its documented annotation callbacks
feed the local queue directly; this pilot does not route through Agentation MCP.
The explorer is vanilla HTML/CSS/JS. Queue/revisions are in SQLite; browser outbox
retries failed delivery. JSON exports are available from the panel's History link.

## Run

Requires Python 3, JJ, an authenticated Codex CLI, and Node. Build dependency root
must contain agentation 3.1.2, React/react-dom 19.2.0, and esbuild 0.25.10. The
existing /Users/jeremyhale/work/sumi-review-prototype supplies those locally.
DOM checking uses linkedom 0.18.13 installed in its .qa/node_modules.

```sh
mkdir -p .playground/live-bebop
node experiments/live-review/build.mjs /path/to/dependency-project "$PWD/.playground/live-bebop/review.js"
python3 experiments/live-review/server.py --root "$PWD/.playground/live-bebop" --bundle "$PWD/.playground/live-bebop/review.js" --registry "$PWD/.playground/external-runs" --dom-module /path/to/node_modules/linkedom/esm/index.js
```

Default port 8770; binds 127.0.0.1. `--workers` adjusts concurrency. Server restart
keeps queued jobs and published snapshots, and marks interrupted work for manual
retry instead of silently duplicating it. The process must remain running.
Starting again resumes the saved repository rather than replacing it from source.
Use a new `--root` to start a separate study. Native run records appear in Sumi's
existing session list. Worker and reconciliation attempts each have a 300s cap.

## Verification

- `SUMI_DOM_MODULE=/path/to/linkedom/esm/index.js python3 experiments/live-review/test_server.py`
- Six backend tests: duplicate delivery, edited snapshot, queue/restart state,
  malformed requests, successful publication, preservation on failed candidate,
  plus overlapping title edits exercising reconciliation (some grouped in tests).
- Two labelled real HTTP annotation payloads automatically dispatched native Luna
  jobs and published revisions in 9.99s and 24.05s. First attempts exposed JJ's
  exit-code-2 behavior for `resolve --list` with no conflicts; fixed by querying
  the conflicts revset first, with a clean-publication regression test.
- Both intended changes survive in latest HTML: search placeholder and illustration
  footer note. Original revision remains retrievable. Setup-test jobs are hidden
  from the main review panel but retained in History and SQLite.
- Page checks cover JS initialization, six-character roster, search empty state,
  details, crew filter, scene restoration, and conflict-marker absence.
- Chrome's native automation pipe failed to start, so the actual browser toolbar
  click flow and visual layout have not been verified in this session. Callback
  bundle builds; worker/queue/publication path has been exercised through HTTP.

Limits: no semantic correctness guarantee from a clean merge or DOM check, no
accounts/LAN service, no automated screenshot comparison, no warm-session reuse,
no intent grouping or cancellation of running work yet. Reconciliation receives
prior published feedback to help preserve intent but remains a model judgment.
