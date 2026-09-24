# cmux TUI hyperlink investigation (LF-14)

The installed binary is cmux TUI 0.1.0, commit
`8c00e06fe17b57a765c82634f0da2a7e51413ba1`. This finding concerns the
terminal-hosted TUI, not the native cmux macOS application.

A named terminal hyperlink uses OSC 8 to associate a hidden URL with visible
text. Inspection of the installed revision's rendering path indicates that
this association is lost before output reaches the outer terminal:

- [Ghostty render Cell](https://github.com/manaflow-ai/cmux/blob/8c00e06fe17b57a765c82634f0da2a7e51413ba1/cmux-tui/crates/ghostty-vt/src/render.rs)
  carries text, color and styling, but no hyperlink destination.
- [TUI terminal grid](https://github.com/manaflow-ai/cmux/blob/8c00e06fe17b57a765c82634f0da2a7e51413ba1/cmux-tui/crates/cmux-tui/src/ui/terminal_grid.rs)
  translates these cells into Ratatui symbols and styles without forwarding
  hyperlink metadata or emitting OSC 8.
- [Render protocol](https://github.com/manaflow-ai/cmux/blob/8c00e06fe17b57a765c82634f0da2a7e51413ba1/cmux-tui/spec/render.md)
  likewise describes text/style runs without a destination field.

This is source-based evidence of a renderer limitation, not a verified click
test. Changing the outer terminal's click modifier cannot restore a missing
destination. Supporting named links requires carrying the URI through the
render model and emitting it in the TUI output.

An isolated private PTY probe successfully printed a named link and a bare URL
inside a test terminal (confirmed with `terminal screen read`). The attached
TUI capture did not show that terminal, so its absence of OSC 8 is inconclusive.
The test session was stopped; the user's workspaces were not changed.

Bare, visible URLs are a separate case: the outer terminal may detect their
text without OSC 8. Jeremy's reported click failure for those remains
unverified. No working click fix or upstream issue submission is claimed.
For now, copying a visible URL or opening it explicitly from a shell avoids
depending on hyperlink forwarding.
