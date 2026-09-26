# CLI launcher verification

2026-09-26, macOS, local checkout.

- `sumi` installed as a symlink in `~/.local/bin`; the source checkout remains required.
- Default launch reuses `sumi-zellij` without disturbing the existing workspace.
- Separate project with spaces in its path: real Zellij, tmux, and cmux TUI launches succeeded.
- Repeated launches retained 8 Zellij terminal panes, 6 tmux panes, and 6 cmux panes;
  the artifact region uses 3 stacked panes/tabs in Zellij/cmux and nested tabs in tmux.
- Pane commands receive the project root explicitly, so task state, shells and diffs
  refer to the selected project rather than the Sumi source checkout.
- Test-only sessions were stopped after inspection; the user's original sessions remain.
- Skill installation for Codex and Claude succeeded and a second installation made no changes.
  Identical legacy Codex copies were backed up to avoid duplicate discovery.
- 27 tests passed, including config persistence, command quoting, skill collisions,
  native app layout construction/reuse/access-denial handling, and existing runner tests.

Native cmux's installed CLI confirms the supported `new-workspace --layout` schema.
The native layout adapter has automated contract tests, but live creation is still
unverified: the app currently rejects socket clients not descended from cmux.
The computer-control connection also failed to start. Sumi reports this restriction
and does not change the access setting. Live verification requires running Sumi
inside cmux or enabling its local automation access with user approval.

This slice launches workspace layouts. Managed agent-run adapters and native
pane activity detection remain Zellij-only; other layouts explicitly label their
sessions display as recorded runs only.
