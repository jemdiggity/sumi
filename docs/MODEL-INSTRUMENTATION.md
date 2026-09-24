**Implementation brief v1 — model pinning and conversation usage**

Base commit: `a104655ddcb6bc3bbd0ee422d2c6314069c3ba2f`. Read all four requested files. No code edits, agent launches, or task-state changes.

1. **Scope and integration points**

   Extend `lib/sumi_runner.py` at argument parsing, `Factory.prepare()`, and worker command construction. Add a pure usage reader, preferably in a small separate module. Keep `lib/agent_activity.py`’s bounded transcript reader unchanged: its 256 KiB tail is unsuitable for accounting.

   Extend `tests/test_runner.py`’s fake Codex harness and update `docs/MODEL-EXPERIMENT.md` with implemented commands and accounting semantics. Preserve mux adapters and existing lifecycle behavior.

2. **Prepared configuration**

   Support:

   ```sh
   sumi prepare LF-X --model gpt-6-sol --effort medium --no-subagents
   sumi resume RUN --prompt ...
   sumi usage RUN
   ```

   Add `--model`, `--effort`, and `--no-subagents` to both prepare and resume. Resolve each field independently at preparation:
   
   - Explicit values override predecessor values in the **new** run.
   - Omitted resume fields inherit the immediate predecessor’s recorded values.
   - New runs may omit model and effort. Record null requested values and `inherited/unpinned` provenance; do not read current defaults and claim they are pinned.
   - Persist delegation disabling and inherit it on resume. An omitted flag must not clear an inherited `true`.
   - Keep prepared configuration immutable through start/worker. Resume creates another record; never rewrite its predecessor.

   Store requested model and effort separately from observed model. Observed model remains null/unknown unless supported by worker event evidence; record the evidence source. Neither requested settings nor current user configuration establishes observation. Legacy records receive unknown/unpinned interpretations in memory, without migration writes.

3. **Worker invocation**

   Build actual Codex arguments exclusively from the prepared record. Route model through `--model`, effort through Codex’s per-invocation reasoning-effort override, and `--no-subagents` through its supported per-invocation delegation-disable setting. Verify exact flag placement for both `exec` and `exec resume` against installed CLI help; test the resulting argv explicitly.

   Preserve stdin prompts, JSONL capture, worktree, sandbox, approval policy, and session targeting. Keep the existing prompt prohibition on launching agents. Never modify global user configuration.

   At worker start, capture `codex --version` using the resolved worker binary and persist it alongside the actual command. A failed version probe records unknown plus diagnostic information, never an invented version.

4. **Read-only usage contract**

   `sumi usage RUN-ID` returns JSON containing run state, session identity, configuration provenance, CLI version, cumulative counters, attempt delta, baseline identity, completeness, and diagnostic reasons.

   Dispatch usage through a read-only path **before constructing `Factory`**, whose constructor creates directories and initializes a mux. Do not call reconcile, save, task projection, or lock-file creation. Read only Sumi run records and `events.jsonl`; require neither a mux nor provider session logs.

   Stream the entire JSONL file. Inspect every complete event, including all `turn.completed` snapshots. Handle malformed lines and unfinished trailing records without crashing, expose diagnostics, and withhold trustworthy-final status when corruption leaves completion or session continuity uncertain.

   For CLI **0.156.1**, completion usage is conversation-cumulative across resume:
   
   - Select the latest completed snapshot; never sum snapshots.
   - Validate nonnegative integer counters and monotonicity wherever successive counters are comparable.
   - Preserve missing, invalid, or errored counters as null/unknown. Do not fill absent fields from earlier snapshots.
   - Preserve optional cached-input and output-reasoning breakdowns when present. Cached input is contained in input; reasoning contained in output is not added again. Any total is input plus output only, and unknown when either is unknown.
   - Live, failed, interrupted, or incomplete attempts may expose their latest completed snapshot as **partial**, never as complete attempt consumption.

5. **Delta rules**

   For an evidenced new conversation, subtract zero from each known counter. Unknown counters remain unknown.

   For a resumed conversation, subtract only the immediate predecessor’s trustworthy final completed baseline. Require matching, evidenced session identity and a completed predecessor with valid relevant counters. Never search older ancestors to replace a missing baseline.

   Compute optional counters only when both endpoints contain trustworthy values. Reject session mismatch or any comparable counter decrease: return an unavailable delta with a specific reason, retaining raw cumulative evidence. Do not return negative deltas or silently treat a reset as a new conversation.

   LF18 acceptance fixture:

   | Counter | Initial cumulative | Resume cumulative | Resume delta |
   |---|---:|---:|---:|
   | Input | 203,969 | 353,663 | 149,694 |
   | Cached input | 178,176 | 320,512 | 142,336 |
   | Output | 2,252 | 2,868 | 616 |

6. **Regression coverage**

   Extend fake Codex processes to handle `--version`, capture argv, and emit selectable sessions, event sequences, and exit codes. Cover:

   - Exact fresh/resume argument routing after user defaults change between prepare and worker.
   - Independently inherited and overridden model/effort; inherited delegation disabling; unchanged predecessor records.
   - Omitted configuration and legacy records.
   - Missing events, absent usage, malformed JSONL, truncated final lines, and usage outside the transcript tail.
   - Several cumulative snapshots without summation.
   - LF18 baseline subtraction, missing/failed baseline, unrelated sessions, and counter reset.
   - Missing optional counters, invalid counters, and explicit zero counters.
   - Live/failed partial reporting and no reasoning/cache double counting.
   - Usage with unavailable mux and read-only state; verify unchanged files and no new files.

**Remaining limitations:** This slice reports recorded inference counters, not unique prompt size, instantaneous context, prices, invoices, or subscription allowance. Missing telemetry can prevent complete accounting. CLI-version/schema changes need explicit compatibility handling. Requested settings do not prove the served model, and disabling native delegation does not prove shell-launched agents were absent; strict benchmark validity still requires trace review.