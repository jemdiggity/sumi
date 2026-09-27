# Shared scheduling state (LF-38 / LF-40)

Both implementations use the existing unversioned LF-38 JSON format. This preview
adds no schema fields and performs no migration. Incompatible or malformed data
must produce an error without overwriting it. Unknown object fields are retained
when definitions or run records are rewritten. A future incompatible schema needs
an explicit version and migration design before either writer changes it.

`.sumi/schedules.json` is an array of definitions:

| Field | Meaning |
|---|---|
| `id` | 1–64 ASCII letters/digits/underscores/hyphens; starts alphanumeric |
| `generation` | 32 lowercase hex digits; a new identity each time an ID is added |
| `every` | Positive decimal integer with `s`, `m`, `h`, or `d`; up to ten years |
| `command` | Nonempty array of argument strings; first is the executable |
| `enabled` | Boolean |
| `anchor` | Unix epoch seconds (number); set at add/resume |

`.sumi/schedule-runs/<run_id>/run.json` records `run_id`, `schedule_id`,
`generation`, `command`, absolute `project`, `started`, nullable `ended`, `state`,
nullable `exit_code`, nullable `pgid`, absolute `stdout`/`stderr` log paths, and
optional `error`. IDs use the same formats as above; run_id is 32 lowercase hex
digits. Times are Unix seconds. Child signal exits are represented as negative
signal numbers. States: starting, running, succeeded, failed, interrupted.

The latest run in a generation is ordered by `(started, run_id)`. Next due is the
later of anchor and latest completion, plus interval. Missed intervals coalesce
into one execution. A successful command is not stakeholder acceptance.

Three persistent files under `schedule-runs/` are POSIX `flock` lock files:
`config.lock` serializes definition updates/selection; `execution.lock` excludes
all concurrent commands in the project; `serve.lock` excludes additional services.
Never replace or unlink a live lock file. Execution is acquired before config;
config is released while a child runs. Manual execution and services use the same
execution lock in both languages. File descriptors are not inherited by commands.

A starting record is saved atomically before spawning, then the child's session /
process-group ID is saved as running. On recovery, a null PGID is ambiguous and
blocks execution. A surviving group also blocks execution. A dead group becomes
interrupted, with completion set to recovery time. Never infer success after a
launcher crash. Inspect and stop surviving processes before manually repairing an
ambiguous starting record; preserve the record and set state=interrupted and ended
to current Unix seconds only after establishing that the command is stopped.

SIGINT/SIGTERM stop dispatch, signal the child process group, escalate to SIGKILL
after two seconds, and confirm group exit. If exit cannot be confirmed, preserve
an active recovery record. Commands must not daemonize or escape their group.
The project lock only coordinates Sumi; it cannot serialize unrelated tools.

Definitions/run records are written using a same-directory temporary file, flush /
fsync, and atomic rename. Rust also syncs the directory. No secrets from the
inherited environment are persisted. Command arguments and output are persisted.
