# Clone setup, slice 1

Run from your Sumi checkout:

```sh
./setup.sh --mux zellij --with-codex
codex login
bin/zellij-playground
```

Or select tmux dependencies and open the existing basic tmux workspace:

```sh
./setup.sh --mux tmux
bin/playground attach
```

Choose a profile explicitly. With no `--mux`, setup installs only shared tools.
The native macOS cmux application can be installed with `--mux cmux`; its managed
runner adapter is a later slice. It is different from the cmux TUI binary used
in the original local experiment. Superlogical is an intended future adapter,
not an available installation profile.

## Installation behavior

The script uses an existing [Homebrew installation](https://brew.sh/) on macOS,
Linux, or WSL. Other package managers can install the listed tools manually;
`--check` works without Homebrew. Native Windows is outside this first slice
because the current runner uses POSIX process groups and file locks.

```sh
./setup.sh --mux zellij --with-codex --dry-run
./setup.sh --mux zellij --with-codex --check
```

Setup checks Python 3.10+ with curses/fcntl, Git, Glow, Delta, Neovim, less, the
selected mux, and optional Codex. Missing tools are installed; already available
commands are retained. It checks the resulting PATH and fails if prerequisites
remain unavailable. It does not authenticate accounts, copy credentials, modify
shell configuration, start agents/services, install skills globally, or replace
existing runtime state. It does not pin dependency versions.

Package profiles use the published Homebrew formulae for
[Zellij](https://formulae.brew.sh/formula/zellij),
[tmux](https://formulae.brew.sh/formula/tmux),
[Glow](https://formulae.brew.sh/formula/glow), and
[Delta](https://formulae.brew.sh/formula/git-delta), and the casks for
[native cmux](https://formulae.brew.sh/cask/cmux) and
[Codex CLI](https://formulae.brew.sh/cask/codex).

The Zellij adapter has been exercised with 0.45.1, and tmux key configuration
with 3.6a. Setup checks executable availability, not every version capability;
older manually installed muxes may need an upgrade. `top` is expected from the
OS; the launcher selects macOS or Linux arguments.

## What works on a fresh clone

The Zellij workspace opens tracked Markdown, a diff viewer, task/session panes,
shells and CPU monitoring. The tmux launcher opens its basic shell/task workspace.
Artifact viewers fall back to tracked repository files when the original
ignored demo repo is absent. Fresh tmux launch does not require Forgejo.

The repository includes Sumi's own task history, not an empty project template.
Existing local runs and conversations are not distributed with a clone.

Quota display is optional: without a separately installed `codexbar` CLI and
provider logins, the pane reports unavailable. The Radicle/Forgejo lab, its
identity, issue records, and database are also optional and are not installed or
reconstructed by this script. Their local experiment is documented separately.

## Mux boundary and next slices

`lib/mux_adapters.py` owns view operations: open a workspace, enumerate it, focus
it, capture a pane, and stream updates when supported. The runner records
`workspace_mux`, `workspace_session`, and an opaque `workspace_id`. Old records
without a backend field use Zellij for compatibility. Task IDs, run IDs, Git
branches and provider conversation IDs remain separate from these view IDs.

The architecture is mux-independent; implementation coverage is still uneven:

| Layer | Current coverage |
| --- | --- |
| Tasks, worktrees, run lifecycle | Shared runner state and file-based records |
| Managed worker launch/focus/capture | Zellij adapter extracted; no other managed adapter yet |
| Workspace launchers | Zellij; basic tmux; local experimental cmux TUI wrapper |
| Session sidebar | Zellij discovery/subscriptions; portable presentation is follow-up work |
| Future backends | tmux, native cmux, and Superlogical when an interface is available |

Follow-up slices: implement and exercise the tmux adapter; add cmux with an
explicit native-app versus TUI decision; move the session sidebar's discovery
behind the same capability boundary. Each should run the same bounded task and
recovery checks. A Superlogical adapter can follow once its interface can be
evaluated. None requires a change to task identity or a rewrite of factory skills.
