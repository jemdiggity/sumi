# LF-38: Schedule local Sumi tasks

Status: approved for implementation by Jeremy; factory invoked for LF-38.

## Outcome

Schedule a command in a project so Sumi can periodically launch work such as
learning from PR reviews or refactoring. Scheduling must work without a mux or
desktop app. Commands can invoke any agent CLI or a script that invokes a Sumi
skill; the scheduler does not interpret skills or choose an agent.

## First slice

One project, one foreground scheduler, recurring intervals, durable run logs.
All commands use Sumi's existing project-root selection, including `--root`.

```sh
# Save an executable and its arguments; no implicit shell evaluation.
sumi schedule add learn --every 24h -- ./scripts/learn-from-reviews
sumi schedule add refactor --every 7d -- ./scripts/weekly-refactor

sumi schedule list
sumi schedule run learn           # Run now, even if paused; wait for its result.
sumi schedule serve               # Stay running and dispatch due commands.
sumi schedule pause refactor
sumi schedule resume refactor
sumi schedule remove refactor     # Remove definition; preserve run history.
```

These scripts are examples of user-provided commands, not bundled features.
For a quick smoke test, schedule a command that prints a message every `10s`.

`list` shows ID, enabled/paused state, interval, next due time, running state,
and last result. Adding a schedule enables it, with its first automatic run
one interval later. Duplicate IDs and invalid intervals produce helpful errors.
Accept positive integer intervals with `s`, `m`, `h`, or `d` suffixes; a day is
24 hours. This slice has no calendar or timezone scheduling.

## Execution rules

- Run the saved argument vector in the project's root, without a shell, with
  stdin closed. Interactive commands are unsupported; use noninteractive agent
  modes. Inherit the launching process's environment; do not save that environment.
- Execute at most one scheduled command per project at a time. Due commands run
  oldest-due first, breaking ties by ID. Manual runs use the same lock and fail
  clearly if another command is running. Only one `serve` may own a project.
- After completion, set the next automatic run to completion time plus interval.
  Failure is recorded and follows the same interval; no immediate retries.
- If the computer sleeps or the scheduler stops, run each overdue schedule once
  on recovery, not once for every missed interval. Pausing prevents future starts
  but does not kill a running command. Resuming sets next due to now plus interval.
- Manual runs leave the enabled/paused setting intact and reset next due to
  completion plus interval. Removing a running schedule fails clearly.
- Ctrl+C stops dispatch and terminates the active command's process group,
  escalating after a short grace period; record it as interrupted. On restart,
  reconcile incomplete run records. Never launch a duplicate while a prior child
  is still alive; report recovery instructions if ownership cannot be established.
- A zero exit code means the command succeeded, not that a task, review, or PR
  was accepted. The invoked workflow owns worktrees, reviews, and task outcomes.

## Persistence and visibility

Store project schedule definitions in `.sumi/schedules.json`. Store runtime
state, locks, and per-run records under `.sumi/schedule-runs/` and ignore that
runtime directory in Git. Use atomic writes and serialize definition changes.

Each run records schedule ID, command, project, start/end times, state, exit code,
and separate stdout/stderr log paths. `sumi schedule runs [id]` lists recent runs
and their log paths. Errors remain visible after restarting Sumi. Schedule IDs
must be safe names, not paths. Reject malformed configuration without replacing it.

No background service is installed by these commands. `serve` must remain alive;
users can run it in a terminal pane. No changes to mux layouts are required.

## Acceptance

1. Add a ten-second printing command, run `serve`, and observe a real execution
   and saved output without an agent or mux dependency.
2. List, manual run, pause, resume, and remove work across separate CLI processes
   and scheduler restarts; changes take effect without restarting `serve`.
3. A long-running command cannot overlap another run in the same project,
   including one requested manually or by a second scheduler process.
4. A nonzero exit preserves logs and failure state; later schedules still run.
5. Missed intervals produce one catch-up run; interrupted work is distinguishable
   from success and is not duplicated while its process survives.
6. Paths with spaces and literal shell characters reach the executable unchanged.
7. Test timing and recovery with an injectable clock and short fake commands;
   do not spend agent tokens or wait days to verify scheduling.

## Later slices

Background startup via launchd/systemd, calendar times, one-shot schedules,
agent-specific conveniences, notifications, and task-pane schedule views.
Parallel dispatch across worktrees can follow once ownership is explicit.
