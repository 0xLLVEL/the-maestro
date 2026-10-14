# PRD: Order Cancellation

> Fixture: identical copies live at `project-prd/references/example-prd.md` and `project-build/evals/files/example-prd.md`. Keep them identical and update both in the same commit; the build selftests read the copy under `project-build/evals/files/`.

| Field | Value |
|---|---|
| Status | Draft |
| Version | 0.1 |
| Date | 2026-10-07 |
| Slug | order-cancellation |

## 1. Summary
A customer cancels their own `pending` order from the order detail page; held stock is released automatically and an admin can view the cancellation history. Decision: cancellation only before payment, no refund, the product UI is English only.

| Role | Main access rights |
|---|---|
| Customer | Cancel their own `pending` order |
| Admin | View the cancellation history of all orders |

**Not a goal:** refunds, cancellation after shipping, partial item cancellation.

## 2. Feature Catalog
| ID | Feature | Description | Priority | Origin | Phase |
|---|---|---|---|---|---|
| F-001 | Cancel order | A customer cancels their own `pending` order along with a reason | Essential | Requested | 1 |
| F-002 | Stock release | Held stock is released on cancellation | Essential | Implicit essential | 1 |
| F-003 | Confirmation email | Email to the customer after cancellation | Important | Recommended | 2 |
| F-004 | Admin cancellation history | List of cancellations for the admin | Optional | Requested | 2 |

**Out of scope:** cancellation by an admin on behalf of a customer.

## 3. Acceptance Criteria
### F-001 Cancel order
- AC-F001-1: Given my order is `pending`, when I confirm the cancellation, then the status becomes `cancelled` and `cancelled_at` is set.
- AC-F001-2: Given the order is `paid`, when I try to cancel it, then the system refuses with 409 `ORDER_NOT_CANCELLABLE`.
- AC-F001-3: Given the order belongs to another customer, when I try to cancel it, then the system refuses with 403.
- AC-F001-4: Given the order is already `cancelled`, when the cancellation is repeated, then the result is idempotent (200, no duplicate effect).

### F-002 Stock release
- AC-F002-1: Given an order with 3 items, when the cancellation succeeds, then each item's stock increases by the ordered quantity in the same transaction.

### F-003 Confirmation email
- AC-F003-1: Given the cancellation succeeded, when the notification job runs, then the email is sent to the customer only once.

### F-004 Admin cancellation history
- AC-F004-1: Given there are 45 cancellations, when the admin opens the list, then the data shows 20 rows per page, newest first.
- AC-F004-2: Given the user is not an admin, when opening the list, then access is refused with 403.

## 4. Business Rules and Flow
- Only the `pending` status can be cancelled; `pending` to `cancelled` is final.
- Reason optional, at most 500 characters (422 when longer).
- Cancellation and stock release in a single database transaction.

## 5. Design

| ID | Slug | Name | Route | Feature | Components | State |
|---|---|---|---|---|---|---|
| SCR-001 | order-detail | Order detail | /orders/{order} | F-001, F-002 | Reuse: Button, Modal, Badge. New: ConfirmDialog | loading, error, cannot be cancelled |
| SCR-002 | admin-cancellation-log | Cancellation history | /admin/order-cancellations | F-004 | Reuse: Table, Pagination | loading, empty, error |

**Translation key:** `orders.cancel.title`, `orders.cancel.confirm`, `orders.cancel.reason_label`.

## 6. Technical Specification
**Data:** `orders.cancelled_at` (nullable timestamp, indexed) and `orders.cancellation_reason` (nullable string 500); additive migration.

| ID | Endpoint | Auth | Feature | Summary | Error |
|---|---|---|---|---|---|
| API-001 | `POST /api/v1/orders/{order}/cancel` | the project's auth mechanism | F-001, F-002 | Cancel your own order | 401, 403, 404, 409, 422 |
| API-002 | `GET /api/v1/admin/order-cancellations` | the project's auth mechanism | F-004 | List of cancellations, paginated | 401, 403 |

**Security and performance:** `OrderPolicy::cancel` (prevents IDOR); rate limit 10/minute/user on API-001; email through the queue; the admin list eager loads `customer`.

## 7. Testing
Every AC becomes a test. Additional scenarios outside AC:

| ID | Level | Feature | Scenario |
|---|---|---|---|
| T-001 | Feature | F-001 | Payment webhook and cancellation at the same time: only one wins |

## 8. Implementation Plan
### Phase 1 - Core cancellation
| Task | Feature | Effort | Notes |
|---|---|---|---|
| Migration for the cancellation columns | F-001 | S | `feature/order-cancellation`; scope `db` |
| Action, Request, Policy, endpoint | F-001, F-002 | M | scope `order` |
| Screen `order-detail` + ConfirmDialog | F-001 | M | scope `ui` |

### Phase 2 - Notification and admin
| Task | Feature | Effort | Notes |
|---|---|---|---|
| Notification job and confirmation email | F-003 | S | scope `notification` |
| Endpoint and admin history screen | F-004 | M | scope `admin` |

Release: no feature flag; rollback by reverting the PR (additive migration).

## 9. Risks, Assumptions, and Open Questions
| ID | Type | Description | Mitigation / impact if wrong |
|---|---|---|---|
| Q-001 | Open question | Does a customer need to see their own cancellation history? | Determines whether an extra screen is needed |
| R-001 | Risk | Payment webhook and cancellation at the same time | Check the status inside the transaction + a row lock (T-001) |
