# Evolving workflow experiment

## Outcome

Try a software factory assembled from reusable skills and existing tools. Keep
task state independent of terminal panes and collaboration backends.

First success: a proposal receives revision-specific feedback, an agent acts on
that feedback, and a person can trace the resulting change without reconstructing
the terminal transcript.

Confirmed direction: dynamic structure means both composing skills per task and
revising the task plan as evidence arrives. Jeremy confirmed both aspects.

## Current tasks

| ID | Result | Status | Dependencies | Evidence |
| --- | --- | --- | --- | --- |
| W01 | Draft reusable workflow and feedback skills | done | None | Local skill files; see paths below |
| W05 | Add prompt-selected starting templates to the workflow skill | done | W01 | factory-workflow/references/task-templates.md, now version 2 |
| W06 | Add iterative artifact design and scoped stakeholder agreement | done | W05 | factory-design skill; revised templates and feedback guidance |
| W02 | Select a proposal revision and record review feedback against it | ready | W01 | None yet |
| W03 | Revise the proposal and record how feedback was addressed | proposed | W02 | None yet |
| W04 | Identify missing orchestration glue from the observed review loop | proposed | W03 | None yet |

These tasks can split, merge, or be superseded. The table is the initial shape,
not a required lifecycle for every future task. No agent workers are launched.

## Skill drafts

- `~/.codex/skills/factory-workflow/SKILL.md`: evolve tasks and dependencies while
  preserving outcome, constraints, IDs, and completion evidence.
- `~/.codex/skills/factory-feedback/SKILL.md`: anchor review comments to artifact
  revisions and turn them into traceable follow-up work.
- `~/.codex/skills/factory-design/SKILL.md`: iterate on a representative artifact
  and obtain scoped stakeholder agreement before autonomous implementation.

## Decisions

- Start with local Markdown state. A database or scheduler is not yet justified.
- Keep backend details out of reusable skills. The existing playground is a
  place to exercise the workflow, not a dependency of the workflow definition.
- Do not prescribe a fixed sequence of specialist skills. Select the next
  activity according to dependencies and what is still uncertain.
- Select an initial task template from the prompt and source material: bug repair,
  defined feature, product discovery, engineering exploration, or maintenance.
  Source (Linear/GitHub/product/engineering) and work type are separate dimensions.
  Each template supplies starting tasks; discoveries can change their structure.
- Front-load new behavior with a concrete mockup, prototype, or written spec and
  iterative review. Record approval of an artifact revision and bounded scope
  before deriving autonomous implementation or cross-layer prototype work.
  Build approved slices while other slices evolve; return affected work to design
  if implementation reveals a material change. No stakeholder approval has yet
  been recorded for the playground proposal.

## Next experiment

Use `.playground/demo/WORKSPACE.md` as a candidate review artifact. Capture its
revision before reviewing it. Choose local feedback or the existing private
Radicle issue as the record. Establish the actual feedback before revising it;
do not invent reviewer comments to demonstrate progress.
