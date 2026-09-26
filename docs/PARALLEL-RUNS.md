# Parallel task workspaces — revision 1

Jeremy approved this slice by selecting two Codex agents. Sumi itself is the
prototype. The first implementation supports Codex and Zellij.

## Use it

```sh
bin/sumi prepare LF-17 --agent codex
# run: LF-17-<id>; branch: sumi/LF-17-<id>; base: <commit>
# worktree: .playground/worktrees/LF-17-<id>
# prompt: .playground/runs/LF-17-<id>/prompt.md

bin/sumi start LF-17-<id>
# opens a Zellij tab containing the native agent CLI and a shell
# task becomes active before the agent starts

bin/sumi prepare LF-18 --agent codex
bin/sumi start LF-18-<id>
# second independent worktree/tab; both agents can run concurrently

bin/sumi runs
# task / run / state / branch / workspace / last update
bin/sumi inspect LF-17-<id>
# task contract, recorded command, Git status, exit result, workspace reference
bin/sumi focus LF-17-<id>
# switch to its tab; leave other agents running

bin/sumi resume LF-17-<id> --prompt "Address the review findings"
# prepares a NEW attempt using the same worktree and exact Codex session
# start the returned new run ID explicitly

bin/sumi task LF-17 --status done --evidence "Reviewed artifact and checks ..."
# coordinator records acceptance after review; no merge is performed
```

## Contract

- A task is durable work. A run is one attempt. A Git worktree isolates files
  and its branch; a multiplexer tab displays processes. These IDs stay distinct.
- Preparation checks task dependencies (including ancestors), creates a branch
  from a recorded commit, and writes a task prompt from its title and acceptance
  criteria. Uncommitted changes in the coordinator checkout are not inherited.
  The captured task/prompt is authoritative for the assignment; task metadata
  can be newer than the code base commit, just as a tracker issue can be.
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

This initial probe proved concurrent process launch and working-directory
isolation. Subsequent runner tests cover atomic competing claims, dependency
and cycle rejection, two overlapping fixture workers, duplicate start refusal,
nonzero exit, lost worker detection, and preparation of a resumed attempt.

## Implementation notes

`bin/sumi` controls durable run records under `.playground/runs/`, with one
advisory lock for run/task mutations and an independent lifetime lease for each
worker. Use the CLI for task outcomes while workers run; direct edits to
`.sumi/tasks.json` do not participate in this lock. Run records are saved before task
status projection; `runs`/`inspect` re-project it after a partial write failure.

Agent panes run native `codex exec --json` and display messages/commands. Raw
events, stderr, final message, exact command, and the emitted Codex thread ID
are retained per run. The adjacent shell is available for interactive tools.
Codex uses workspace-write permissions and no interactive approval prompts;
no blanket sandbox bypass or model override is added. Worktrees isolate files,
not processes, ports, dependencies, credentials, or all Git metadata.

Exits become task `blocked` awaiting review, never automatic `done`. Closing a
workspace preserves all files; `inspect` reports a missing workspace. If a worker
dies without finalizing, `runs`/`inspect` detects its lost lease (with a 30-second
startup grace) and records interruption. Resumption requires a captured session
ID; if none exists, return the task to ready and prepare a fresh run. There is
no background scheduling, automatic retry, merge, cleanup, or migration of a
running process between muxers.

A worktree-level lease is inherited by the Codex subprocess as well as held by
the supervisor. A lost supervisor with a still-held worktree lease is marked
`orphaned` and stays reserved until the process releases it. `cancel RUN` releases
an unstarted preparation without deleting its branch or files.

## Live exercise and review

Two Codex workers completed concurrently in distinct branches/worktrees:
`LF-17-47af3c7c` reviewed the runner and `LF-18-30fefb5e` wrote a quickstart.
Their documents remain unmerged in their worktrees. A follow-up run,
`LF-18-318f0712`, successfully resumed the exact same Codex conversation in the
same worktree. Focus switching was verified against the live tabs.
The coordinator committed the reviewed worker artifacts on their own branches:
`9ce515d` (review) and `37aa0da` (quickstart). Neither is merged into main.

Review disposition:

- Worktree reuse after supervisor loss: hardened with the inherited worktree
  lease; a regression test kills the supervisor and verifies the surviving
  child keeps the worktree reserved until it exits.
- Startup without a captured session: the existing `task --status ready` then
  `prepare` recovery path works; now covered by a regression test. `resume`
  deliberately refuses to guess a conversation ID.
- Unlocked external edits to .sumi/tasks.json: outside the supported writer protocol;
  documented and routed through the locked CLI in the orchestrator skill.
- Queue metadata newer than the code commit: intentional; clarified the prompt
  snapshot as authoritative. Code starts from the recorded commit.

The review document contained hypotheses rather than executed reproductions.
Coordinator checks above distinguish the supported recovery paths from the
issue that warranted additional protection.

Run `python3 -m unittest discover -s tests -v` for the local, no-model tests.
