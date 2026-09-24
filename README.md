# Sumi playground

A lean software factory assembled from existing tools and composable agent skills.

Clone setup (macOS, Linux, or WSL with Homebrew):

```sh
./setup.sh --mux zellij --with-codex  # or --mux tmux; no mux is required by the core
codex login
bin/zellij-playground
```

Use `--dry-run` to preview or `--check` to verify dependencies. See
[setup and adapter coverage](docs/SETUP.md) for optional tools and current limits,
and [LF-7–10 implementation history](docs/IMPLEMENTATION-HISTORY.md) for what was
built versus exercised manually.

The draft [feature list](docs/FEATURES.md) records proposed priorities and current
implementation coverage, informed by [related product research](docs/PRODUCT-RESEARCH.md).

Sumi itself is the working mockup: the experiment is how quickly we can set up
parallel tasks, isolated Git worktrees, workspaces, and a control layer. The UI
is replaceable; tmux, cmux TUI, and now Zellij are adapters around the same files
and tools. `bin/sumi` now prepares isolated worktrees and launches parallel Codex
runs through Zellij. The earlier HTML proposal is one design artifact, not a
prerequisite for these explicitly requested workspace experiments.

The `skills/` directory versions the factory skill drafts installed under
`~/.codex/skills/`. Keep those working copies synchronized when revising skills.
`docs/WORKSPACE.md` preserves the proposal shown in the disposable demo repository.
The runtime state under `.playground/` is local and is not committed.

To process the queue, ask an agent to use `factory-orchestrator` with `tasks.json`.
For example: "Use factory-orchestrator to work through the design tasks, iterating
with me on the mockup before implementation." The skill selects eligible work,
uses the other factory skills, and records progress in the task file. It runs in
the current agent session; there is no background scheduler. Explicitly launched
Codex workers run in their own workspaces with recorded lifecycles.
LF-2 through LF-4 produced the first HTML design artifact. LF-5 awaits review of
that experience; separately approved native-tool workspace slices have proceeded.

## Parallel Codex workspaces

Prepare an eligible leaf task, then start the returned run ID:

```sh
bin/sumi prepare LF-17 --agent codex
bin/sumi start LF-17-<id>
bin/sumi runs
bin/sumi inspect LF-17-<id>
bin/sumi focus LF-17-<id>
bin/sumi resume LF-17-<id> --prompt "Address this review feedback ..."
```

Each run opens a separate tab with a Codex execution pane and a shell in its
own worktree. The main task list reflects active runs. Codex events, conversation
ID, result, stderr, base commit, branch, and workspace reference are retained in
`.playground/runs/`. `resume` prepares a new attempt in the same worktree and
conversation; start its returned ID explicitly. It never uses global `--last`.
Agent panes display native `codex exec` progress; they are not interactive Codex
chat prompts. The shell can be used for manual review and editing.

Workers finish into `blocked` awaiting review. Record the reviewed task outcome:

```sh
bin/sumi task LF-17 --status done --evidence "Reviewed the result and checks ..."
```

This records acceptance, not a merge. Branches and uncommitted worker changes
stay separate until explicitly integrated. While workers run, use `bin/sumi`
for task outcomes; direct JSON edits do not participate in the writer lock.
See [the run contract](docs/PARALLEL-RUNS.md) for failure and recovery behavior.

Inspect recent output without switching focus:

```sh
bin/sumi tail RUN-ID --lines 10 --follow
bin/sumi activity RUN-ID
bin/sumi peek terminal_2 --lines 10 --follow
```

`tail` and `activity` use the managed Codex event log and run state. A turn start
means busy, a turn completion means idle, and a recorded process exit means
finished (not necessarily an accepted task). Quiet output alone never means idle.
`peek` works on any existing Zellij terminal. With `--follow`, it subscribes to
native Zellij render events: an initial viewport followed by changed viewports.
It trims trailing blank padding and shows the last ten lines, cropping locally;
Zellij does not offer a row-region subscription. Redirected output is one JSON
object per update. Pane closure emits `source: pane-closed` with unknown activity.
Without `--follow`, it captures a single viewport. The default
busy regex is `esc to interrupt`, matching Codex's working indicator. Override
`--busy-regex` or `--waiting-regex` for other terminal tools, including Claude.
These screen matches are labelled heuristics: scrolled output, hidden indicators,
or quoted text can mislead them. Without a match the result is unknown.
They do not automatically schedule work or change task status.

The **Agent sessions** pane below Tasks runs `bin/session-list`. It discovers
native Codex/Claude terminals in this Zellij session and uses native viewport
subscriptions for screen-based busy hints (`~`). Managed workers use their
event logs; finished conversations appear under Recent, with resumed attempts
grouped by conversation. A missing screen indicator is unknown, not idle.
Use `j/k` to scroll, or `bin/session-list --once` for a JSON snapshot.

## Zellij comparison

Zellij 0.45.1 is installed through Homebrew. In a new Ghostty tab, run:

```sh
cd /Users/jeremyhale/work/sumi
bin/zellij-playground
```

The `sumi-zellij` session has the task list on the left, an agent shell in the
center, and a stack of Markdown, Diff, and Terminal panes above a CPU monitor
and Claude/Codex usage monitor on the right. Click a stack title to expand that viewer. Terminal is a regular
shell: run `nvim` and quit back to the prompt. Viewers can be rerun with Enter
after they exit. No agent CLI is launched automatically.

Only Ctrl-g is reserved in normal typing. After Ctrl-g: arrows (or h/j/k/l)
focus a pane, n adds a pane, t adds a tab, [/] change tabs, f toggles fullscreen,
and d detaches. Escape cancels; Ctrl-g twice sends a literal Ctrl-g.
These are Sumi's bindings, not Zellij's defaults.

```sh
bin/zellij-playground start   # create in background, or leave existing session alone
bin/zellij-playground status  # structured pane IDs, commands, and geometry
bin/zellij-playground action dump-screen --pane-id terminal_1
bin/zellij-playground action new-pane --name scratch --cwd /path/to/worktree
bin/zellij-playground stop    # ends this session and its processes
```

The launcher generates a layout under `.playground/zellij/` and uses the tracked
`config/zellij.kdl`. Background creation ignored the initial layout in this
build, so the launcher applies it explicitly to a fresh session through the
control CLI. Existing sessions are not relaid out on attach/start.
Configuration validation, six live terminal panes, task/CPU screen capture,
attach, and Ctrl-g/d detach were verified. Ghostty mouse behavior, transcript
hyperlinks, and Shift+Enter in an agent CLI still need interactive comparison.
Zellij's native [layouts](https://zellij.dev/documentation/creating-a-layout)
and [control CLI](https://zellij.dev/documentation/programmatic-control.html)
are the adapter surface for this experiment.

`bin/usage-monitor` refreshes a weekly allowance remaining table every 60 seconds,
using existing provider CLI logins (`--source cli`). It reports fetch failures
instead of treating missing usage as zero. CodexBar CLI 0.65.0 is installed
locally under `.playground/codexbar/bin/`; the release archive was checked against
the GitHub release's SHA-256 digest. The monitor also accepts `codexbar` on PATH.
It reads CodexBar's JSON weekly window for each provider and displays
`100 - usedPercent` plus the weekly reset in local time. Missing weekly data
is marked unavailable; session usage is never substituted. It shows subscription
quota remaining, not API billing totals.

## cmux comparison

A separate Ghostty tab hosts the native Apple Silicon **cmux TUI** binary, with
an isolated `sumi-cmux` session. It shares tasks.json and the demo artifacts with
tmux but uses its own processes. One coordinator writes task state.

```sh
bin/cmux-playground attach
bin/cmux-playground workspace list --json
bin/cmux-playground server stop
```

The local binary, verified vendor manifest, config, session state, and layout IDs
are under `.playground/cmux/` and are not committed. This wrapper accesses the
installed experiment; it is not yet a portable installer. cmux uses Ctrl-g as
its prefix. Click the right-pane Markdown/Diff/Terminal tabs; Ctrl-g then t creates
a new terminal tab. The keyboard behavior is still part of this comparison.
Transcript hyperlinks currently fail for Jeremy, including Cmd+Shift+click;
LF-14 tracks this unresolved issue.

## Design review

The first journey is in `docs/TASK-JOURNEY.md`. Open `mockups/factory.html` in a
browser for the interactive proposal, and follow `docs/DESIGN-REVIEW.md` to review
it. The mockup is intentionally disconnected from live task state and approval.

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
The launcher enables extended keys in CSI-u format and declares Ghostty's
extended-key support so modified Enter can reach terminal applications.
Shift+Enter also has an explicit CSI-u passthrough binding, preserving its modifier
when an agent starts in legacy pane mode. Ordinary Enter is unchanged. This is
configured on the outer playground server where agent CLIs run.
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

The left sidebar shows workspace task records from the versionable `tasks.json`,
a JSON list with stable IDs, titles, statuses, dependencies, acceptance criteria,
and optional recursive `children`. Nesting groups work; `depends_on` specifies
execution ordering independently. The pane refreshes every second; j/k or arrows
scroll, and g/G jump to the start/end. No demo Radicle issues are imported as real
tasks. The header shows executing leaf task IDs; active entries are bold and
marked `>`. The orchestrator writes status changes before starting work and after
each outcome. `bin/playground tasks` adds the
sidebar to a running workspace, and start/attach also ensure it exists.

The current upper-right pane runs `bin/artifact-viewer`, a nested tmux session
with Markdown (Glow), Diff (Delta), and Terminal tabs. Click a tab or use F1/F2/F3
while that pane is focused; F5 refreshes Markdown or Diff and is passed through
to the terminal without restarting its process. The terminal starts in the project
root: run `nvim tasks.json` or `nvim .playground/demo/WORKSPACE.md`, then `:q` returns
to the shell. Save edits with `:w`, then refresh the other views to see them.
On a Mac, function keys may need
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

Explicit agent orchestration is available through `bin/sumi`; the playground
launchers themselves do not start agents. Peer synchronization, automatic
scheduling, a live custom dashboard, and HTML annotation remain future work.

## WAN direction

Radicle supports internet peers. Reachability can come from a reachable seed
node, a directly reachable node (normally TCP 8776), or a Tor onion service.
Advertising an IP alone does not bypass NAT or carrier-grade NAT. A private
repository must authorize the peers/seed nodes receiving its contents.

Read https://radicle.dev/guides/user before enabling network synchronization.
First prove the local review loop, then add a second isolated peer, then a LAN
peer, and finally choose a WAN transport.
