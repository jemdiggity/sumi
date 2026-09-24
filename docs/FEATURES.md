# Sumi feature list

Revision 1 · 2026-09-24 · Draft for discussion, not an approved build backlog.

Sumi is a lean software factory: a human or agent turns a request into a useful
artifact, iterates with stakeholders, delegates bounded work, and brings back
evidence for review. Tasks and their history survive changes of agent, terminal,
editor, workspace host, and reviewer.

This draft combines Jeremy's stated requirements, the working Sumi prototype,
and a [comparison of seven related products](PRODUCT-RESEARCH.md). Priorities
below are recommendations to revise together.

## Product shape

Sumi should own the task graph, workflow decisions, artifact revisions, feedback
links, and run handoffs. Existing tools provide terminals, agents, editors,
browsers, Git operations, and collaboration surfaces. A CLI exposes the same
operations to humans and agents. Small TUIs and browser pages present that state.

The first user is a developer coordinating several pieces of work. A stakeholder
should be able to review a proposal or preview without installing an agent CLI.
A second developer should be able to take over a task without reconstructing its
history from terminal scrollback.

Local operation is the baseline; a LAN server is an optional next deployment.
An external model provider can still receive context from its agent client:
locally hosted orchestration and locally hosted inference are separate choices.

## Feature catalog

**Working** means exercised in this prototype, not production completeness.
**Partial** means some mechanics or skills exist. **Proposed** means future work.
Feature IDs are discussion references, not automatically scheduled tasks.

### Understand and shape the work

| ID | Feature and desired behavior | Sumi today | Priority |
| --- | --- | --- | --- |
| F01 | Intake from a prompt, GitHub/Linear issue, product request, engineering idea, or maintenance need. Preserve source and acceptance criteria. | Partial: workflow skill; no issue import command. | Core |
| F02 | Choose and adapt a starting workflow: bug repair, defined feature, discovery, exploration, maintenance. Add, skip, repeat, or replace activities as evidence changes. | Partial: composable skills and templates. | Core |
| F03 | Recursive tasks and dependencies. Show what is eligible, blocked, active, or awaiting review, with reasons. Split work while preserving its parent intent. | Partial: tree, dependency validation, sidebar, locked outcomes; no full task-edit CLI. | Core |
| F04 | A durable task brief containing objective, constraints, approved scope, relevant context, and current handoff. | Partial: task and prompt snapshots; artifacts scattered across files. | Core |
| F05 | Explore alternatives with sketches, Markdown, HTML, diagrams, or executable prototypes before committing to an approach. | Partial: design skill and a standalone mockup. | Core |

### Iterate with people

| ID | Feature and desired behavior | Sumi today | Priority |
| --- | --- | --- | --- |
| F06 | Artifact registry: open the current proposal, preview, diff, or test result for a task; retain earlier revisions. | Partial: artifact references and viewers; no registry command. | Core |
| F07 | Review Markdown, HTML/mockups, and code. Anchor comments to the reviewed revision and passage, element, screenshot region, or diff line. | Partial: feedback skill and actual local Radicle round-trip; no integrated annotation UI. | Core |
| F08 | Route feedback to the responsible task/agent; capture a reply, changed artifact, or explicit defer/reject reason. | Partial: manual, revision-specific feedback mapping. | Core |
| F09 | Record agreement on a bounded slice. Preserve unaffected approvals when the plan changes; revisit only materially changed behavior. | Partial: skill guidance and recorded scope; no enforced approval object. | Core |
| F10 | Share a review link on the LAN with comments and reviewer identity. Support asynchronous review before adding simultaneous editing. | Proposed. | Next |

### Execute and recover

| ID | Feature and desired behavior | Sumi today | Priority |
| --- | --- | --- | --- |
| F11 | Agent-operable CLI: create/edit tasks, inspect capabilities, launch work, retrieve results, and make explicit handoffs using stable IDs and structured output. | Partial: prepare/start/inspect/resume/task outcomes exist; no complete discovery or task CRUD surface. | Core |
| F12 | Provider adapters for native Codex, Claude Code, and other CLIs. Separate interactive sessions from unattended execution and report supported capabilities. | Partial: managed Codex exec only; other CLIs can run manually. | Core |
| F13 | Workspace adapters: use Zellij, tmux, cmux, or another host without changing task identity. Open editors and previews where supported. | Partial: three workspace experiments; managed runs only support Zellij. | Core |
| F14 | Parallel worktrees, task claims, durable attempts, exact conversation resume, failure recovery, and preservation of unfinished work. | Working: bounded Codex/Zellij slice with leases and regression tests. | Core |
| F15 | Project setup/run/teardown recipes, assigned ports, dependency preparation, and explicit environment-file handling. | Proposed. Worktree separation currently covers files, not services or databases. | Next |
| F16 | Cross-repository tasks with coordinated workspaces and contract/version dependencies. | Proposed. | Later |
| F17 | Bounded queue execution: choose eligible tasks, cap concurrency, stop at a real blocker, and recover after coordinator restart. | Partial: orchestration skill in the current agent session; no persistent scheduler. | Next |

### Observe, review, and integrate

| ID | Feature and desired behavior | Sumi today | Priority |
| --- | --- | --- | --- |
| F18 | Session overview with task, agent, workspace, elapsed time, activity, and a direct jump to the terminal. | Partial: live sidebar, recent sessions, CLI focus; limited interactive navigation. | Core |
| F19 | Attention queue: unanswered questions, permission requests, failed checks, design decisions, and results ready for review. Keep these distinct from busy/idle process status. | Proposed; current sidebar shows activity only. | Core |
| F20 | Structured provider events first; hooks next; terminal capture as a labelled fallback. Preserve unknown/stale/disconnected states. | Partial: Codex event logs, native Zellij stream, regex hints. | Core |
| F21 | Review bundle: brief, approved artifact, diff, preview, check results, agent summary, and unresolved comments together. | Partial: separate logs/results/diff tools; no unified bundle. | Core |
| F22 | Explicit integration: review against the current base, resolve conflicts, rerun affected checks, then merge or create a PR when authorized. | Partial: manual Git review; Sumi has no merge/PR command. | Next |
| F23 | Quota, run cost where available, and resource visibility; optionally limit parallel work to available capacity. | Partial: CPU and weekly subscription quota panes; no cost accounting or scheduling policy. | Next |

### Collaborate and improve

| ID | Feature and desired behavior | Sumi today | Priority |
| --- | --- | --- | --- |
| F24 | Portable context packets: send a task brief, selected evidence, and unresolved questions to another agent without copying an entire transcript. | Partial: initial prompt snapshot and same-provider continuation. | Next |
| F25 | Local/LAN team ownership and handoff; optional SSH/WAN workers. Keep task storage and execution-host choice independent. | Proposed; current control state is local to one checkout. | Next for LAN, later for WAN |
| F26 | Feedback adapters for local Markdown, Radicle, and existing issue/PR systems; preserve external IDs and avoid duplicate imports. | Partial: private local Radicle experiment; no sync/import service. | Next |
| F27 | Improve reusable skills from actual outcomes. Propose a change, review its effect, and version the accepted workflow. | Partial: tracked factory skills and completed self-improvement tasks. | Core |
| F28 | Optional triggers for recurring maintenance or incoming issues, with explicit scope and capacity limits. | Proposed. | Later |

## Recommended next slices

These are independently useful experiments, not a mandatory sequence of phases.

1. **Task brief and attention queue.** Make one task explain what it is doing,
   what artifact is current, and exactly what it needs from a person. Exercise
   normal completion, a question, failed validation, and lost session state.
2. **One complete review loop.** Produce a Markdown proposal and HTML preview,
   attach a real comment, revise the artifact, and hand the agreed slice to an
   agent. Start with an existing review surface; evaluate the missing pieces
   before building an annotation application.
3. **Prove the adapter boundary.** Run the same bounded task using a second
   provider and a second execution backend. Evaluate RunPane or Superset's CLI
   alongside direct mux adapters. Preserve task/artifact identity and document
   which continuation and status capabilities each backend actually provides.

My recommendation is to start with the review loop while using the task brief
and attention queue as its smallest supporting surface. That exercises the
front-loaded collaboration Jeremy wants, and tells us what more orchestration
mechanics are actually necessary.

## Representative story

Consider an engineering idea: “Let reviewers annotate the current feature preview.”

The coordinator records the outcome and chooses discovery. An agent produces
two small interaction options and a Markdown explanation. Jeremy chooses an
option and changes a detail. That comment remains attached to revision 1; the
agent replies with revision 2 and a concise explanation of the change.

Jeremy agrees to a first slice: local browser review, one comment anchor type,
and file-backed feedback. The agent creates implementation and verification
tasks appropriate to that slice. Independent work can run concurrently; actual
dependencies remain explicit. Results return as a review bundle. A changed
assumption revises the affected task or design; it does not restart everything.

If the agent crashes, a new attempt reuses the recorded context and appropriate
workspace. If a reviewer comments on an old preview, Sumi identifies the old
revision rather than silently applying the comment to the latest page. If
checks pass, the result becomes ready for review; that alone does not merge it.

## Choices for the next revision

- **Primary daily experience:** coordinator conversation plus task/attention
  panes, or a task board first? Recommendation: retain the conversation and panes.
- **First collaboration surface:** Markdown comments, rendered HTML annotations,
  or code review? Recommendation: Markdown plus a linked HTML preview first.
- **Execution backend:** how much direct mux plumbing should Sumi retain if an
  existing agent-operable workspace manager supplies it well?
- **Local team scope:** one coordinator and several reviewers first, or concurrent
  task writers? Recommendation: the former until shared editing is needed.

## Boundaries for the first release

Use existing editors, browser engines, agent harnesses, and Git review tools.
Support optional browser surfaces without requiring an embedded WebView in every
mux. Keep closing a view separate from cancelling a run or deleting its worktree.
Keep the working UI replaceable, and avoid requiring a hosted account for local
task state. Cross-provider handoff transfers context; it does not promise native
conversation migration between incompatible agent formats.

An initial success criterion: start from a real request, revise one representative
artifact with actual human feedback, run two independent pieces of work, recover
an interrupted attempt, and review the resulting change with its evidence intact.
