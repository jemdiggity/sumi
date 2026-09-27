---
name: sumi-sw-factory
description: Sumi Software Factory takes in design docs (specs, UI mock-ups or prototypes) and produces production-ready, reviewed Pull Requests.
---

The Software Factory takes in a design specification (as a design spec, a UI mock-up, or a prototype) and produces a production-ready, reviewed Pull Request.
The design specification is in .sumi/docs/specs/<taskId>/. The design specification has already been reviewed, but no specification can cover everything so use reasonable trade-offs and assumptions
If there's is a serious gap in the spec, mark yourself as needing attention.
Document your design trade-offs in .sumi/docs/impl/<taskId>.

After implementation, launch a review subagent using codex astra on medium level with fresh context.
Read the reviewers feedback from .sumi/docs/review/<taskId>.
Complete as most 5 reviews. If the last review doesn't pass, mark yourself as needing attention.
If your review passes, create a pull request.

Check .sumi/docs/learning/. If it's been more than 24 hours since the latest sumi self improvement effort. Start a self-improvement session.
Check .sumi/docs/maintenance/. If it's been more than 1 week since the latest codebase refactor start a new sumi codebase refactor.
Your work is done.
