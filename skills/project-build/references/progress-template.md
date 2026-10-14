# Build Progress File Template

Save as `docs/build/<slug>.md` (same slug as the PRD). Created in Step 2 and **updated once at phase close** (or when stopping mid-phase), then committed. Completed task status can also be read from `git log`. Prose, identifiers, branches, and commits are all in English. The `Field | Isi` header matches the PRD template (the label is read by the scripts). PRD IDs are used verbatim in this file and in the PRD-code index, never in code.

Task status: `not started`, `in progress`, `done`, `deferred`, `failed`. Task names are **exactly** as in PRD Section 8 (read by `prd_tasks.py plan`). Per-test AC status is not recorded here: see `prd_tasks.py verify --ac-table`.

````markdown
# Build: <Feature or Product Name>

| Field | Value |
|---|---|
| PRD | docs/prd/<slug>.md (version <x.y>) |
| PRD approval | <who/when, or a short quote> |
| Branch | feature/<slug> |
| Active phase | <N> |
| Last updated | YYYY-MM-DD |
| Baseline (lint/static, before build) | pass / N problems / cannot run: <reason> |

## Tasks
| Task | Feature | Status | Commit |
|---|---|---|---|
| Cancellation column migration | F-001 | done | <hash> |

## Deviations from PRD
| ID | What differs | Reason (standards/technical) | Approved |
|---|---|---|---|
| D-001 | | | yes / pending |

## Notes
Assumptions made during the build, findings outside the PRD (not yet done), deferred tasks along with their reasons, the latest `verify` result (count of OK/MISS/?), and the next steps.
````

## Final report format for a phase (in chat)
Format per `AGENTS.md` § 4; delete the sections that are empty.

```
## Summary
Phases/tasks completed in 1-3 sentences.

## Changes
Features and PRD IDs built, files/areas changed, deviations.

## Testing
Commands and their results compared to the baseline; prd_tasks.py verify results; n of m ACs passing.

## Assumptions and decisions
Assumptions, deviations, and decisions along with their reasons.

## Risks and items that need human review
Impact, migrations that need to be run, findings outside the scope, open questions.
```
Add the PR title and description (Conventional Commits in English; what, why, how to test, risks, PRD IDs) and one closing question: continue to the next phase?
