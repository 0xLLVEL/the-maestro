# PRD Template (concise)

Save as `docs/prd/<feature-slug>.md` (English file name, kebab-case). The numbered headings `## 1.` through `## 9.` are read by `scripts/check_prd.py` and `project-build/scripts/prd_tasks.py` through the **heading keywords** (Ringkasan, Fitur, Acceptance, Aturan, Design, Teknis, Pengujian, Implementasi, Risiko), so do not change the keywords. Those keywords, the table column headers, and the priority and origin values are parsed by `scripts/check_prd.py` and `project-build/scripts/prd_tasks.py`, so do not translate them. Prose is in English; identifiers (endpoints, tables, columns, JSON keys, slugs, translation keys) are in English as well (`docs/CODE-STANDARDS.md`).

## Density rules (mandatory)
- **One sentence per cell or bullet.** No paragraph that repeats the contents of `AGENTS.md` or `docs/`; just reference the file.
- **No** personas, glossary, long background, metrics, or Definition of Done unless the user asks for them. The DoD is in `AGENTS.md` § 5; feature-specific criteria are written as AC.
- **No traceability table** and **no user stories**. The link from feature to AC, screen, endpoint, and test already exists through the `Fitur` column in every table; `check_prd.py --trace` prints the matrix automatically.
- **AC = test.** Each AC is one testable Given/when/then line. Edge cases that need testing are written as AC, not as a paragraph. 2-5 AC per feature.
- A section that is not relevant is written as a single line `None.`, not deleted (the heading must remain).
- Target size: 1-3 features ±120 lines; A-Z product ±400 lines. `check_prd.py` warns above 450 lines.

ID scheme: `F-001` feature, `AC-F001-1` acceptance criteria (the number after F = feature), `SCR-001` screen, `API-001` endpoint, `T-001` test scenario outside AC, `A-001` assumption, `Q-001` open question, `R-001` risk.

````markdown
# PRD: <Feature or Product Name>

| Field | Value |
|---|---|
| Status | Draft |
| Version | 0.1 |
| Date | YYYY-MM-DD |
| Slug | feature-slug |

## 1. Summary
At most three sentences: what is built, for whom, the expected result. Then one line of key decisions from the Q&A.

| Role | Main access rights |
|---|---|
| Customer | ... |

**Not a goal:** what is intentionally not done.

## 2. Feature Catalog
Priority: **Essential** (without this the goal fails), **Important** (the next phase), **Optional**. Origin: **Requested**, **Implicit essential** (derived so the requested feature works; can be rejected), **Recommended**.

| ID | Feature | Description | Priority | Origin | Phase |
|---|---|---|---|---|---|
| F-001 | | | Essential | Requested | 1 |

**Out of scope:** explicit list.

## 3. Acceptance Criteria
### F-001 Feature Name
- AC-F001-1: Given <condition>, when <action>, then <measurable result>.
- AC-F001-2: Given <failure/edge condition>, when <action>, then <error or behavior>.

## 4. Business Rules and Flow
Bullets of rules, statuses and their transitions, validation per field. Flows are written only when not linear (one line or a small Mermaid).

## 5. Design

| ID | Slug | Name | Route | Feature | Components | State |
|---|---|---|---|---|---|---|
| SCR-001 | screen-slug | | /path | F-001 | Reuse: ... / New: ... | loading, empty, error |

**Translation key:** list of English keys. Display text is never hardcoded; accessibility (WCAG 2.2 AA) applies by default and is not written again here (`docs/CODE-STANDARDS.md`, `docs/FRONTEND.md`).

## 6. Technical Specification
Only what **cannot** be inferred from the standards.

**Data:** new columns/tables, types, relations, indexes, migration notes.

| ID | Endpoint | Auth | Feature | Summary | Error |
|---|---|---|---|---|---|
| API-001 | `POST /api/v1/resources` | the project's auth mechanism | F-001 | | 401, 403, 422 |

**Security and performance:** only special rules (authorization per role, rate limit, queue, cache, row lock).

## 7. Testing
Every AC becomes a test. This table is only for scenarios **outside AC** (concurrency, idempotency, integration); write `None.` when there are none.

| ID | Level | Feature | Scenario |
|---|---|---|---|
| T-001 | Feature | F-001 | |

## 8. Implementation Plan
Phases in order by dependency. Tasks the size of one build cycle (merged when small and of the same kind). The Notes column: branch name (`feature/...`) and commit scope.

### Phase 1 - <name>
| Task | Feature | Effort | Notes |
|---|---|---|---|

Release: one line (feature flag or not, how to roll back).

## 9. Risks, Assumptions, and Open Questions
| ID | Type | Description | Mitigation / impact if wrong |
|---|---|---|---|
| A-001 | Assumption | | |
| Q-001 | Open question | | |
| R-001 | Risk | | |
````
