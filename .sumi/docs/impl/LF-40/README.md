# LF-40 implementation

Rust is a scheduling-only preview, built independently of Python and invoked as
`dist/<target>/sumi`. Existing Python commands are retained. The native executable
links platform libraries but embeds its Rust/crate code; it never locates or
launches Python. Build dependencies are pinned in Cargo.lock.

The shared state contract is `native/STATE.md`. Both implementations use POSIX
flock on the same files. Run generation IDs, timestamps, exit semantics, process
groups, recovery records and due-time calculation remain compatible. Unknown JSON
object fields are preserved. Rust validates persisted fields before using them as
paths or process identifiers. No schema migration occurs in this slice.

Rust uses owned lock files and a child guard to clean up after errors. SIGINT and
SIGTERM set an atomic flag; interruptible waits run normal cleanup code outside the
signal handler. The durable starting record precedes process creation, and a crash
before PGID persistence remains an explicit recovery condition. The fork/exec
pre-exec callback only invokes setsid, an async-signal-safe system call.

We use small modules for CLI/root discovery, JSON storage/locking, process cleanup,
and scheduler behavior. Dependencies are clap, serde/serde_json, chrono, uuid,
signal-hook, libc, and anyhow; none require an installed runtime on the user's
machine. The explicit libc boundary is limited to flock, process-group signaling,
and setsid.

Shared CLI checks exercise both executables and switch writers/readers between
operations. They include crash recovery and execution/service locking in both
directions. Redundant Python-only CLI tests were replaced by shared checks; existing
Python timing and runner tests remain. The standalone check copies the binary into
a temporary directory and removes Python, Cargo and Git from PATH.

The two advertised preview platforms are macOS arm64 and Linux x86_64 on the Ubuntu
24.04 libc baseline. CI builds, lints, executes the full shared suite and inspects
linked libraries on those systems. No claim is made for cross-compiled but untested
platforms. Downloadable binaries are workflow artifacts, not a switch of the default
Sumi installation.

Performance measurements use a release build and the same host/fixtures for both
implementations. `benchmark-macos-arm64.json` records the reproducible command's
method, versions, median/p95 startup/list latencies, idle CPU/RSS and binary size.
These are warm-cache local measurements; startup excludes model/network time and
is not evidence that agents answer faster. Release budgets should be decided before
a future default-runtime switch, not retrofitted to this initial measurement.

Validation completed: CI run 36298722828 passed on both target platforms (38 tests
each, formatting, Clippy, and dependency inspection). The downloaded macOS CI
artifact also ran successfully outside the checkout with Python/Cargo/Git absent
from PATH. `ci-verification.json` records the artifact hash and observed output.
Learning and maintenance records were checked; both are recent, so the factory
did not start redundant follow-up sessions. PR: https://github.com/jemdiggity/sumi/pull/2.
