# LF-38 implementation

The scheduler is a separate standard-library module. It uses the existing CLI
root resolution and atomic JSON writer; it has no mux or agent dependency.

Definitions are a JSON array in `.sumi/schedules.json`. A generation ID separates
re-added schedules from their old history. Next due is derived from the later of
the definition's anchor and the latest run's completion, plus the interval. This
avoids a crash between saving a finished run and updating a separate due-time file.

Three advisory POSIX locks cover definition mutation, project-wide execution,
and ownership of the foreground service. Definition locking is short-lived so
pause/resume/add work while a command executes. An execution owns a process group;
remaining descendants are terminated before the project execution lock is released.
Commands must remain in their process group and must not daemonize themselves.

A durable starting record precedes process creation. If Sumi crashes in the gap
before it saves the PID, recovery refuses to guess whether the command started.
If a recorded process group survives, recovery also refuses another launch. Once
the group is gone, the next execution reconciles the record to interrupted. This
favors avoiding duplicate edits over unattended recovery in ambiguous cases.

Intervals are bounded to ten years to reject impractical values and timestamp
overflows. Days mean 24 hours. Times use UTC in output and epoch seconds internally.
A clock can be injected for deterministic interval/catch-up testing.

Output from list/runs is JSON for now: usable in a terminal and composable by other
Sumi tools. Manual run returns zero only for a successful command, one for failure,
and 130 for interruption. Logs preserve the actual child exit code separately.

Scope: no service installer, agent policy, mux pane changes, worktree creation,
calendar syntax, or automatic task acceptance. Those remain responsibilities of
future scheduling slices or of the command being scheduled.
