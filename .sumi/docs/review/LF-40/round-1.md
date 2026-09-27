# LF-40 review — round 1

Verdict: **PASS**

Reviewed the committed diff from `4834ae5` through `d7d0613` in the Git worktree
`.sumi/worktrees/LF-40`, against `.sumi/docs/specs/LF-40/README.md` and the existing
Python scheduling behavior. No material correctness or contract issues found.
This includes the follow-up that pins CI Python to 3.12.

## Review coverage

- Native CLI, definition/history compatibility, literal arguments, scheduling
  selection and completion anchors, and preservation of unknown JSON fields.
- Shared flock paths and execution-before-config lock ordering, configuration
  edits during execution, durable intent before spawn, and recovery when the
  launcher's child group survives or ownership is ambiguous.
- SIGINT/SIGTERM handling and process-group cleanup, including retention of an
  active record when cleanup cannot establish that the group has exited.
- Standalone build/dependency boundaries, rollout documentation, benchmark
  methodology, and the macOS arm64 / Linux x86_64 CI workflow.

## Independent validation

`SUMI_NATIVE_BIN="$PWD/dist/aarch64-apple-darwin/sumi" python3 -m unittest discover -s tests -p test_schedule_contract.py -v`
passed all five shared contract tests, exercising both implementations and their
interoperability. These cover lifecycle/history, literal arguments, invalid
input, failure logs, concurrent exclusion, crash recovery, interruptions, and a
copied native binary with no tools in PATH.

Additional temporary-project CLI checks passed: unknown definition fields survive
a native edit; SIGTERM during a native manual run exits 130 and persists an
interrupted record; an ambiguous starting record with null PGID blocks a new run
without changing the record.

Linux runtime validation remains for the configured Linux CI job. This local
review validates macOS behavior and the workflow definition, and does not claim
a Linux runtime result before CI executes.
