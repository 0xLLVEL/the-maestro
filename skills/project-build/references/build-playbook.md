# Build Playbook

Table of contents: 1 PRD to code map · 2 Layer order · 3 Data and migrations · 4 Backend · 5 API · 6 Tests from ACs · 7 UI framework · 8 Design and UI text · 9 Queue · 10 Commit

Detailed rules live in the project's `docs/`; read only the standards file for the layer currently being worked on. Examples only illustrate the shape. If they differ from the project documents, the project documents win; conflicts with the PRD: see "Conflicts and deviations" in `SKILL.md`.

## 1. PRD to code map
| PRD section | Becomes | Standards |
|---|---|---|
| 2 Feature catalog (phase, priority) | Work order and scope; Optional is not built | AGENTS.md § 2 |
| 3 AC (`AC-F001-1`) | Test (Given/when/then = Arrange/Act/Assert) and code behavior | docs/TESTING.md |
| 4 Business rules | Enum, constants, guard in the service or use-case layer, input validation | docs/BACKEND.md |
| 5 Screens (`SCR-###`) | `docs/design/screens/<slug>.md`, the route and components of the UI framework | docs/FRONTEND.md |
| 6 Data, endpoint (`API-###`), security | Migration, models, factories; route, entry point/handler, input validation, response mapping, authorization; rate limit, queue | docs/DATABASE-PERFORMANCE.md, docs/API.md, docs/SECURITY.md |
| 7 Additional tests (`T-###`) | Descriptive test; IDs only in the PRD-code index | docs/TESTING.md |
| 8 Phases and tasks | Branch, commit scope, release | docs/GIT.md, docs/CI-CD.md |
| 9 Risks (`R-###`) | Mitigation in code (e.g. a row lock) and its test | docs/DATABASE-PERFORMANCE.md |

Definition of Done: `AGENTS.md` § 5 (feature-specific criteria have already become ACs).

## 2. Layer order within one feature
1. Migration and model (if there is new data).
2. Enum/constants, service or use-case layer, input validation, authorization, response mapping.
3. Thin entry point/handler and route.
4. Tests from ACs, **written alongside** steps 1-3. **Tests first** only for bug fixes and critical business rules.
5. API client, types, and frontend hooks.
6. The UI framework's components and routes, translation files.
7. Doc comment, OpenAPI, `CHANGELOG.md` (the last of these at phase close).

The backend and API contract are complete and tested before the UI uses them.

## 3. Data and migrations
- New migration; do not change one that has already been run; prefer additive (nullable/defaulted first, backfill, then tighten); no ORM models inside a migration (`docs/DATABASE-PERFORMANCE.md`).
- Apply the columns, types, relations, and indexes from the PRD exactly. Foreign keys with an explicit `onDelete`; database unique constraint when a rule requires uniqueness.
- Money: integer or decimal, not float. `snake_case`, plural tables. Factory for new models; an explicit allowlist of assignable fields; status uses an Enum.
- Risky migration (large data, column change/drop): confirmation, rollback plan.

## 4. Backend
- Thin entry point/handler -> service or use-case layer -> data layer -> response mapping. Input validation with the framework's validation layer.
- One service or use case per use case; multi-step inside a transaction. Race condition risk in the PRD: check status inside the transaction and use a row lock.
- Business rules in the service or use-case layer and Enums. Violations: domain exception mapped centrally to the PRD error code (e.g. `ORDER_NOT_CANCELLABLE`).
- Authorization through the framework's authorization layer, deny by default; queries scoped to the owner (prevent IDOR).
- Strict typing where the language supports it, full type hints, doc comment on classes and public methods.

```php
public function cancel(CancelOrderRequest $request, Order $order, CancelOrderService $service): OrderResponse
{
    $this->authorize('cancel', $order);

    return new OrderResponse($service->execute($order, $request->validated('reason')));
}
```

## 5. API
- Under `/api/v1`, plural kebab-case. Authentication middleware and rate limit per the PRD's Auth column and security section.
- Status code = the PRD Error column, no more no less. Uniform success/error format, handled centrally in the framework's central error handler.
- Collections paginated with a capped `per_page`. Dates in ISO 8601 UTC.
- Update OpenAPI with the generator in `AGENTS.md`. Removing/renaming a field = breaking change.

## 6. Tests from ACs
- One AC = one or more tests; the name describes the behavior and **contains no PRD ID**. The ID map is filled **once at phase close** in the PRD-code index (`prd_tasks.py scaffold`, then `verify`):
```php
it('rejects cancelling a paid order with 409 ORDER_NOT_CANCELLABLE', function () { /* ... */ });
```
```ts
it('shows the validation error under the reason field', async () => { /* ... */ });
```
- Feature test for endpoints (status, JSON structure, authorization, validation, database effects); unit test for the service or use-case layer. Use the framework's testing helpers (transaction rollback between tests, factories, fakes for messages and mail).
- Every edge case in an AC and `T-###` scenario has a test; what cannot be realized (needs infrastructure) is recorded in the progress file.
- Frontend: user-visible behavior, tested at the component level. Async server-rendered components via an end-to-end runner or by extracting their logic. End-to-end tests only for the main Essential flow and only if an end-to-end harness already exists.

## 7. UI framework frontend
- **Route:** `/orders/{order}` becomes the route/view file of the framework, per the router in `AGENTS.md`. The route file only composes components from `features/`.
- **Server/Client:** server-rendered by default; client-rendered only for state/effect/event, as close to the leaf as possible.
- **Structure:** `features/<feature>/{components,logic,api,types}` + `index.ts` (name `logic` as the framework does: `hooks`, `composables`, `stores`); HTTP through a centralized API client in `lib/`.
- **Async state:** every screen handles loading, empty, and error per the State column in PRD Section 5 (the framework's loading/suspense convention and an error boundary per segment).
- **Form:** one consistent approach; show the validation errors on the fields, disable submit while pending.
- **Security:** the frontend only forwards to the backend; the framework's server endpoints and handlers without business/authorization logic and without secrets reaching the browser. Role checks in the UI are for UX only.
- Reuse existing components before creating new ones (`docs/FRONTEND.md`).

## 8. UI and text
- The UI is not worked on before the screen files exist (created by `project-prd`). Build the layout, components, and states they specify; do not invent product values.
- Reuse existing components; a new component is reusable, with names and variants exactly per the PRD.
- Implement all states, responsive behavior, and accessibility from the screen file.
- Display text goes through translation files using the PRD's translation keys. If no translation mechanism exists yet: propose the simplest option and ask for approval; do not add a library without a reason.
- Screen code locations are recorded in the PRD-code index (Screens section), **not** in the screen file.

## 9. Queue and notifications
Slow work (email, reports, webhooks) goes through a Queue; Jobs are idempotent with `tries` and `backoff`; dispatched after the transaction commits. Test with a fake: the effect happens exactly once.

## 10. Commit
- One commit per task or group of similar small tasks (`feat(scope)`, `fix`, `refactor`) containing the code and its tests; scope from the PRD Note column. A migration may be committed separately.
- Bulk formatting (if needed) in a separate commit (`style: apply formatter`), not mixed with logic.
