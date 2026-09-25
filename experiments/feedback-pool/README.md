# Parallel UI feedback pilot

LF-29. Six coordinator-authored synthetic comments (fixtures.json), not reviewer
feedback or approval. Same frozen mockup and comments, gpt-6-luna medium, native
Codex exec JSON, isolated JJ workspace per comment, concurrency 1/3/6. No worker
sees another result. Queue is assigned to the next available slot. The first pilot
uses fresh conversations per job to isolate concurrency; it does not measure a
prewarmed/resumed session pool or provider latency in isolation.

Each arm runs separately to avoid competition between arms. Order: 3, 1, 6.
All comments arrive at once. Deadline 300 seconds/job. No automatic retries or
model fallback. Coordinator serializes JJ snapshots and merges; agents edit only
their workspace. Workers may not run version-control mutations, network requests,
other agents, or read unrelated workspaces.

Measure worker completion, first syntax-valid candidate, total batch elapsed,
usage (cached input is a subset of input), merge conflicts, and smoke checks.
A candidate or clean textual merge is not stakeholder acceptance. Record actual
review and integration labor separately. A single order-dependent run is an
engineering probe, not statistical evidence of speedup or model quality.

Reproduction: Python 3, jj, authenticated codex CLI. `python3
experiments/feedback-pool/run.py --help`. Outputs stay in an explicitly chosen
new disposable directory. Source and registry paths are explicit arguments.
No global JJ configuration or existing repository is changed by the runner.

First measured run: [RESULTS.md](RESULTS.md). The checked-in summary records
worker timings and coordinator-verified candidate checks; combined previews were
manually integrated, not produced automatically by run.py.

DOM verification uses linkedom 0.18.13, installed outside worker workspaces:

```sh
python3 experiments/feedback-pool/run.py --output /path/to/new-disposable-dir --source /path/to/sumi-workspace.html --registry /path/to/sumi/.playground/external-runs
python3 experiments/feedback-pool/summarize.py /path/to/new-disposable-dir --dom-module /path/to/node_modules/linkedom/esm/index.js
```

`check.mjs MODULE HTML all` checks a combined file. The lightweight DOM shim
models select values/focus for behavioral checks; it is not native browser QA.
