# Luna live-review latency audit — 2026-09-25

The long waits are substantially caused by the pilot's source layout and integration
scheduler. Luna also wastes time generating oversized failing patches and has two
unsupported completion claims. The available evidence cannot isolate provider
queue time, prefill, and token generation; those should not be labelled separately.

Source: nine real user jobs in .playground/live-bebop/queue.sqlite3; 13 matching
native edit/reconciliation run records and timestamped public tool events from
their persisted session transcripts. Setup-test jobs excluded. No model runs
were launched during this audit. Runtime behavior was not changed.

| Request | Edit worker | Reconcile worker | Waiting/checks/other | Total |
|---|---:|---:|---:|---:|
| Faye hair color | 18.16s | — | 0.92s | 19.08s |
| Faye portrait improvement | 38.67s | 86.50s | 0.66s | 125.83s, failed |
| Jet likeness | 24.56s | 60.65s | 83.14s | 168.35s |
| Jet size/aggression | 25.44s | 101.24s | 83.88s | 210.56s |
| Ein dog body | 37.94s | — | 31.44s | 69.38s |
| Favorite songs | 44.64s | — | 0.85s | 45.49s |
| Background color | 82.72s | 27.95s | 0.95s | 111.62s |

The remainder column is derived by subtraction, not directly instrumented lock
wait. Native timestamps corroborate long waits behind reconciliation. Arrival to
worker start is 0.21–0.63s for all nine user jobs; the six-slot execution queue was
not the bottleneck. Job total starts at executor entry and excludes that small
arrival delay and the browser's polling/navigation delay.

## Specific evidence

The baseline is 35 lines; its CSS is one 9,395-character line. Broad `rg` reads
regularly return ~20KB, often truncated at tool limits. Line-based patches and
merges touch unrelated rules together.

Background run ca362fe128c4:
- Worker begins 18:32:51.335 UTC.
- Reads matching page content, then the CSS; last read returns 18:32:58.596.
- At 18:34:01.934 it submits a 10,840-character tool call containing a large
  apply_patch. Verification fails: expected lines do not match.
- At 18:34:10.897 it uses a much smaller Python replacement; returns in 0.126s.
- Editing finishes 18:34:14.057. Reconciliation runs another 27.95s.

Thus ~63 seconds elapsed between reading CSS and the oversized patch attempt.
This includes model/service/generation time, not 63 seconds of shell execution.
The color edit worker reports 4,123 output tokens and only 43 reasoning-output
tokens: excessive generated patch text is a more concrete issue than attributing
this run to lengthy reasoning. Input counters are cumulative across tool rounds
and include cached tokens; they are not a unique prompt size.

The integration mutex encloses the entire reconciliation model call in server.py.
Jet's first edit finished at 18:26:06.114, but reconciliation started at
18:27:28.731 after Faye's repair failed. Ein's edit finished at 18:29:40.553 and
published only after Jet's reconciliation finished at 18:30:11.164, despite Ein
requiring no reconciliation itself. The earlier description of serial integration
understated this lock's impact on clean changes.

Faye repair 8dd630b7eda2 attempted to split JJ conflict text using Git-style
`=======` separators, then made repeated parsing attempts. It consumed 86.5s and
still left conflict markers. The failed output was correctly kept off the live page.

## Correctness finding

Jobs 115880ab53ab (Faye neckline) and 485eb742a16a (backstories) claimed successful
edits. Each transcript contains one read command and no mutation. `jj diff
--name-only` is empty in both workspaces. The runner treats every zero-diff result
as `answered`, so requested changes were neither implemented nor visibly failed.
These 7.36s and 12.40s runs must not count as successful fast edits.

## Recommended order

1. Reformat source and separate CSS, character data, and SVGs so small changes
   read and patch small regions. Preserve existing revisions and pending edits.
2. Move slow reconciliation outside the publication lock. Before publishing,
   recheck the current revision and remerge/revalidate if it advanced. Independent
   clean work must be able to publish while a conflicting candidate is repaired.
3. Give the reconciler explicit base/current/candidate files or familiar conflict
   representation instead of making it reverse-engineer JJ's marker format.
4. Route clear color/text/property edits to constrained patches with exact-match
   validation; reserve full repository exploration for broader changes.
5. Distinguish a question/answer from an edit request with an empty diff. Do not
   accept a claimed modification without changed-file evidence.
6. Add phase timestamps (queue, first tool, edit, validation, lock wait,
   reconciliation, publication). Then compare warm sessions and a faster patch
   path on the same color edit; the current audit does not establish their gain.
