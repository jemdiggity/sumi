---
name: sumi
description: Load me when using the sumi development environment
---

Sumi is an outer loop for agents.
Keep the primary checkout on main. Do feature work in a separate branch and worktree by default.
Create worktrees in .sumi/worktrees under the primary checkout, not nested inside another worktree.
Mark yourself as needing attention by putting a file in .sumi/tasks/needs-attention with your task ID as the file name and the reason you need attention as the contents.
