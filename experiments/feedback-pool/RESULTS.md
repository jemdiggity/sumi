# LF-29: first parallel feedback pilot, 2026-09-25

Six workers completed six candidate changes in 51.2 seconds, versus 196.4 seconds
with one worker: 3.84× faster batch completion in this trial. This is throughput
evidence, not an end-to-end latency result or a statistical model comparison.

| Concurrent workers | First result | All six results | Initial conflict regions |
|---|---:|---:|---:|
| 1 | 38.5 s | 196.4 s | 4 |
| 3 | 26.4 s | 102.2 s | 2 |
| 6 | 22.7 s | 51.2 s | 2 |

All 18 independent candidates passed a core mockup-flow check and their targeted
DOM behavior check. The three combined results passed core + six fixture checks
following **manual coordinator integration**. Two coordinator omissions (the
three-worker wrap handler and serial search handler) were caught by checks and
repaired. This is evidence for checking merged behavior, not just conflict markers.

JJ recorded six-sided file conflicts without losing worker results. Workspaces
were separate; agents never concurrently wrote the same physical file. All six
comments touched index.html, a deliberately small and conflict-prone artifact.
Independent state additions and event handlers explain most conflict regions.

| Workers | Input tokens | Cached input (included in input) | Output tokens |
|---|---:|---:|---:|
| 1 | 573,692 | 484,608 | 8,482 |
| 3 | 725,026 | 604,928 | 9,223 |
| 6 | 582,194 | 489,728 | 8,301 |

All 18 persisted turn-context records report gpt-6-luna. Requested effort medium,
Codex CLI 0.156.1, JJ 0.45.1. Usage is reported by completed native CLI turns;
coordinator effort is excluded. No pricing or cost-saving claim.

## Review

Local dashboard: http://127.0.0.1:8769/
Six-worker combined preview: http://127.0.0.1:8769/combined-6.html
Original mockup and Agentation review sessions remain unchanged.

Disposable repo and all workspaces: /Users/jeremyhale/work/sumi-pool-20260925/
Raw native logs: Sumi .playground/external-runs/pool-sumi-pool-20260925-*/
Versioned measurement/check summary: results-20260925.json beside this file.
JJ commit IDs for combined previews are in that summary. Conflict snapshots,
source SHA-256, per-job sessions/times, and observed models are in the disposable
experiment directory. No source changes merged into Sumi or its review prototype.

## Limits and next slice

This is a batch scheduler with fresh sessions, not a prewarmed pool. Each job
starts from the same baseline, even with concurrency one; it does **not** compare
against a single agent incrementally applying all comments in one conversation.
All comments arrive together, arms run once in order 3/1/6, cache/provider
conditions vary. Timing excludes setup, verification, and manual integration.
Manual integration intervals exclude planning and interleaved work and should
not be treated as comparable end-to-end timing. DOM checks use linkedom 0.18.13;
they do not prove CSS layout or native-browser behavior. Native Chrome control
failed at startup twice, so visual review remains pending.

The useful next slice is an explicitly dispatched Agentation queue feeding three
persistent sessions, grouping overlapping comments and publishing individually
checked previews before integration. Then measure comment-to-visible-fix time
against one persistent session. Do not automatically start work when a reviewer
adds an annotation; preserve the user's explicit-dispatch preference.
