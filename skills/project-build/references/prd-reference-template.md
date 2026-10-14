# PRD to Code Reference Index Template

Code **must not** contain PRD IDs, whether in comments, doc comments, test names, or strings (`docs/CODE-DOCUMENTATION.md`). Tracing from the PRD to code is recorded in one place: `docs/prd-reference/<slug>.md` (English file name, kebab-case; `<slug>` is the same as the PRD slug). The skeleton is generated automatically with `prd_tasks.py scaffold` (all IDs already listed); fill it in **once at phase close** for the whole phase, then commit it together with the closing document. When renaming a file, test, or symbol after that, update its row in the same commit.

Content rules:
- **One row per pair** of PRD ID and test (or code). One AC may have several rows.
- Code is referenced with a **path from the repository root and the symbol name**: `path/File.php::method`, `src/features/x/Comp.tsx::CancelDialog`. No line numbers, because they go stale quickly.
- Test names are written **exactly** as in the test file (a literal fragment unique enough), in backticks. Avoid the `|` character in test names.
- PRD IDs (`F-###`, `AC-F###-n`, `API-###`, `SCR-###`, `T-###`) are used verbatim **in this file only**.
- Column and section titles are read by `prd_tasks.py verify`; do not change them.

````markdown
# PRD Reference: <Feature Name>

| Field | Value |
|---|---|
| PRD | docs/prd/<slug>.md (version <x.y>) |
| Last updated | YYYY-MM-DD |

## Features
| Feature | Code |
|---|---|
| F-001 | `src/services/CancelOrderService.js::cancelOrder`, `src/api/handlers/CancelOrderHandler.js::handle` |

## Acceptance criteria
| AC | Test file | Test name | Code |
|---|---|---|---|
| AC-F001-1 | `tests/orders/cancel-order.test.js` | `cancels a pending order and releases its stock` | `src/services/CancelOrderService.js::cancelOrder` |
| AC-F001-2 | `tests/orders/cancel-order.test.js` | `rejects cancelling a paid order` | `src/services/CancelOrderService.js::cancelOrder` |

## Test scenarios
| Scenario | Test file | Test name |
|---|---|---|
| T-001 | `tests/orders/cancel-order.test.js` | `cancels a pending order and releases its stock` |

## Endpoints
| Endpoint | Code |
|---|---|
| API-001 | `routes/api.js`, `src/api/handlers/CancelOrderHandler.js::handle` |

## Screens
| Screen | Code |
|---|---|
| SCR-001 | `pages/orders/[order].jsx`, `src/orders/components/CancelOrderDialog.jsx::CancelOrderDialog` |
````

## How to fill in
1. At phase close: `prd_tasks.py scaffold docs/prd/<slug>.md --root . --phase <N>` (only if the file does not exist yet).
2. Fill in the **Test file**, **Test name** (the real test name, without an ID), and **Code** columns for every row of that phase; the **Features**, **Endpoints**, **Screens** sections get code paths.
3. Run `prd_tasks.py verify` (Step 4 of `SKILL.md`). `[MISS]` means the row is empty or points at something that does not exist; `[MISS] code.prd-ref` means there is a PRD ID in code and it must be removed.
