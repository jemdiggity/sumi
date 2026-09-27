# LF-40: Python prototyping and a standalone native Sumi

Status: draft. Jeremy selected Rust unless a concrete application need favors Go;
no such need has been identified. Rollout scope remains proposed.

## Outcome

Keep Python for quickly trying ideas. Ship stable Sumi functionality as one native
executable per supported platform, with no separately installed Python runtime or
language toolchain. The native implementation must run on its own, including its
Sumi-owned helpers; invoking Python behind a compiled launcher does not qualify.

External integrations remain external: Git, the selected mux, agent CLIs, and
optional viewers/editors. Missing tools should only prevent the features that
need them. OS-provided libraries are allowed; “standalone” does not mean a kernel
or system libraries are bundled into the executable.

## Development model

Python is the experimental implementation; native Sumi is the release implementation.
An experiment does not have to be implemented twice before we can try it. Promote
features once their behavior is useful and stable. Fixes to promoted behavior must
keep both implementations compatible, or explicitly retire that Python feature.

Share specifications, file formats, fixtures, and a small set of observable
behavior checks—not line-by-line architecture or every internal unit test. The
written contract takes precedence when the implementations disagree; Python bugs
must not become native requirements. No transpiler or cross-language FFI is needed.

During rollout, keep `bin/sumi` working as today's Python prototype. Build the
native candidate as `dist/<target>/sumi`; invoke it explicitly. No silent Python
fallback. Report unsupported commands clearly. Only replace the installed `sumi`
after a release has the agreed feature coverage. Keep the prototype accessible
explicitly for development after that switch.

## First slice: native scheduling

Port the LF-38 scheduling command family. It is a contained, real slice covering
CLI parsing, JSON state, filesystem operations, subprocesses, locking, and recovery.
It also works without a mux, agent subscription, or network access.

- Preserve LF-38 command behavior, exit semantics, scheduling rules, and logs.
- Read existing `.sumi/schedules.json` and `.sumi/schedule-runs/` data. Python must
  also read state created by the native implementation. Define the shared format
  explicitly before changing it; reject incompatible data without overwriting it.
- Use compatible lock paths and lock semantics: a Python scheduler and a native
  scheduler pointed at the same project must never execute overlapping jobs.
- Interruption and crash recovery must preserve ownership across implementations.
- Keep native sources in `native/` and retain Python's current layout during the
  pilot. Build without requiring Python. Build-time dependencies are allowed;
  installed users must not need the build tools or a source checkout.

This slice is a native scheduling preview, not a claim that all of Sumi has been
ported. Later slices cover workspace adapters, managed agent runs, pane TUIs,
skill installation and bundled assets, and finally the default installer switch.

## Portability and performance

Proposed first release targets: macOS arm64 and Linux x86_64. Add macOS x86_64 and
Linux arm64 next; Windows support is a separate design because the current code
uses POSIX locks and process groups. Validate each advertised target on that OS;
cross-compiling alone is not runtime verification.

Measure Python and native builds on the same machine and fixture: CLI startup
(`--help` and `schedule list`), idle scheduler CPU/RSS, listing 1,000 run records,
and executable size. Record machine, build mode, repetition count, median and p95
latencies, and measurement method. Exclude agent/network latency. Set release
performance budgets from this baseline before replacing Python; the preview's
performance result is evidence, not an assumed benefit of a language rewrite.

## Acceptance

1. A downloaded native binary runs scheduling in an environment without Python,
   a compiler, or the source checkout. Verify linked dependencies on each target.
2. A compact shared CLI acceptance suite passes against both executables. Cover
   lifecycle/output, literal arguments, interruption/recovery, and cross-language
   ownership. Avoid duplicated suites and tests that merely mirror helpers.
3. Switching implementations preserves existing schedules and run history, and
   attempting to run both concurrently cannot duplicate a job.
4. Document build/install commands, supported features/platforms, dependency
   boundaries, and measured performance, including any regressions.
5. Existing Python workflows remain usable while the native preview is developed.

## Decisions for review

- Native language: Rust (selected). Reconsider only for a demonstrated requirement,
  not a speculative performance advantage.
- Confirm the Python-experiment/native-release promotion model rather than full
  feature parity on every experimental change.
- Confirm scheduling as the first slice and the proposed initial release targets.

Rust is the selected implementation language. Sumi mostly coordinates processes,
files, and terminal updates; a rewrite should primarily improve packaging and
Sumi-owned overhead, not agent response times. Ownership and explicit error handling
help model resource lifetimes, but cross-process locks and recovery still require
explicit design and behavioral checks. Go could simplify some implementation and
build workflows; its bundled runtime is not an installation dependency. Neither
that convenience nor unmeasured speed claims justify changing the choice here.

Language references: [Go runtime FAQ](https://go.dev/doc/faq#runtime),
[Rust](https://rust-lang.org/), [Zig overview](https://ziglang.org/learn/overview/).
