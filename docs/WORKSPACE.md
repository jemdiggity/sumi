# A lean software factory

Build the glue. Use the tools we already like.

## The workspace

| Area | Purpose |
| --- | --- |
| Left pane | Native agent CLI or editor |
| Upper right | Proposals, artifacts, and review feedback |
| Lower right | CPU and memory monitor |

## Keep the layers separate

- **Factory CLI:** tasks, agent runs, worktrees, and artifact references.
- **Workspace adapter:** arrange panes in tmux, WezTerm, or cmux.
- **Collaboration backend:** store issues and reviews in Radicle or Forgejo.
- **Existing tools:** edit with Neovim, read with Glow, preview HTML in a browser.

> A task exists independently of the pane showing it.

## First feedback loop

1. An agent writes a Markdown proposal.
2. A person reads it and attaches review comments to that revision.
3. The agent reads the feedback and revises the proposal.
4. The task records what changed and what remains unresolved.

## Decisions to explore

- [ ] Choose how an artifact identifies its reviewed revision.
- [ ] Try Radicle comments without changing the source document.
- [ ] Launch one native agent CLI in its own worktree.
- [ ] Open an HTML preview in a browser when a terminal cannot display it.

## Playground commands

```sh
bin/playground status
bin/playground rad issue list
```

Start local. Add a second peer after the review loop works.
