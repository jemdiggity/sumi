# LF-38 review — round 1

**FAIL** — two actionable correctness findings.

Reviewed committed changes from `main` (`19ef5f0`) through implementation
`a50e1c6`, against the LF-38 specification and implementation notes. Unrelated
working-tree skill changes and existing CLI skill-test failures are outside scope.

## Findings

1. **P2 — Confirm descendant termination before finishing the run.**
   `lib/sumi_schedule.py:246–250` sends SIGKILL at the grace deadline and waits
   only for the original `Popen` child. That child can already have exited while
   a descendant remains in the process group. Sending SIGKILL does not establish
   that all group members have exited (in particular, delivery can remain pending
   during uninterruptible kernel work). `run()` then records a terminal state and
   releases `execution.lock`, and reconciliation ignores that terminal record.
   Another scheduled command may therefore launch while the old group survives,
   violating the project's no-overlap guarantee. Check group termination after
   escalation; if it cannot be established within a bounded wait, retain an active
   recovery record and prevent later launches. Add coverage with an exited leader
   and a group that remains alive after escalation. A deterministic probe with
   `group_alive=True` and an expired grace deadline confirms `stop_group()` returns
   after TERM/KILL and one leader-only wait without verifying the group is gone.

2. **P2 — Recognize the actual add subcommand before stripping `--`.**
   `lib/sumi_runner.py:375–380` checks whether the strings `schedule` and `add`
   appear anywhere before the separator. A valid schedule ID named `add` makes
   `schedule run add -- unexpected` silently discard the unexpected arguments
   and execute the saved command; `schedule remove add -- unexpected` similarly
   removes the definition. These should be argparse errors, as they are for other
   schedule IDs. Parse/identify the actual selected subcommand before extracting
   executable arguments, preserving normal validation for all other actions.
   Add a regression covering a schedule named `add` and unexpected trailing
   arguments. Reproduced with a temporary project: `run add --
   this-argument-should-be-rejected` exited 0 and the saved command printed
   `EXECUTED`.

## Validation

- `python3 -m unittest discover -s tests -p test_schedule.py -v`: all 8 pass.
- Standalone temporary-project CLI reproduction for finding 2: confirmed.
- Mocked forced-cleanup probe for finding 1: confirmed lack of group-exit check.

No implementation changes or commits were made during this review.
