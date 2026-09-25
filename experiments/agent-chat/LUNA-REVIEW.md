# Luna UI review audit — LF-35

Audited the eight user annotation jobs after the initial chat canary, their native
JSONL transcripts, candidate JJ diffs, and combined revision
`7e0191f2ae19a9be3464a552b4fb9800f8c2a0fb`. The repair is published as
`9fd605298277a01685a164484ed0249d97fe07eb`. Original review snapshots,
transcripts, and responses are retained. Publication is not reviewer acceptance.

| Request / job | What Luna actually did | Finding and correction |
| --- | --- | --- |
| Expand responses, e5ee362f53a9 | Added disclosure code and filtered activity by `item.turn` | Broken: the stream has `event.turn`, not `event.item.turn`. Zero matching tool items meant no disclosure. Preserve turn on item ingestion; show usage/elapsed and emitted reasoning summaries in every response disclosure. Keep expanded state across subsequent events. |
| Exit commenting mode, 5fbfc5d45ec8 | Explicitly said no commenting state existed in index.html, then added Escape to the unrelated inspector | Wrong behavior. Removed that handler; enabled Agentation's keyboard support in the injected toolbar. Browser checked Escape exits mode; a draft takes one Escape to dismiss first. |
| Drill into conversation, 72a387285eac | One-line replacement of “This turn” with “Turn details are in the conversation” | No interaction implemented. Move usage, elapsed, model/effort, and activity into response details; keep session inspector optional. |
| Session tools/thinking, 8e51879c756c | Put expandable activity in the right sidebar | Partial/wrong location. Now available inside the conversation. Only summaries actually emitted by Codex are shown; absent summaries are identified rather than invented. |
| Model/effort, c1148ac26502 | Returned blocked because its HTML-only scope excluded backend changes | Correct escalation, unfinished request. Coordinator added model/effort selects, an installed-model catalog, server-side validation, per-turn persistence, and native argv selection for both new and resumed threads. |
| Skin picker, 9f1bb732a9b2 | Added Modern/TUI selector, CSS, persistence, scene hook | Implemented. Fixed light message backgrounds undermining TUI contrast; browser fixture verifies selection and dark message backgrounds. |
| Remove name, 1ebfe9d3d69e | Removed name text | Implemented. Also removed empty completed-message speaker rows and redundant thinking text. |
| Animate working, e8e91366a43b | Added a CSS pulse and busy row | Implemented. Retained one working indicator and added reduced-motion behavior. |

## Why publication did not catch it

The transcript evidence consists of source searches, patches, and rereading the
modified code. There were no actual browser interaction tests in those worker
runs. Existing coordinator validation checked script initialization, DOM IDs, and
scene/draft hooks; it did not replay a conversation or exercise response expansion.
A nonempty diff passed even when it changed the wrong behavior.

My worker setup also hid relevant context: Agentation is injected outside the
editable HTML and backend changes are disallowed. That restriction was appropriate
for isolated UI edits, but workers needed an explicit boundary and a route to
report blocked cross-layer requests, rather than substitute a nearby control.
The prompt's emphasis on tiny patches also encouraged the label-only shortcut.

## Changes to the workflow

- Worker prompt now requires the smallest *complete behavior*, forbids substituting
  a label/different control, and requires blocked outcomes for out-of-scope work.
- Chat-specific worker context explains the injected toolbar, actual stream data
  shape (including turn identity), supported chat APIs, and available model catalog.
- Every combined chat preview must pass `validate-browser.mjs` in real Chromium
  before publication. Fixtures verify per-turn tool output, available reasoning
  summaries, usage, open disclosure persistence, no cross-turn leakage, busy state,
  model/effort request payload, and TUI message backgrounds. Historical candidates
  get structural checks first; browser checks run on the combined revision so
  a valid patch against an older page is not rejected for missing newer features.
- This protects known interactions, not all future semantics. New requested
  behaviors still need an appropriate acceptance check and reviewer feedback.
- Review rows retain original replies/publications and add audit findings plus
  the repair revision. The local pre-repair database was backed up.

## Evidence

- New browser gate fails against the audited original with “Response must expose
  turn details: 0 !== 1”; repaired source passes.
- Real-browser/native-Luna smoke test verified response, resumed conversation,
  workspace command output inside expanded response, usage, draft/history reload,
  Stop, and absence of browser exceptions.
- Actual Agentation toolbar passed Escape mode-exit and draft-then-mode behavior.
- Five chat backend tests pass, including validated model/effort propagation into
  the resume command; nine pool regressions pass. Model catalog exposes installed
  Luna, Sol, and Astra. No paid comparison of all three models was run.
- Audit snapshots and candidate diffs: `.playground/chat-agent/audit/`.
  Native worker transcripts: `.playground/external-runs/chat-ui-<job>-edit/events.jsonl`.
