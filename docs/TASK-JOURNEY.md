# Lean factory: first task journey

Design revision 1. Proposed behavior for review, not an implemented scheduler.

## The improvement we use to build the factory

“Let me select a task in the sidebar and inspect its proposal, changes, and
feedback without hunting for files.” This is a real gap in the current workspace:
the sidebar is read-only and the artifact viewers always open WORKSPACE.md.

## From request to working change

1. **Capture intent.** Keep Jeremy's original request and create a stable task ID.
   A tracker URL would add source context; no tracker is required for this idea.
2. **Choose a starting shape.** Use product-discovery because task selection and
   artifact behavior still need agreement. Create children for the task list,
   detail view, and review interactions. Existing skill drafts supply guidance.
3. **Show a concrete proposal.** Selecting a task displays its goal, dependencies,
   completion criteria, artifact revision, and feedback. An empty queue offers a
   starting prompt; blocked tasks show the actual decision or dependency.
4. **Iterate.** Jeremy marks a passage or behavior, for example “keep the selected
   task independent from whichever task the agent is running.” This is an example
   comment, not feedback we claim to have received. The agent revises the mockup.
5. **Agree on a slice.** Record approval for task selection, details, and artifact
   navigation against a specific revision. Approval does not automatically include
   agent spawning, deployments, public sharing, or the rest of the backlog.
6. **Build from that reference.** Derive work for the local task model, CLI commands,
   task TUI, and workspace adapter. Reuse native terminals and editors. Experiments
   can proceed across layers within the approved behavior.
7. **Verify and review the result.** Show the selected task's real artifact, verify
   that another task can run without changing selection, and test reopening the
   workspace. Attach evidence before marking the task done.
8. **Improve the workflow itself.** Record a new child or follow-up when use exposes
   missing behavior. If it changes the approved experience, return that slice to
   the mockup and review loop; do not silently extend the build scope.

## State visible to people

- **Selected task:** what the person is inspecting; independent of execution.
- **Working task:** what the orchestrator is actually executing, persisted before
  work begins. Parents may be active as groups; a serial runner has one active leaf.
- **Waiting for review:** blocked with the artifact revision and decision needed.
- **Run failed:** task records failure evidence and recovery options; not silently done.
- **Done:** completion criteria have evidence. Design approval is a separate record.

## Artifact and feedback contract

An artifact has a task ID, path/URL, immutable revision or content hash, type, and
provenance. Comments name that artifact revision and a text/element/region anchor.
Responding to a comment, implementing a change, and accepting a design are separate
events. A changed revision leaves older comments intact and flags uncertain anchors.

The local files are authoritative for this prototype. tmux and cmux are views over
the same files. Only one coordinator writes task state; two workspace windows do
not imply two independent orchestrators. An editor may be used in either workspace.

## First slice to review

Select a task → read its details → open its artifact → leave revision-specific
feedback → inspect the agent's response. Keep agent execution explicit and local.
Use a standalone HTML mockup to make the interaction testable without building a
new terminal application. Mockup approval controls are simulated and never update
the real queue or grant actual approval.
