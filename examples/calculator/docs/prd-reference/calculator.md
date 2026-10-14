# PRD Reference: Calculator

| Field | Value |
|---|---|
| PRD | docs/prd/calculator.md (version 0.1) |
| Last updated | 2026-10-14 |

## Features
| Feature | Code |
|---|---|
| F-001 | `calculator.js::evaluate` |
| F-002 | `calculator.js::addEntry` |

## Acceptance criteria
| AC | Test file | Test name | Code |
|---|---|---|---|
| AC-F001-1 | `tests/calculator.test.js` | `adds two numbers and shows the sum` | `calculator.js::equals` |
| AC-F001-2 | `tests/calculator.test.js` | `reports divide-by-zero with the error key instead of crashing` | `calculator.js::evaluate` |
| AC-F001-3 | `tests/calculator.test.js` | `computes percent of the displayed value` | `calculator.js::percent` |
| AC-F001-4 | `tests/calculator.test.js` | `maps keyboard keys to the matching calculator actions` | `calculator.js::keyToAction` |
| AC-F002-1 | `tests/calculator.test.js` | `records each finished calculation at the top of the history` | `calculator.js::addEntry` |
| AC-F002-2 | `tests/calculator.test.js` | `empties the history on clear-all and deletes single entries` | `calculator.js::clearHistory` |

## Test scenarios
| Scenario | Test file | Test name |
|---|---|---|

## Endpoints
| Endpoint | Code |
|---|---|

## Screens
| Screen | Code |
|---|---|
| SCR-001 | `index.html`, `app.js::render` |
