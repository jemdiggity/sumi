---
name: factory-design
description: Iterate with a user on representative mockups, prototypes, or written specifications for stakeholder approval before autonomous software-factory implementation. Use to make a proposed experience or system behavior concrete enough to review and build.
---

# Iterative design for agreement

Produce a representative artifact that stakeholders can evaluate and that agents
can use as a specification. Treat design as a feedback loop, not a one-time
document-writing phase. Favor early concrete examples over exhaustive planning.

## Establish the review target

Identify the intended outcome, affected users or consumers, scope of this slice,
and who can approve it. Reuse prior decisions and existing artifacts. Ask about
approval authority only when needed; do not invent stakeholders or contact them
without authorization. Prepare a reviewable artifact before requesting approval.

Choose a format that exposes the important decisions: an interactive HTML mockup
for an experience, representative CLI transcripts for a command interface,
request/response examples for an API, or a written specification for behavior
that is not usefully visual. Pair formats when necessary. A mockup may itself
serve as the spec; supplement only the behavior it cannot express.

## Iterate in small slices

Build an initial artifact promptly. Use realistic examples and representative
states. Review with the user, capture what changed and why, revise the artifact,
and repeat until the proposed slice is representative enough to approve.
Use available review tools; locally stored Markdown feedback is sufficient.

Represent the normal flow plus consequential alternatives: failure, empty data,
loading, permissions, or recovery where relevant. Include system effects and
constraints that affect stakeholder decisions. Do not require every possible
edge case or implementation detail before progress is possible.

Label simulated data and interactions, implemented behavior, untested assumptions,
and deliberately excluded scope. Visual polish does not prove completeness or
technical feasibility. Use a small technical experiment when feasibility affects
the proposal; keep it explicitly scoped as design exploration, not an approved
production implementation. Broad build or cross-layer prototype work follows
approval of the intended behavior.

## Present and record agreement

Present the concrete artifact revision, what it demonstrates, meaningful open
choices, and the proposed implementation scope. Record actual approval with
who approved, which revision, what scope, and any conditions. Silence, resolved
comments, and the agent's own review are not stakeholder approval. Existing
explicit approval can satisfy this step; do not request it again needlessly.

Approval can cover a small end-to-end slice while the rest is still being designed.
Unresolved choices outside that slice need not block it. Decisions that materially
affect the approved slice must be resolved or explicitly bounded before its build.

## Hand off and keep learning

Derive implementation tasks, layer-specific prototypes, dependencies, and observable
acceptance checks from the agreed artifact. Link each task back to its relevant
behavior or example. Keep the artifact available to agents throughout execution.
Approval of a design does not authorize deployment or unrelated external actions.

Allow implementation details to evolve autonomously within the agreed behavior.
When a finding changes user-visible behavior, scope, or a material constraint,
return that affected slice to design, show the proposed difference, and obtain
the needed decision. Continue independent approved work. Preserve the earlier
revision and agreement, and connect the new decision to them. Do not restart
the entire workflow or silently rewrite what stakeholders approved.
