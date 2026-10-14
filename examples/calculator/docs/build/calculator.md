# Build: Calculator

| Field | Value |
|---|---|
| PRD | docs/prd/calculator.md (version 0.1) |
| PRD approval | user: "setujui" (2026-10-14), relocated to examples/calculator |
| Branch | example/calculator |
| Active phase | 1 |
| Last updated | 2026-10-14 |
| Baseline (lint/static, before build) | n/a: no toolchain in this project (plain HTML/JS, no formatter or linter configured) |

## Tasks
| Task | Feature | Status | Commit |
|---|---|---|---|
| Logic + tests | F-001, F-002 | done | feat(examples): add calculator logic with tests |
| Skeleton UI | F-001, F-002 | done | feat(examples): add unstyled calculator skeleton UI |

## Deviations from PRD
| ID | What differs | Reason (standards/technical) | Approved |
|---|---|---|---|
| | none yet | | |

## Notes
- Q-001 (styling direction) does not affect Phase 1: the skeleton stays unstyled until answered.
- Scaffold check: n/a, static file project with no manifest or toolchain to bootstrap.
- Demo lives in examples/calculator so the kit repository stays the single checkout.
- Verify 12 OK / 1 MISS: `SCR-001.page` MISS is explained, not a defect — the page heuristic only knows
  framework conventions (`pages/`, `views/`, ...); this static page is `index.html` at the root.
  Kit follow-up proposed: teach `collect_pages` the root `index.html` case on its own branch.
- 6 of 6 ACs connected in the PRD-code index; `node --test tests/` 9/9 pass.
