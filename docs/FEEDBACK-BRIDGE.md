# Local mockup feedback bridge

Product brief · revision 1 · 2026-09-24.

Proposed first measured Astra/Sol/Luna feature, replacing the larger parallel
workspace as the competition candidate. The existing workspace mockup is the
review target. These are product requirements, not the measured Astra technical
design. No comparative implementations have been launched.

## Intended experience

Jeremy annotates a locally served HTML mockup using Review.js and explicitly
sends the review. An agent retrieves the saved feedback when Jeremy asks,
reopens the reviewed revision and scene, and replies or proposes a fix.
Agent replies appear automatically while the review is open. Jeremy decides
whether to resolve or reopen each feedback item.

## Decisions confirmed by Jeremy

The following seven answers were explicitly supplied in this conversation:

1. **Local only:** one reviewer on this computer, no accounts. LAN sharing and
   multi-user coordination are outside the first slice.
2. **Snapshot submission:** Send review creates an immutable snapshot. Later
   annotation edits become a new submission. A transport retry must not create
   a duplicate submission.
3. **Reviewer-owned resolution:** the agent replies and proposes fixes; Jeremy
   resolves or reopens feedback. Agent completion does not close an item.
4. **Original anchors:** annotations stay on the original artifact revision,
   with links to proposed fixes. No automatic migration onto newer content.
5. **Reproducible context:** retain the exact revision and scene. Screenshot
   capture is excluded from this slice.
6. **Explicit agent work:** submitting feedback only saves it. Jeremy asks the
   agent to retrieve and address it; submission never launches an agent.
7. **Automatic reply updates:** while a review is open, agent replies appear
   without a manual refresh. Polling versus streaming is a design choice.

## Proposed supporting contract

These details make the decisions testable; they are recommendations rather
than additional user answers:

- Serve an immutable artifact revision, identified by a manifest/content hash
  rather than a mutable URL or Git commit alone. Preserve each annotation's
  scene at creation, including selected task, tab, and relevant expanded state.
- Submit stable annotation IDs and a submission ID. Retrying an identical
  submission returns its original receipt; reusing its ID with changed content
  produces an explicit error. Later snapshots remain traceable to earlier ones.
- Submission contents are immutable. Replies, proposed fixes, resolution, and
  reopening are separately recorded history, not edits to the submitted text.
- Provide CLI operations to list/read pending feedback and add replies or fix
  proposals, including machine-readable output. MCP is not required.
- A successful submission receipt means the review is persisted. Restarts and
  overlapping server/CLI writes must not lose acknowledged feedback.
- Browser updates show connection failure and recover without duplicating
  replies. A proposed acceptance target is replies visible within five seconds
  in an active foreground review, and reconciliation on returning to the page.
- A proposed fix references its target artifact revision. It does not retarget
  the original annotation or resolve it automatically.
- Review.js supplies annotations; a small local service supplies persistence
  and agent access. The current static file server does not implement this.
- The present mockup preview uses a sandboxed iframe. The test fixture should
  put the annotation toolbar and mockup in the same document, avoiding a
  cross-frame selection dependency.

## Evaluation scenarios to freeze before measured design

1. Annotate two different scenes, submit, and reopen each exact reviewed state.
2. Retry after a lost response: one submission, with a stable receipt.
3. Edit and resubmit: preserve both snapshots and their annotation lineage.
4. Restart the service: acknowledged feedback and discussion survive.
5. Retrieve feedback through the CLI, add a reply and fix proposal, and observe
   them automatically in the open browser review.
6. Publish a new mockup revision: original anchors and scene remain intact.
7. Propose a fix: feedback stays open until reviewer resolution; reopening
   preserves prior replies and decisions.
8. Interrupt connectivity: report failure, retain unsent work, and recover
   without silently duplicating feedback or losing replies.

Use the four-arm protocol in `MODEL-EXPERIMENT.md`: Astra continues after its
design; fresh Sol, Astra, and Luna implement the same frozen design. Freeze the
product brief, repository base, checks, and repair allowance first. Design,
implementation, review, and repair all count toward the comparison.

These answers settle the main product choices. They do not record approval of
an unseen technical design or claim any experiment result.
