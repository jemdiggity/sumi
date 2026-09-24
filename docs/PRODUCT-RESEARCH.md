# Product references for Sumi

Research date: 2026-09-24. First-party websites, documentation, and repositories
only. This is a documented-capability comparison, not a hands-on benchmark or
a claim that every advertised feature works equally well. Sumi's baseline is
the local prototype at `fc4737c`.

Conductor here means conductor.build, not Google's similarly named workflow
extension. RunPane refers to Pane and its `runpane` CLI. The cmux reference below
is the native macOS app; our installed cmux TUI experiment is a different surface.

| Product | Relevant documented capabilities | What Sumi can learn or reuse |
| --- | --- | --- |
| **HumanLayer** | Combines agent sessions, design artifacts, and code review; collaborative inline design comments feed back into agents. Offers several workflow shapes, multi-repo task setup, and local/remote execution building blocks. [Product](https://www.humanlayer.dev/) | Make the artifact and its feedback part of the task's working context. Its overlap with our goals is substantial; iterative design alone is not a unique differentiator. |
| **RunPane / Pane** | Native CLI agents in worktree workspaces; a discoverable agent-operable CLI; orchestrator skills; status cues, browser tabs, resource/port management, and self-hosted remote operation. [Repository](https://github.com/greenfield-inc/Pane) | Strong candidate for an execution backend. Agents bootstrapping their own workspaces is already a product pattern worth evaluating rather than rebuilding by default. |
| **Superset** | Provider-independent workspaces, parallel worktrees, status, diff review, editor handoff, remote hosts, scheduled work, and CLI/SDK/MCP control. [Product](https://superset.sh/) and [docs](https://docs.superset.sh/) | Evaluate its control surface as an adapter. Bring task context and review evidence together; expose the same operations to agents and humans. |
| **Conductor** | Task workspaces connect agents, branches, terminals, diffs, PRs, merge, and archive. The current product also advertises cloud microVMs and shared multiplayer workspaces. [Introduction](https://www.conductor.build/docs) and [product](https://www.conductor.build/) | Study the complete work-to-review lifecycle and shared handoff experience. Map execution hosting to our local/LAN preference separately. |
| **Cursor** | Editable implementation plans, worktree setup, and an agent-controlled browser with screenshots, console/network information, and dev-server awareness. [Plan Mode](https://prod.cursor.com/docs/agent/plan-mode), [worktrees](https://prod.cursor.com/docs/configuration/worktrees), [browser](https://cursor.com/docs/agent/tools/browser) | Make plans actionable and previews reviewable. Reuse an editor/browser's capabilities through task links and artifacts. |
| **cmux, native app** | Programmable terminals and browser panes, workspace metadata, attention notifications, and agent hooks. [Product/API overview](https://cmux.com/) | Treat the UI as a capable adapter, including attention signals and optional browser embedding. Do not infer native-app features from our cmux TUI test. |
| **Vibe Kanban** | Task board, agent workspaces, inline diff feedback, previews, and PR flow. Its current repository announces sunsetting. [Repository](https://github.com/BloopAI/vibe-kanban) | Useful interaction reference for tasks and review; investigate project continuity before choosing it as a dependency. |

## Patterns worth carrying forward

These are synthesis and Sumi design recommendations, not additional claims
about any one product.

**Attention is more valuable than raw activity.** Busy/idle helps locate work,
but the operator needs to know what decision, reply, or review will unblock it.
An attention item should link to the relevant artifact and proposed action.

**Worktrees are only part of workspace readiness.** A runnable task also needs
dependencies, environment choices, ports, and service lifecycle management.
Superset explicitly documents project setup/run/teardown scripts; that is a
useful adapter contract to examine. [Lifecycle scripts](https://docs.superset.sh/setup-teardown-scripts)

**The review loop crosses artifact types.** A feature can begin as a sketch,
become a written specification, then produce a diff and running preview. Sumi
should preserve those relationships rather than reduce every review to code.

**A scriptable workspace is becoming common.** CLI-first control and native
agents are valuable design choices, but are not sufficient differentiation.
The useful Sumi hypothesis is portable task/workflow/review state across these
systems, with low setup cost and a local/LAN deployment path.

**Choose a backend through an experiment.** Compare direct Zellij control with
one existing workspace manager using the same task. Measure setup effort,
native-agent fidelity, activity accuracy, recovery, artifact handoff, and local
operation. Backend reuse remains a proposal; none was installed or integrated
as part of this research.

## Questions the documentation does not settle

- Can a backend be used headlessly without its own UI or account becoming a
  mandatory part of the local Sumi workflow?
- Which events reliably distinguish working, waiting for input, and completed
  across supported agent versions?
- Can sessions and artifact references be exported and restored without losing
  useful context or requiring the original backend?
- Does a review surface support the exact Markdown/HTML anchoring and private
  LAN deployment we need? An embedded browser alone does not establish this.
- Which host manages ports, credentials, processes, and cleanup, and how are
  those responsibilities exposed to the orchestrator?

The [feature list](FEATURES.md) separates these proposals from the mechanics
already exercised in Sumi.
