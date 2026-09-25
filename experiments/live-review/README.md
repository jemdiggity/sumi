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
separate integration workspace. Slow reconciliation and validation run outside
the publication lock. Before publishing, the coordinator checks that the live
revision is still the one it merged; if it advanced, the reconciled candidate is
merged with the new head and checked again (at most three merge attempts).
Conflicts or failed combined checks trigger a bounded Luna reconciliation pass
for that attempt, without holding up independent clean results. If checks still fail, the
last published preview stays available and the job shows failed. Successful
publication is a proposed fix, not reviewer acceptance. A new-revision link
appears without reloading the page being annotated. Workers return a structured outcome. A claimed edit with no file diff fails;
other incomplete/no-change outcomes need attention. Genuine answers produce no
new revision. Formatting alone does not count as an edit.

React is used only for the Agentation toolbar. Its documented annotation callbacks
feed the local queue directly; this pilot does not route through Agentation MCP.
The explorer is vanilla HTML/CSS/JS. Queue/revisions are in SQLite; browser outbox
retries failed delivery. JSON exports are available from the panel's History link.

## Run

Requires Python 3, JJ, an authenticated Codex CLI, and Node. Build dependency root
must contain agentation 3.1.2, React/react-dom 19.2.0, and esbuild 0.25.10. The
existing /Users/jeremyhale/work/sumi-review-prototype supplies those locally.
DOM checking uses linkedom 0.18.13 installed in its .qa/node_modules.
Source normalization uses Prettier 3.6.2; install it locally with
`npm install --prefix .playground/live-tools --ignore-scripts prettier@3.6.2`.

```sh
mkdir -p .playground/live-bebop
node experiments/live-review/build.mjs /path/to/dependency-project "$PWD/.playground/live-bebop/review.js"
python3 experiments/live-review/server.py --root "$PWD/.playground/live-bebop" --bundle "$PWD/.playground/live-bebop/review.js" --registry "$PWD/.playground/external-runs" --dom-module /path/to/node_modules/linkedom/esm/index.js --formatter "$PWD/.playground/live-tools/node_modules/prettier/bin/prettier.cjs"
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

## Runner v2 verification (2026-09-25)

The baseline and live HTML/CSS/JS/SVG are formatted. Live revision
80a648f88f0f612c76fcbec48a579a22c1cc34a6 preserves prior published changes;
its longest line is 126 characters (previously 9,368). Original snapshots remain
immutable. Even jobs targeting an old revision get formatted source, snapshotted
before the worker starts; formatter changes cannot masquerade as a worker edit.
Prettier uses an explicit empty ignore file so `.playground` is never skipped.

Worker guidance: worker-prompt.md. Reconciliation guidance: reconcile-prompt.md.
Each reconciler receives read-only reviewed/current/candidate HTML plus intent
context. The coordinator requests Git diff3-style markers through JJ's per-command
configuration; the prompt also explains snapshot-format fallback and longer
markers. See [JJ's documented marker formats](https://www.jj-vcs.dev/latest/conflicts/).
No global JJ configuration is changed. Structured results use result.schema.json.

Nine regression tests pass, including a slow conflicting repair concurrent with
a clean publication, remerging the slow result against the advanced head,
no-op edit-claim rejection, and formatting inside ignored directories. Run with
`SUMI_DOM_MODULE` and `SUMI_FORMATTER` set to the local module/CLI paths.

Isolated native canary: one CSS variable edit used 8.98 seconds in Luna and
11.67 seconds through publication (215 output tokens). A deliberate title
conflict, with synthetic side edits, was resolved by real Luna in 28.11 seconds
and published with both title changes intact. These are smoke checks, not a
controlled comparison. See runner-v2-verification.json for sessions and phases.

Job records now include phase timestamps. Original no-op requests 115880ab53ab
and 485eb742a16a were relabelled needs attention with the audit finding; their
original replies/workspaces were retained. They were not silently retried.
