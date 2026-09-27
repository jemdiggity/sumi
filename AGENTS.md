# Sumi development

Keep the primary checkout on `main`. Do feature work in separate branches and
worktrees by default, located under the primary checkout's `.sumi/worktrees/`.
Run commands and assign agents with an explicit worktree path.

Before creating a task workspace, select the version-control backend. If `jj` is
installed and `jj root` succeeds in the project, use JJ workspaces. Otherwise use
Git worktrees. Installing JJ alone does not opt a repository into JJ; do not
initialize or convert the repository unless requested.

Keep task workspaces under the primary checkout's `.sumi/worktrees/` with either
backend. Give delegated agents the selected backend and exact workspace path.
Keep the primary checkout stable; in JJ repositories, do task work in separate
workspaces and leave the primary workspace's checkout and `main` bookmark alone.
