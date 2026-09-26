# What LF-7 through LF-10 actually delivered

These were prototype acceptance tasks. They were not four independently
dispatched implementation jobs. The coordinator implemented most mechanics;
the two explicitly authorized Codex workers performed review and documentation.

| Task | Delivery | Implementation / evidence |
| --- | --- | --- |
| LF-7 durable task state | Implemented, then credited retrospectively from LF-15's parallel-run slice. | `.sumi/tasks.json`, `lib/sumi_runner.py`, `tests/test_runner.py`; initial implementation `b51c434`, recovery hardening `c6f4f8a`. |
| LF-8 native handoff | Implemented and exercised with two real Codex workers. Also credited retrospectively from LF-15. | `bin/sumi` prepare/start/inspect/resume; separate Git worktrees and Zellij tabs. LF-17 reviewed the runner; LF-18 wrote documentation and resumed its exact conversation. |
| LF-9 Radicle round-trip | Manual integration experiment, not an importer/service. | Coordinator copied the actual LF-17 review into a private local Radicle issue, posted its technical disposition locally, retrieved JSON, and checked bodies/reply anchors. See `docs/RADICLE-FEEDBACK.md`; recorded in `aeb6874`. |
| LF-10 self-improvement | Workflow exercise resulting in a concrete child task, LF-20. | Coordinator replaced repeated pane polling with native Zellij subscription in `peek --follow`, cropped the viewport locally, and verified initial delivery and subscriber cleanup. Implemented in `aeb6874`. |

## LF-7: scope of durability

Task trees support dependencies, acceptance criteria, evidence and status.
The runner atomically writes task/run JSON under an advisory writer lock.
Each attempt records its prompt, source commit, branch, worktree, provider
conversation ID, logs, result, and workspace reference. Worker/worktree leases
prevent duplicate claims and detect interrupted or orphaned execution.

These are local filesystem mechanics. Reconciliation happens when controls
inspect runs; there is no persistent scheduler or distributed state service.
Closing a view is not deletion of its task, artifacts, or worktree.

## LF-8: who did what

The coordinator wrote the runner. Native `codex exec --json` workers ran bounded
tasks in independent worktrees and overlapped for about 47 seconds:

- `LF-17-47af3c7c`: review artifact committed as `9ce515d` on its worker branch.
- `LF-18-30fefb5e`: quickstart, followed by `LF-18-318f0712` in the same worktree
  and exact conversation; artifact committed as `37aa0da`.

Those worker branches remain unmerged. The coordinator evaluated the review,
hardened orphan-child handling, and added regression coverage in the main
checkout. Worker exit means review is needed, not task approval or automatic merge.
The [run contract](PARALLEL-RUNS.md) records the review dispositions.

## How the queue evolved

LF-7/8 originally depended on approval of an earlier HTML mockup. Jeremy later
explicitly approved a separate live native-tool slice with two Codex agents.
That work satisfied their acceptance criteria. In `aeb6874`, the coordinator
reconciled their statuses and scoped the old HTML gate to that custom experience.
It did not infer approval of the HTML design from successful runner tests.

LF-9/10 followed as local experiments under the request to continue factory
tasks. Their completion means the documented bounded exercises succeeded.
It does not mean shared document annotation, automatic feedback synchronization,
continuous scheduling, or all mux/provider adapters were implemented.
