# PRD: Calculator

| Field | Value |
|---|---|
| Status | Approved |
| Version | 0.1 |
| Date | 2026-10-14 |
| Slug | calculator |

## 1. Summary
A single static page calculator (standard operations plus history) in plain HTML and vanilla JavaScript, no dependencies. Key decisions: keyboard support included; skeleton-first UI, styling only after the skeleton is approved.

| Role | Main access rights |
|---|---|
| Visitor | use the calculator (no auth; everything runs locally) |

**Not a goal:** scientific functions, persistence, theming, backend.

## 2. Feature Catalog
Priority: **Essential** (without this the goal fails), **Important** (the next phase), **Optional**. Origin: **Requested**, **Implicit essential** (derived so the requested feature works; can be rejected), **Recommended**.

| ID | Feature | Description | Priority | Origin | Phase |
|---|---|---|---|---|---|
| F-001 | Standard operations | Add, subtract, multiply, divide with decimals, percent, sign toggle, and clear. | Essential | Requested | 1 |
| F-002 | History | List of past calculations, newest first, with per-entry delete and clear-all. | Essential | Requested | 1 |

**Out of scope:** scientific mode, memory keys, persistence across reloads, styling (separate step after skeleton approval).

## 3. Acceptance Criteria
### F-001 Standard operations
- AC-F001-1: Given `2 + 3` entered, when `=` is pressed, then the display shows `5`.
- AC-F001-2: Given a division by zero, when `=` is pressed, then the display shows the `error.cannot-divide` message and no crash occurs.
- AC-F001-3: Given `200` on display, when `%` is pressed, then the display shows `2`.
- AC-F001-4: Given focus anywhere on the page, when a digit, operator, `Enter`, or `Escape` key is pressed, then it behaves like the matching button.

### F-002 History
- AC-F002-1: Given a completed calculation, when it finishes, then one entry `expression = result` appears at the top of the history list.
- AC-F002-2: Given history entries exist, when clear-all is pressed, then the list is empty.

## 4. Business Rules and Flow
- Division by zero never throws; it shows the translated error message and resets the pending operation.
- Display shows at most 12 significant digits; longer results are rounded.
- Flows are linear (enter, operate, show); no extra flow diagram needed.

## 5. Design

| ID | Slug | Name | Route | Feature | Components | State |
|---|---|---|---|---|---|---|
| SCR-001 | calculator | Calculator | /index.html | F-001, F-002 | Reuse: none / New: display, keypad, history-list | loading: n/a (static), empty (history empty), error (divide-by-zero) |

**Translation key:** `calculator.title`, `calculator.error-cannot-divide`, `calculator.clear-history`. Display text is never hardcoded; accessibility (WCAG 2.2 AA) applies by default and is not written again here (`docs/CODE-STANDARDS.md`, `docs/FRONTEND.md`).

## 6. Technical Specification
Only what **cannot** be inferred from the standards.

**Data:** no storage; history lives in memory only.

**Security and performance:** no input leaves the page; no special rules.

## 7. Testing
Every AC becomes a test. This table is only for scenarios **outside AC** (concurrency, idempotency, integration); write `None.` when there are none.

None.

## 8. Implementation Plan
Phases in order by dependency. Tasks the size of one build cycle (merged when small and of the same kind). The Notes column: branch name (`feature/...`) and commit scope.

### Phase 1 - calculator
| Task | Feature | Effort | Notes |
|---|---|---|---|
| Logic + tests | F-001, F-002 | S | feature/calculator (calculator.js, tests/) |
| Skeleton UI | F-001, F-002 | S | same branch, separate commit, unstyled HTML only |

Release: no flag needed (static page); roll back by reverting the merge.

## 9. Risks, Assumptions, and Open Questions
| ID | Type | Description | Mitigation / impact if wrong |
|---|---|---|---|
| A-001 | Assumption | Browser target is evergreen (ES2020+). | Transpile or simplify syntax if older support is needed. |
| Q-001 | Open question | Styling direction after skeleton approval? | Skeleton stays unstyled until answered. |
