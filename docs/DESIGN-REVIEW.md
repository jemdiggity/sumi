# Review: task inspection and artifact feedback

Revision 1 · proposed · no stakeholder agreement recorded.

Open `mockups/factory.html` in a browser, or use the running local preview linked
from the latest session response. This is a standalone, offline-capable mockup;
no external fonts, scripts, accounts, or services are needed.

## Try the proposed interaction

1. Select **Task list and details**. The selected task changes, but **Working now**
   remains independent. All three example tasks refer to the same design artifact.
2. Open **Task details** to inspect dependencies and completion criteria.
3. Return to **Proposal**, then **Comment on this behavior**. Enter feedback; it
   is associated with the selected task, artifact revision, and passage anchor.
4. Simulate an agent acknowledgment. Acknowledgment leaves the request unresolved.
5. Simulate approval, then a material revision. Approval applies only to the earlier
   revision, and older comments are flagged for rechecking.
6. Explore the empty queue, failed run, and completed task states. Everything in
   these examples is simulated; a mockup button cannot start work or approve it.

## Proposed first implementation slice

Task selection, a detail view, and opening the selected task's artifact using
existing terminal/browser tools. Persist feedback with task ID, artifact revision,
anchor, and disposition. Keep selected task separate from executing task.

Agent scheduling, parallel workers, WAN collaboration, publishing, and deployments
are outside this slice. Prototype the persistence and feedback plumbing after
agreement; exact implementation tasks should be refined from the reviewed artifact.

## Decisions for Jeremy

- Does selecting a task without switching the running agent fit how you want to work?
- Is this first slice useful enough, or should another interaction come first?
- What should change in the proposal before it becomes the build reference?

Approval can be recorded later against the hashes in .sumi/tasks.json. Reviewing or
clicking the mockup does not by itself authorize implementation.

## Validation and limits

DOM checks covered selection independence, comments anchored to task/revision,
agent acknowledgment, simulated agreement, invalidation on material revision,
empty/failed/completed states, and reset. JavaScript syntax and local HTTP serving
were checked. Browser automation was unavailable, so visual layout has not yet
been verified in a real browser.

Comments and agreement are in-memory demo data. The mockup does not write .sumi/tasks.json.
Live task state remains in that JSON file and is shared by the tmux and cmux views.

## Evidence from using the workspace

The real task sidebar and artifact viewers are still disconnected: viewers always
open WORKSPACE.md regardless of the task. This is the concrete improvement driving
the design, rather than a hypothetical need for a new desktop application.
