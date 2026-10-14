# Build: Blog Phase 1

| Field | Value |
|---|---|
| PRD | docs/prd/blog-phase-1.md (version 0.1) |
| PRD approval | user: "gas" after summary (2026-10-14) |
| Branch | example/blog-kit |
| Active phase | 1 |
| Last updated | 2026-10-14 |
| Baseline (lint/static, before build) | n/a: no toolchain in this project (zero-dependency Node, no formatter or linter configured) |

## Tasks
| Task | Feature | Status | Commit |
|---|---|---|---|
| Auth + roles + tests | F-001 | done | feat(examples): add blog auth with roles and tests |
| Posts + pagination + tests | F-002, F-003 | done | feat(examples): add blog posts, routes, and HTTP tests |
| Skeleton UI + style | F-001, F-002, F-003 | done | style(examples): design light theme for blog |

## Deviations from PRD
| ID | What differs | Reason (standards/technical) | Approved |
|---|---|---|---|
| | none yet | | |

## Notes
- Q-001 (registration open vs invite-only): assumed open, does not block Phase 1.
- A-002 (light style): approved direction for the styling step.
- Scope for the comparison experiment: kit side keeps full traceability; effort per step is recorded.
- Verify 33 OK / 13 MISS, all MISS explained (not defects): the 9 API route and 4 page MISSes come
  from heuristic collectors that only recognize framework route calls and framework page folders;
  this zero-dependency server dispatches manually and renders directly. Every listed route is
  exercised live by the HTTP tests (14/14 pass), which is the stronger evidence.
- 9 of 9 ACs and both T scenarios connected in the PRD-code index.
