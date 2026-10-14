# Refactor Playbook

Contents: 1 Business logic in entry points · 2 Unvalidated input binding and string-built SQL · 3 N+1 · 4 Environment reads outside config · 5 Types and strict typing · 6 Large files and functions · 7 Duplication · 8 Frontend: logic in components · 9 Frontend: types, legacy APIs, Error Boundary · 10 Token in browser storage · 11 Language and UI text · 12 Doc comment · 13 Tooling and CI · 14 Tests for critical flows · 15 Git hygiene

Every playbook follows the cycle in `SKILL.md` (behavior lock, change, verify, review, commit). The details of the target rules live in the project's `docs/`; read the referenced standards file before starting. Code examples only illustrate the shape, not a template to be copied blindly.

## 1. Business logic in entry points
**Standards:** docs/BACKEND.md. **Target:** thin entry point/handler, logic in a service or use-case layer, input validation, response mapping.
1. Write a feature test for the endpoint (status, JSON structure, effects on the database).
2. Move validation to a dedicated input-validation layer.
3. Extract the logic into one service or use case per use case (one responsibility). Wrap multi-step operations in a transaction.
4. The entry point only calls the service and returns the mapped response.
5. Run the same test and ensure the result does not change.

```php
// After: the entry point only validates, delegates, and maps the response
public function store(StoreOrderRequest $request, CreateOrderService $service): OrderResponse
{
    return new OrderResponse($service->execute($request->validated()));
}
```
**Be careful:** do not roll behavior changes (e.g. fixing a bug you found) into this refactor. Record that bug separately.

## 2. Unvalidated input binding and string-built SQL
**Standards:** docs/SECURITY.md.
- Unvalidated input binding (`Model::create($request->all())`) becomes binding of only the validated fields (`Model::create($request->validated())`), with an explicit allowlist of assignable fields on the model. Add a test that disallowed fields are ignored.
- Raw queries with string interpolation become parameterized queries (bound values) or a query builder.
- If the change makes input that was previously accepted now rejected, that is a behavior change: confirm with the user.

## 3. N+1
**Standards:** docs/DATABASE-PERFORMANCE.md.
1. Reproduce: write a test that counts the number of queries on a scenario with many rows.
2. Eager-load the relations that are accessed (the ORM's `with()`/`load()` style); select only the columns needed.
3. Enable the framework's lazy-loading guard in a service provider (disabled in production) so regressions are detected.
4. Ensure the query count drops and the results are identical.

## 4. Environment reads outside config
Move every environment read (`os.environ`, `process.env`, `ENV[...]`, `os.Getenv`, `System.getenv`, `env()`, and the like) into the configuration layer, expose the values through the framework's configuration accessor, and replace the usages. Add new variables to `.env.example`. If the deploy caches configuration, ensure no environment reads remain outside the configuration layer.

## 5. Types and strict typing
**Standards:** docs/CODE-STANDARDS.md.
- Enable strict typing/`strict` mode per module, not all at once across the whole repo, then run tests to catch behavior changes caused by type coercion.
- Add type hints to parameters, returns, and properties. Raise the static analysis level gradually; use a *baseline* file for old debt so CI does not turn red immediately, then shrink the baseline over time (it must not grow).
- TypeScript: enable `strict` and fix errors per folder; use `unknown` + type narrowing instead of `any`.

## 6. Large files and functions
**Standards:** AGENTS.md § Core Principles (heuristic thresholds).
1. Ensure there is a characterization test for its behavior.
2. **Extract method** for blocks that have one clear purpose; name it after that purpose (a verb).
3. **Extract class** when a group of methods and data has one responsibility of its own.
4. Replace growing `if/switch` chains with strategy/interface (OCP).
5. One extraction per commit; run tests after each extraction.

## 7. Duplication
**Rule of three:** extract when the same logic appears for the third time. Ensure the duplicates are *truly the same in intent*, not merely similar by coincidence with different reasons to change. First check whether an existing helper/service/hook can be used. Extract to one place, replace usages one at a time, test after each replacement.

## 8. Frontend: logic in components
**Standards:** docs/FRONTEND.md.
- **Scattered fetches:** move them to a centralized API client and a custom hook per feature (`useOrders`). Use a server state library if the project already uses one.
- **Giant component:** separate presentational components (UI) from hooks (data/logic). Only the props that are used.
- **Unnecessary effect:** derive the value from state/props during render, not via an effect that only computes it.
- **Fetch in a client-rendered component that could be server-rendered:** move the initial data fetching to a server-rendered part, set cache/revalidation explicitly, and leave client-rendered parts only for the interactive parts.
- **The client-rendering boundary placed too high in the component tree:** move the boundary to leaf components. Ensure the props sent to client-rendered components are only the fields that are used.
- **Business logic in the framework's server endpoints:** return it to the backend (service/use-case layer) and leave the frontend layer as a thin proxy. This can change the API contract, so follow docs/API.md.
- Test what is visible to the user, not implementation details. Async server-rendered components are tested via an end-to-end runner or by extracting their logic (docs/TESTING.md).

## 9. Frontend: types, legacy APIs, Error Boundary
- `any` becomes the correct type in one place, ideally aligned with the API/OpenAPI contract.
- Class component becomes function component + hooks (exception: Error Boundary). Legacy ref/API patterns (forwarding refs, default-prop objects, prop-type maps, the legacy root render API) are replaced with the current function component patterns (ref as a prop, default parameters, types, the current root API).
- Add a global and per-feature Error Boundary with a meaningful fallback and centralized error reporting. Use the framework's error convention per route segment, plus a library-based boundary for the client-rendered parts outside those.

## 10. Token in browser storage
Moving the token to an `httpOnly` cookie (an SPA/session-based flow) changes the authentication flow in backend and frontend at once, including how requests from the server forward the session cookie to the backend (docs/SECURITY.md). This is **breaking** and high risk: confirm with the user, do it as its own item, with tests for the login/logout flow, and a transition plan for currently active sessions.

## 11. Language and UI text
**Standards:** docs/CODE-STANDARDS.md.
- Rename internal identifiers to English per module with IDE/automated rename tooling so all references change as well; run tests afterward.
- Renaming a public API (route, JSON key, table/column) = breaking, requires confirmation and migration.
- Hardcoded UI text is moved to translation files (the language directory, locale JSON) with English keys; the text values do not change.
- Comments and log/exception messages are translated while passing through that module; do not translate en masse outside the plan.

## 12. Doc comment
**Standards:** docs/CODE-DOCUMENTATION.md.
Complete the public API per module: a one-sentence summary, meaningful `@param`/`@throws`, rich doc types. Do not write docblocks that only repeat the name. Run static analysis afterward because the types in the docblock are checked as well.

## 13. Tooling and CI
**Standards:** docs/CI-CD.md, AGENTS.md § Project Context.
A safe order (one commit per step):
1. `.editorconfig`, the formatter and linter configuration of every stack in the project.
2. **Mass format** in one separate commit with no other changes.
3. Static analysis with a baseline, then ratchet up gradually.
4. A CI workflow that runs format, static analysis, tests, lint, typecheck, build, and dependency audit.
5. A runtime-version pin and one dependency lockfile.

Install the CI gate **after** the code passes the baseline, not before, so the pipeline does not turn red from day one.

## 14. Tests for critical flows
**Standards:** docs/TESTING.md.
Start from the riskiest flows (auth, payment, authorization, operations that change important data). Write feature tests for endpoints and unit tests for the service or use-case layer. Tests must be deterministic and independent. Do not chase coverage numbers; prioritize critical paths.

## 15. Git hygiene
**Standards:** docs/GIT.md.
- `.gitignore`: add `.env`, the installed dependencies directory, build output. Files already tracked are untracked with `git rm --cached <file>` (not deleting the local file).
- Create `CHANGELOG.md` if it does not exist yet. Tags and releases **only** on the user's explicit instruction.
- Do not rewrite shared history.
