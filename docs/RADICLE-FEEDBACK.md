# Local Radicle feedback round-trip (LF-9)

This exercise stores actual agent review feedback locally, retrieves it as JSON,
and maps findings to their implementation dispositions. No cloud account,
Radicle node, network announcement, or stakeholder impersonation was involved.
Commands used `--no-announce` for both writes in the private playground repo.

## Artifact and provenance

- Reviewed implementation: `b51c4340d16d92242f18635ea7a4686523f25b9f`,
  `lib/sumi_runner.py` and `bin/sumi`.
- Original review: `9ce515d80d712a3cd9aab13877be14baa487eb6d`,
  `docs/RUNNER-REVIEW.md`, authored by Codex worker `LF-17-47af3c7c`.
- Coordinator response/implementation: `c6f4f8aa646ac9df811b6ba4e41f201fbfc06902`,
  including `docs/PARALLEL-RUNS.md` and regression tests.
- Repository: `rad:z4QsfyWRnvzqKxm4ZruPeVvjKtGd8`.
- Issue/root comment: `976c1c9c04101dad8c732fbbf2e1cf1e083dec04`.
- Disposition reply: `4b5de553f5bb8624410b91cf7deffb7c6656841f`.

The lab identity `sumi-playground` imported the original review verbatim with
explicit provenance and replied as coordinator. Neither comment represents
Jeremy's approval. The issue remains open; technical disposition alone is not
reviewer acceptance. Finding headings serve as anchors, with the original
review's source references preserved.

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Worktree reuse after supervisor loss | Addressed | Inherited worktree lease; surviving-child regression test |
| Startup without a session ID | Claim not adopted; regression added | Existing task requeue + prepare recovery works |
| Unlocked queue edits | Addressed in supported workflow | CLI writer lock and orchestrator instructions; arbitrary unlocked writers unsupported |
| Live task metadata vs code revision | Claim not adopted; contract clarified | Prompt snapshot records task context separately from code commit |

## Retrieve without a UI

From the Sumi checkout:

```sh
bin/playground rad issue show 976c1c9c04101dad8c732fbbf2e1cf1e083dec04
bin/playground rad cob show \
  --repo rad:z4QsfyWRnvzqKxm4ZruPeVvjKtGd8 \
  --type xyz.radicle.issue \
  --object 976c1c9c04101dad8c732fbbf2e1cf1e083dec04
```

The retrieved `thread.comments` map contains stable IDs, author, body and
`replyTo`. Verification compared both bodies exactly with the submitted text
and checked the reply points to the root comment. Local inputs and retrieval
snapshot are in `.playground/radicle-feedback/`; this document preserves IDs
and revision mapping in the main repository. The Radicle store itself lives
under `.playground/radicle` and is not backed up by a Sumi Git commit.

This proves a manual local adapter workflow. Automatic polling, importing
Radicle comments into the task queue, and multi-machine synchronization are
not implemented. A future importer can key feedback by repository + issue +
comment ID, preserving author and revision rather than interpreting comments
as execution or approval authority.
