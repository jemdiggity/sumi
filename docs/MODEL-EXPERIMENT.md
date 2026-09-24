# Astra design / Sol implementation experiment

Draft protocol · 2026-09-24. No comparative model runs have been executed yet.
The hypothesis is lower cost per accepted feature without worse correctness or
materially more human review. Cheaper tokens alone do not establish that result.

## Handoff contract

Astra investigates the request and writes a versioned feature brief: intended
behavior, non-goals, relevant code and interfaces, constraints, concrete examples,
acceptance checks, and unresolved questions. Include enough rationale to let the
implementer make routine choices without repeating discovery. Avoid prescribing
every line of code. Resolve consequential product questions before handing off.

Sol receives the brief, its revision, the base commit, and an isolated worktree.
It implements and verifies the slice, reporting changes, checks, deviations,
and blockers. A material contradiction returns to design; routine implementation
choices stay with Sol. An independent review evaluates the actual result.

Use explicit model and reasoning-effort settings, rather than the user's CLI
defaults. The current Sumi runner does not yet expose these fields; model
pinning and usage accounting are the prerequisite instrumentation slice.
The installed native CLI supports `codex exec --model ... --json`.

## Comparison

Freeze the request, base commit, acceptance rubric and evaluator checks before
running either workflow. Give both arms the same tools, permissions, dependency
state, time limit and repair allowance. Isolate worktrees and conversations so
neither sees the other's implementation or review feedback.

| Arm | Workflow | What it tests |
| --- | --- | --- |
| A | Astra designs, then continues implementation | End-to-end Astra baseline |
| B | Astra designs, then hands its artifact to a fresh Sol session | Proposed workflow including handoff overhead |
| C, optional | Same Astra artifact, fresh Astra implementation session | Separates model choice from context-reset effects |

For the first paired pilot, freeze one Astra design artifact and branch at the
handoff. Charge its design usage to each workflow's hypothetical total, while
reporting that the experiment actually generated it once. Later paired tasks
can independently generate designs to test whole-workflow variability. Do not
charge a shared design only to the baseline, or hide the split workflow's review
and repair costs.

Initially disable delegated subagents in both arms and instruct them not to
launch additional agents through shell commands. Audit the observed execution
trace; a delegation violation invalidates the strict single-model comparison.
An unrestricted Astra-orchestrator workflow is a different baseline that can
be tested separately.

Evaluate correctness with prewritten checks plus a model-blind review of the
diff. Include regression behavior, maintainability, unnecessary changes, and
human intervention time. The implementer's own passing tests are evidence,
not the sole grading standard. Apply the same review and repair policy to both.

## Measurements and decision

Record task, arm, artifact revision, code commit, run and conversation IDs,
requested/observed model, reasoning effort, available service settings, CLI
version, time, usage, results, review effort, and repairs. Account for all
designer, implementer, reviewer and delegated usage that the workflow requires.

Keep input, cached input, cache-write input, output and reasoning breakdowns
separate according to the provider's schema. Cached input is a subset of input,
not additional input. Do not add reasoning tokens to output again when already
included. Distinguish run deltas from cumulative conversation totals.

Report total workflow cost per accepted task, acceptance rate, serious defects,
wall time, and human review time. Price estimates should use a dated rate table,
cache treatment and applicable tier/context adjustments. With subscription
authentication, an API-equivalent estimate is not an actual invoice or a measure
of weekly allowance consumed.

Start with one bounded pilot to validate measurement, then approximately ten
representative paired tasks across features, repairs, and maintenance. Repeat
some tasks and vary execution order to expose variability and cache effects.
That is useful engineering evidence, not universal proof. Report failures and
paired results, not only average tokens among successful runs.

A candidate adoption rule to agree before the pilot: all required checks pass,
no additional serious defects, and a worthwhile reduction in cost per accepted
task without unacceptable review-time or latency regression. Choose numeric
thresholds with the user before judging results; do not select them afterward.

## Evidence already available

Our local run logs contain `turn.completed.usage`. The provider session logs
identify both original worker conversations as `gpt-6-luna`, effort `low`.
The user CLI configuration currently has the same defaults. These runs therefore
provide a telemetry example, not an Astra-versus-Sol experiment.

| Conversation | Cumulative input | Cached subset | Output |
| --- | ---: | ---: | ---: |
| LF-17 review, `01a0d1b5-2f2b-71e1-8621-2bb366f1aefa` | 162,934 | 140,544 | 1,993 |
| LF-18 quickstart including continuation, `01a0d1b5-2f99-7661-b157-9907e0fcac5a` | 353,663 | 320,512 | 2,868 |

LF-18's first run reported 203,969 input / 178,176 cached / 2,252 output.
Its resumed run's final counters include those earlier tokens. The continuation
delta is 149,694 input / 142,336 cached / 616 output. Summing both final totals
would double-count the initial run. These counters cover recorded inference
usage, not unique words in the request or the instantaneous context size.

## Official references

Codex subagents inherit the parent model/effort unless selected or configured
otherwise; role configuration and explicit overrides can change this. There
is no basis here to assume an Astra session automatically delegates coding to
cheaper models. [Subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Noninteractive JSON includes completion usage, and App Server offers live thread
token-usage notifications. Local session files supplied the historical model
and cumulative-counter evidence above; their format is an implementation detail.
[Noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[App Server](https://learn.chatgpt.com/docs/app-server)
