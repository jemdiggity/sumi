# Parallel task workspaces — revision 1

Proposed slice for Jeremy's review. Sumi itself is the prototype. The commands
below are a proposed interface, not implemented commands yet.

## Use it

```sh
bin/sumi prepare LF-17 --agent codex
# run: LF-17-<id>; branch: sumi/LF-17-<id>; base: <commit>
# worktree: .playground/worktrees/LF-17-<id>
# prompt: .playground/runs/LF-17-<id>/prompt.md

bin/sumi start LF-17-<id>
# opens a Zellij tab containing the native agent CLI and a shell
# task becomes active before the agent starts

bin/sumi prepare LF-18 --agent claude
bin/sumi start LF-18-<id>
# second independent worktree/tab; both agents can run concurrently

bin/sumi runs
# task / run / state / branch / workspace / last update
bin/sumi inspect LF-17-<id>
# task contract, recorded command, Git status, exit result, workspace reference
bin/sumi focus LF-17-<id>
# switch to its tab; leave other agents running
```

## Contract

- A task is durable work. A run is one attempt. A Git worktree isolates files
  and its branch; a multiplexer tab displays processes. These IDs stay distinct.
- Preparation checks task dependencies (including ancestors), creates a branch
  from a recorded commit, and writes a task prompt from its title and acceptance
  criteria. Uncommitted changes in the coordinator checkout are not inherited.
- Only one live run may claim a given task. Different eligible tasks may run
  simultaneously. Local state mutations use a shared lock and atomic writes.
- Starting a run records intent before creating a tab. Repeating a start never
  silently launches a duplicate. A failed launch records a useful error.
- Workers operate in their own worktrees. They report results and evidence;
  the coordinator owns the canonical task queue and review decisions.
- Agent exit means the process exited, not that the task passed review. Preserve
  its exit code and branch. Never automatically merge, delete worktrees, or mark
  a task done based only on exit code zero.
- Inspect and focus work independently of the original coordinator session.
  If a tab disappears, report it missing; preserve the worktree and run record.
  Provider conversation resume must use an actual recorded session ID, never
  a global "last session" that might belong to a different parallel task.
- Use installed native agent CLIs and their permission settings. Do not add
  blanket permission bypass flags as a side effect of orchestration.

## First proof

Exercise worktree/tab launch with two harmless local commands first: each writes
its own task result, and both are visible concurrently. Test duplicate launch,
dependency rejection, failed command, and reopening the same worktree.
Then exercise two bounded real tasks with the chosen agent providers.

Zellij is the first runner adapter. Keep its tab/pane operations separate from
task/worktree state so tmux or cmux can be added without changing task identity.
Automatic scheduling, task discovery, merging, and cross-machine workers are
outside this slice.

## Feasibility evidence

Two Zellij tabs, `Proof a` and `Proof b`, were created without stealing focus
from the coordinator. Each has a separate branch/worktree in an isolated local
test repository and a shell. Two six-second processes overlapped in time and
wrote independent `result.json` files in their own worktrees. Both passed.
Local evidence is `.playground/parallel-proof/evidence.json`.

This proves concurrent process launch and working-directory isolation. It does
not yet prove agent session recovery, task claiming, dependency enforcement,
or the proposed `bin/sumi` commands. No model-backed workers were launched.
