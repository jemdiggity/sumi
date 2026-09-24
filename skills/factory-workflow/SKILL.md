---
name: factory-workflow
description: Select a starting workflow template for a software-factory task and evolve its plan, dependencies, artifacts, and evidence. Use for factory intake from tracked issues, product requests, engineering ideas, or maintenance work, and for revising an existing factory workflow.
---

# Evolving factory workflow

Maintain enough explicit structure for a person or another agent to understand
what is happening and resume it. Choose activities from the current need;
there is no mandatory design/build/review sequence.

## Route incoming work

Start from the user's prompt and the available source material. Distinguish
where a request came from (Linear, GitHub, product, engineering, or direct input)
from what work it needs (bug repair, defined feature, product discovery,
engineering exploration, or maintenance/refactoring). A GitHub issue can contain
any of these; its location alone does not select the execution template.

Read [references/task-templates.md](references/task-templates.md) for intake and
starting plans. Select the best-fitting template, name it and briefly explain
why, then instantiate only the relevant tasks and dependencies. Record the
source reference, template ID/version, and material assumptions in workflow
state. Treat this as a starting plan, not a mandatory checklist.

Honor explicit user routing. When requests mix types, choose a primary template
and borrow relevant activities from another, or create linked workstreams if
their outcomes are distinct. Ask a question only when ambiguity materially
changes the outcome; otherwise state a provisional classification and proceed.
Reclassify when evidence warrants it, recording why and preserving existing work.

## Durable state

Use the project's existing task store when one exists. Otherwise begin with
one local Markdown workflow document; do not introduce a service or database
just to hold a plan. Tell the user where the state lives.

Record the desired outcome, observable completion criteria, user constraints,
and unresolved decisions. Give active tasks stable IDs, a concrete intended
result, a status, and dependencies when needed. Attach artifact paths/revisions
and evidence of completion to the task. Add ownership or agent-run IDs only
when actual runners exist. A terminal pane is a view, never a task identity.

Use these task statuses initially: proposed, ready, active, blocked, done,
superseded. A blocked task names what would unblock it. Superseded work keeps
its history and points to its replacement. These are local task statuses, not
instructions to change any platform goal status.

## Select and revise work

For new capabilities and material behavior changes, front-load iterative design:
use a representative mockup, prototype, or written spec to reach stakeholder
agreement before autonomous build work. Use the available factory-design skill
for that loop. Approval is tied to an artifact revision and a bounded scope;
record it as an explicit dependency of the corresponding implementation tasks.
Already-approved requirements can satisfy this dependency. Routine repairs to
agreed behavior and behavior-preserving maintenance need not invent a new product
approval ceremony. Apply the user's explicit approval requirements in either case.

Do not require the whole product to be specified before building an approved
slice. Design can continue for other slices, and discoveries can send affected
work back through review. Early feasibility experiments support design when
needed; broad implementation and cross-layer build prototypes follow agreement.

Choose the next useful action from ready work using dependencies, uncertainty,
and the user's priorities. Inspection, an experiment, implementation, or review
can each be the right next action. Apply an available specialist skill when it
helps this action; do not load all skills or invent missing capabilities.

When evidence changes the plan, split, combine, add, remove, or reorder planned
work. Record the reason and affected task IDs in a brief decision entry.
Preserve completed evidence and stable references. Check for dependency cycles
and dependents whose assumptions or acceptance criteria are now invalid.
Plan changes do not rewrite the user's objective or authorize new side effects.
Ask for a decision only when the change actually requires one; continue useful
independent work when possible.

Revisit structure at meaningful boundaries: a finding, failed check, user
correction, completed artifact, or review result. Avoid rewriting the workflow
after every command. For a small task, a single task entry may be enough.

## Execution and handoff

Use native tools for editing, agent execution, previews, and collaboration.
Keep backend-specific IDs alongside the stable local task ID. Do not assume
that synchronizing Git commits synchronizes Forgejo or Radicle discussions.
Launch additional agents only when the user or applicable instructions authorize
delegation; a proposed owner in a plan is not a running agent.

After an action, record the result, relevant artifact revision, validation, and
what it makes possible next. Mark a task done only when its completion criteria
have evidence; distinguish implemented, reviewed, and verified when they differ.
Finish a handoff with the next useful action and any actual blocker.

Treat task-specific replanning separately from editing reusable skills. Change
a reusable skill when requested or when the user has authorized such updates,
not merely because one task required a different sequence.
