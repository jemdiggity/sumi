# Sumi playground

A lean software factory assembled from existing tools and composable agent skills.

The `skills/` directory versions the factory skill drafts installed under
`~/.codex/skills/`. Keep those working copies synchronized when revising skills.
`docs/WORKSPACE.md` preserves the proposal shown in the disposable demo repository.
The runtime state under `.playground/` is local and is not committed.

```sh
bin/playground attach
bin/playground status
bin/playground rad issue list
bin/playground stop
```

`attach` opens a dedicated tmux server/session with two working panes and a
Forgejo service window. Use Ctrl-g then n to switch windows, Ctrl-g then an
arrow to switch panes, and Ctrl-g then d to detach. Press Ctrl-g twice to send
a literal Ctrl-g to an application. Ctrl-b is passed through
for command-line editing. Use `bindkey -e` in zsh for standard Ctrl-a/k/f/b
editing shortcuts (the setup machine's .zshrc now selects this explicitly).
Detaching keeps services
running; `stop` closes only this playground session and its processes.

Forgejo runs at http://127.0.0.1:3180. Its initial installation form is local
to this machine. Complete it with SQLite and the prefilled paths when ready
to try the browser review workflow. No Forgejo account has been created.

The demo Git repository, Forgejo state, and isolated Radicle identity live in
`.playground/`, which is ignored by Git. The Radicle identity is an unencrypted,
disposable lab identity, not a production identity. The demo repository is
private, and no Radicle network node is started or repository published.
The wrapper and tmux shells select this identity via RAD_HOME; your normal
Radicle configuration is untouched.

## First experiments

The current upper-right pane runs `bin/artifact-viewer`, a nested tmux session
with Markdown (Glow), Diff (Delta), and Neovim tabs. Click a tab or use F1/F2/F3
while that pane is focused; F5 refreshes Markdown or Diff and is passed through
to Neovim without restarting the editor. Save edits with `:w`, then refresh the
other views to see them. On a Mac, function keys may need
Fn. The diff includes tracked changes against HEAD and untracked files in the
demo repository. A newly created file appears as entirely added. These are
snapshots refreshed on demand. The viewer uses no Control-key prefix; the outer
Ctrl-g controls still work. `bin/playground stop` also stops the viewer session.
The custom viewer/monitor layout is currently a live experiment, not automatically
recreated by `bin/playground start`.

1. In the demo repository, edit PLAN.md using an existing editor.
2. Read the seeded Radicle issue, add a comment, and inspect `git status`:
   discussion metadata does not change the source file.
3. Create a branch and a Radicle patch; compare review with a Forgejo PR after
   setting up a local Forgejo account/repository. These are independent backends:
   syncing Git commits does not synchronize their issue/review discussions.
4. Launch a native agent CLI manually in one pane and observe it from another.
5. Add only the glue this reveals we need: task/run IDs, worktree creation,
   artifact paths, and feedback routing. Keep each backend behind an adapter.

The experiment does not yet include agent orchestration, peer synchronization,
a custom dashboard, or HTML annotation. No paid agent runs are launched.

## WAN direction

Radicle supports internet peers. Reachability can come from a reachable seed
node, a directly reachable node (normally TCP 8776), or a Tor onion service.
Advertising an IP alone does not bypass NAT or carrier-grade NAT. A private
repository must authorize the peers/seed nodes receiving its contents.

Read https://radicle.dev/guides/user before enabling network synchronization.
First prove the local review loop, then add a second isolated peer, then a LAN
peer, and finally choose a WAN transport.
