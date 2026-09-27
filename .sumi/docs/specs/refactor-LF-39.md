# LF-39: Self-contained skill installation fixtures

## Problem

CLI installation tests use live skill directory names that can change independently
of the installer. Their fixtures must describe installer inputs explicitly.

## Change

Add a test helper that creates two temporary skills with `SKILL.md` files, patches
`cli.TOOLS` to their temporary checkout, patches the home directory, and supplies a
temporary `CODEX_HOME`. Use the helper in both skill installation tests.

Verify repeated user installs retain valid symlinks for both Codex and Claude.
Replace one installed skill with personal content and verify installation rejects
the collision without overwriting that content. Verify project installation links
the temporary sources and does not create skill directories in user scope.

No production code changes are required.

## Validation

Run `python3 -m unittest discover -s tests -p test_cli.py -v`. Inspect the diff to
confirm that no live skill names or developer home paths are required by these tests.
