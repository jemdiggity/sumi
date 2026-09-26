#!/usr/bin/env bash
# Install missing tools only. Does not start agents, services, or edit shell config.
set -euo pipefail

mux=none
with_codex=0
mode=install
usage() {
  cat <<'EOF'
Usage: ./setup.sh [--mux zellij|tmux|cmux|cmux-app|none] [--with-codex] [--check|--dry-run]

Installs missing dependencies using Homebrew on macOS, Linux, or WSL.
Core: Python 3.10+ with curses, Git, Glow, Delta, Neovim, less.
Select a mux explicitly; none installs just the shared tools.
--with-codex installs the optional native Codex CLI (login remains manual).
--check reports missing tools without installing anything (exit 1 if missing).
--dry-run prints install commands without changing anything.

cmux-app installs the native macOS application. On macOS, cmux also installs
that app to obtain its bundled terminal cmux CLI. On Linux, install the cmux TUI
release separately and put cmux-tui on PATH.
Managed agent runs currently have a Zellij adapter only. Mux parity is a
separate slice; installing a mux does not imply runner support for it.
EOF
}
while (($#)); do
  case "$1" in
    --mux) [[ $# -gt 1 ]] || { usage; exit 2; }; mux=$2; shift 2 ;;
    --with-codex) with_codex=1; shift ;;
    --check) mode=check; shift ;;
    --dry-run) mode=dry-run; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
case "$mux" in zellij|tmux|cmux|cmux-app|none) ;; *) echo "Unknown mux: $mux" >&2; exit 2 ;; esac
os=$(uname -s)
case "$os" in Darwin|Linux) ;; *) echo 'Use macOS, Linux, or WSL for this setup slice.' >&2; exit 2 ;; esac
if [[ "$mux" == cmux-app && "$os" != Darwin ]]; then
  echo 'The native cmux application profile requires macOS; choose tmux, zellij, or none.' >&2
  exit 2
fi

formulae=()
casks=()
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing: $1"
    formulae+=("$2")
  fi
}
if ! command -v python3 >/dev/null 2>&1 ||
   ! python3 -c 'import curses,fcntl,sys; sys.exit(sys.version_info < (3,10))' >/dev/null 2>&1; then
  echo 'Missing: Python 3.10+ with curses and fcntl'
  formulae+=(python)
fi
need git git
need glow glow
need delta git-delta
need nvim neovim
need less less
case "$mux" in
  zellij) need zellij zellij ;;
  tmux) need tmux tmux ;;
  cmux)
    if [[ "$os" == Darwin ]]; then
      if [[ ! -x /Applications/cmux.app/Contents/Resources/bin/cmux-tui && ! -x "$HOME/Applications/cmux.app/Contents/Resources/bin/cmux-tui" ]] && ! command -v cmux-tui >/dev/null 2>&1; then
        echo 'Missing: cmux TUI'; casks+=(cmux)
      fi
    elif ! command -v cmux-tui >/dev/null 2>&1; then
      echo 'Install the cmux TUI release and put cmux-tui on PATH, then rerun setup.' >&2
      exit 2
    fi ;;
  cmux-app)
    # Do not mistake a different executable named cmux (the TUI) for the app.
    if [[ ! -d /Applications/cmux.app && ! -d "$HOME/Applications/cmux.app" ]]; then
      echo 'Missing: native cmux.app'; casks+=(cmux)
    fi ;;
esac
if [[ "$with_codex" == 1 ]] && ! command -v codex >/dev/null 2>&1; then
  echo 'Missing: codex'; casks+=(codex)
fi

missing=$((${#formulae[@]} + ${#casks[@]}))
if [[ "$mode" == check ]]; then
  [[ "$missing" == 0 ]] || exit 1
elif [[ "$missing" != 0 ]]; then
  if [[ "$mode" == install ]] && ! command -v brew >/dev/null 2>&1; then
    echo 'Install Homebrew from https://brew.sh, load its shell environment, then rerun setup.' >&2
    echo 'Alternatively install the listed tools with your package manager and run --check.' >&2
    exit 1
  fi
  if ((${#formulae[@]})); then
    printf 'brew install'; printf ' %q' "${formulae[@]}"; printf '\n'
    if [[ "$mode" == install ]]; then brew install "${formulae[@]}"; fi
  fi
  if ((${#casks[@]})); then
    printf 'brew install --cask'; printf ' %q' "${casks[@]}"; printf '\n'
    if [[ "$mode" == install ]]; then brew install --cask "${casks[@]}"; fi
  fi
  if [[ "$mode" == install ]]; then
    # Check the user's actual PATH after installation; do not claim success if shadowed.
    check_args=(--mux "$mux" --check)
    if [[ "$with_codex" == 1 ]]; then check_args+=(--with-codex); fi
    bash "$0" "${check_args[@]}"
    exit $?
  fi
fi
if [[ "$mode" == dry-run ]]; then
  echo 'Dry run complete; nothing changed.'
  exit 0
fi
echo 'Selected dependencies are available.'
case "$mux" in
  zellij) echo 'Start the workspace: bin/sumi --mux zellij' ;;
  tmux) echo 'Start the workspace: bin/sumi --mux tmux' ;;
  cmux|cmux-app) echo "Start the workspace: bin/sumi --mux $mux" ;;
  none) echo 'Choose a UI later with --mux tmux, --mux zellij, or --mux cmux.' ;;
esac
if [[ "$with_codex" == 1 ]]; then echo 'Authenticate when ready: codex login'; fi
echo 'Optional: CodexBar for quota display; Radicle/Forgejo for the separate collaboration lab.'

echo 'Install the command: bin/sumi install; share agent skills: bin/sumi skills install'
