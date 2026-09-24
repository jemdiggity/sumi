# LF-24 implementation review

Astra produced the bounded brief in `MODEL-INSTRUMENTATION.md`. Sol implemented
it in a separate worktree and repaired the coordinator's findings in the same
Sol conversation. Both models were explicitly requested at medium effort and
confirmed from the exact conversations' local provider metadata.

Reviewed implementation: branch `sumi/lf-24-model-usage`, commit `e7c1abb`.
It is committed but unmerged, pending the user's integration choice.

The coordinator independently ran all 20 tests successfully, checked the real
LF-18 continuation delta, and exercised an unfinished turn after a completed
snapshot. Review repairs preserve cache-write counters and prevent that earlier
snapshot from being presented as trustworthy final usage for an unfinished turn.

| Conversation | Cumulative input | Cached subset | Output |
| --- | ---: | ---: | ---: |
| Astra design | 71,913 | 55,424 | 1,722 |
| Sol implementation and repair | 1,539,785 | 1,488,256 | 14,671 |

Sol's repair added 392,910 input (384,768 cached) and 2,067 output tokens.
Cached input is already part of input; these are inference counters, not unique
context size. Coordinator review usage is not included. Raw logs and manifest
are local ignored artifacts under `.playground/model-instrumentation/`.

Initial bootstrap commands prohibited delegation in their prompts and passed
`agents.enabled=false`; enforcement of that setting on the installed CLI was
not established. The repair and implemented runner use the locally verified
`features.multi_agent=false` flag instead.

These runs built the measurement prerequisite. They are not a controlled
comparison and provide no evidence yet that Astra plus Sol beats Astra alone.
The four-arm Astra/Sol/Luna pilot described in `MODEL-EXPERIMENT.md` remains next.

Bootstrap workers ran as separate noninteractive Codex processes outside the
mux, which initially made them invisible in the session sidebar. Their local
external-run registrations now appear there, deduplicated by conversation.
Both workers have finished. Future experiments should use the managed runner
so registration accompanies launch.
