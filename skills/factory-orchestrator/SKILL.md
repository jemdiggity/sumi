---
name: factory-orchestrator
description: Work through an existing software-factory task tree, selecting eligible tasks, applying relevant skills, recording evidence, and adapting the queue. Use when asked to orchestrate or process factory tasks until completion or a real decision boundary.
---

# Process the task tree

Act as the coordinator of an existing task queue. A skill supplies instructions
to the current agent; it is not a background scheduler. Default to executing
serially in the current session. Do not spawn workers merely because tasks exist.

## Locate and reconcile state

Use the task source named by the user or project. In the Sumi playground it is
`tasks.json` at the repository root. Read it and relevant project instructions
before acting. Use factory-workflow for planning and replanning, factory-design
for representative artifacts, and factory-feedback for revision-specific review
when these skills are available. Read only those needed for the selected task.

The task tree contains stable IDs, titles, statuses, `depends_on`, `acceptance`,
`evidence`, optional `skills`, and recursive `children`. Children group work;
dependencies define eligibility. Honor dependencies on every ancestor as well
as on the selected task. Reject missing dependency IDs and cycles before doing
dependent work. A parent being proposed does not itself block a ready child.

Reconcile existing active tasks first. Inspect their artifacts and recorded run
state before resuming; do not assume an agent still runs because a task says
active. Do not repeat completed actions or silently take over another live run.

## Pick the next useful unit

Prefer an eligible leaf task within the user's requested scope. Dependencies
must be done with appropriate evidence, and any required approval must name an
artifact revision and scope. A ready label alone does not prove eligibility.
For a proposed task whose dependencies are met, confirm that scope is sufficiently
defined and already authorized, then mark it ready. Honor explicit priorities;
otherwise use task order, choosing work that resolves uncertainty or unblocks
other work when there is a clear reason to depart from that order.

If a task is too broad, introduce bounded children with stable new IDs and concrete
completion criteria. Record why the split helps. Do not repeatedly decompose work
instead of producing an artifact. Check new dependencies for cycles. Never broaden
the user's authorization by creating a child task.

## Execute and record

Persist `status: active` in the task store BEFORE starting the selected task's
substantive work, so the live sidebar immediately shows what is being worked on.
Saying a task is active in chat is not a substitute for modifying the task list.
Briefly state the intended result. Apply its
relevant skills and produce the artifact or change. Keep parent status coherent:
active while its child work proceeds, done only when its own criteria and required
children are satisfied. Preserve review gates on parents; completed children alone
do not establish stakeholder approval.

Persist each transition as it happens: active on starting, blocked when awaiting
a decision or external condition, done after verifying acceptance, or ready when
work is explicitly returned to the queue. In serial execution, keep one executing
leaf active; ancestors may also be active as grouping tasks. Do not activate a
future task just to make the sidebar look busy, or leave completed work active.

Update the task with artifact paths and revisions, meaningful verification, and
remaining decisions. Distinguish an experiment or mockup from implemented behavior.
Mark done only when acceptance criteria have evidence. For a blocker, use blocked
with a `blocked_reason` and the condition that would unblock it. For an approval
task, keep the task blocked pending the actual decision and record the concrete
artifact presented. Scope approval to what the user or stakeholder actually said.

Keep task IDs and existing fields. For a local JSON queue, re-read before writing,
preserve unrelated changes, and replace the file atomically. Use one coordinator
as the writer for this prototype. This is not a concurrent task-claim protocol;
parallel coordinators need actual locking or a transactional task store first.

After each meaningful result, reconsider the remaining graph and select the next
eligible task. Failed validation may require repair work, a design revision, or a
documented external blocker. Avoid unbounded retries of the same failing action.

## Decision boundaries and stopping

For new behavior, iterate with the user on a representative artifact before
autonomous implementation. Existing explicit approval remains valid for its
recorded revision and scope. Return materially changed behavior to review while
continuing independent approved tasks. Do not infer approval from silence, a
rendered preview, or a clean test run.

Continue within the user's execution request until the requested work is complete,
the user stops it, or no eligible work remains without a decision or external change.
At a decision boundary, present the artifact and the precise decision needed.
Do not poll indefinitely. End with completed IDs, artifact links, actual blockers,
and the next eligible action. Execution ends with the agent session unless a
separately implemented runner resumes it.

External issue updates, messages, publication, deployments, and spawning additional
agents retain their own authorization requirements. Task metadata and this skill
do not grant those permissions.
