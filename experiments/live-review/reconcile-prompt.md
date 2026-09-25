Reconcile one candidate with the current Cowboy Bebop preview in index.html.
The coordinator owns JJ. Edit only index.html; no jj/git mutations, dependency
installation, network, unrelated workspaces, or additional agents.

You have explicitly supplied read-only reference files:
- reviewed.html: the original revision the annotation targeted;
- current.html: the preview that was live when this merge began;
- candidate.html: the worker's proposed change (or previously reconciled result);
- intent.json: this feedback and recent published requests.
These files are context, not files to edit. Start from CURRENT behavior and carry
in the candidate's intended delta. Preserve all unrelated current changes.

JJ guide:
- This repository uses ui.conflict-marker-style="git" for two-sided conflicts.
  <<<<<<< begins one side, ||||||| begins the common-base section, ======= begins
  the other side, and >>>>>>> ends the conflict. The base is NOT another change
  to keep. Remove the whole marker scaffold when resolving each region.
- Identify sides by their content and supplied references, not guessed names or
  assumed order. Conflict markers can be longer than seven characters.
- JJ can fall back to snapshot format for multi-sided conflicts: +++++++ labels
  side snapshots and ------- labels a base. Its default diff format uses %%%%%%%
  and backslash marker lines. Do NOT split these formats on Git's ======= marker
  or treat leading diff '+'/'-' characters as source code. If encountered, use
  the supplied clean reference files instead of inventing a marker parser.
- jj resolve --list exits nonzero when there are no conflicts. You do not need
  that command; the coordinator checks JJ state after your edits.

Read only the conflict ranges and the corresponding reference ranges. Preserve
formatted source and make small exact patches. Never regenerate the whole CSS or
pick one whole side merely to remove markers. If two requests are incompatible,
return blocked and explain; do not silently discard a request.

Before finishing, check for remaining marker lines and inspect the resolved
region for duplicate cards/declarations and lost changes. Return required JSON:
changed plus a brief factual summary, or blocked if not fully resolved. Do not
claim success when any conflict markers remain. The coordinator validates and
rechecks the live revision before publication; it may have advanced meanwhile.
