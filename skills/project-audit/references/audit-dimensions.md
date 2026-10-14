# Audit Dimensions

Contents: 1 Agent documentation · 2 Architecture · 3 Code principles · 4 Standards and language · 5 Doc comment · 6 API · 7 Database and performance · 8 Security · 9 Testing · 10 Git · 11 CI and tooling · 12 Frontend and accessibility · Sampling for large repos

**Checklists about what is right belong in the project's standards files (`docs/`), not here.** This file does not repeat them, so there is only one version of the rules. For each dimension, read the referenced standards file first, then use the guidance below to **gather evidence** and **determine severity**. The criteria for the Healthy / Partly healthy / Messy verdicts are in the table in `docs/REBUILD.md`.

## 1. Agent documentation and context
**Standards:** `AGENTS.md`, all of `docs/`.
**Check:** referenced documents exist and their links are valid; the placeholder `_fill_` is filled in; the commands in the Project Context section actually exist in `scripts` in the dependency manifests; stack facts in the documents match reality.
**Evidence:** `facts` and `project_checks` from the scanner; open the dependency manifests (the backend and the frontend one, if the project has both).
**Severity:** missing document or wrong command = Medium; empty placeholder = Low.

## 2. Architecture and layer separation
**Standards:** `docs/BACKEND.md`, `docs/FRONTEND.md`.
**Evidence:** rule `layer.handler-data-access`, `generic.large-file`, `generic.long-function`. Read the 3-5 largest entry points (controllers/route handlers) and 3-5 largest components. Look for `fetch(` / `axios` scattered across components. Look for "god class" via `metrics.biggest_files`.
**Severity:** widespread business logic in the HTTP/UI layer = High; isolated case = Medium.

## 3. Code principles (DRY, KISS, YAGNI, SOLID)
**Standards:** `AGENTS.md § Core Principles`.
**Evidence-gathering techniques:**
- **DRY:** `grep` characteristic snippets (query fragments, validation rules, data transformations) and count the occurrences; three or more is a candidate.
- **OCP:** `if/else` or `switch` chains on types/status that keep growing (`git log -p` on that file shows the growth).
- **DIP:** `new` dependencies directly in business logic.
- **YAGNI:** unused abstractions, parameters, columns, or dependencies (find usages with `grep`).

**Severity:** duplication in critical areas (payment, auth) = High; the rest Medium/Low.

## 4. Code standards and language
**Standards:** `docs/CODE-STANDARDS.md`.
**Evidence:** rule `lang.*`, the language-specific rules that apply (`php.missing-strict-types`, `ts.any`, `ts.ts-ignore`, `python.mutable-default`), the `ts.strict` check, and the `tooling.*` checks. Run the formatter check, the linter, and the type checker of each stack. Also check commit messages and test names manually.
**Note:** `lang.non-english-identifier` only matches a limited word list. Verify manually, and also look for names outside the list.
**Severity:** widespread mixed language = Medium; scattered cases = Low.

## 5. Doc comment
**Standards:** `docs/CODE-DOCUMENTATION.md`.
**Evidence:** metric `doc_comment` (coverage), rule `doc.missing`, `comment.todo`, `comment.prd-reference`, and `comment.missing-metadata`. Read a few existing doc comments to assess **quality**: one sentence that adds information beyond the name, not a repeat of it. The frontend is assessed manually because the scanner does not measure it.
**Comment rules:** the three allowed items and the prohibitions are in `docs/CODE-DOCUMENTATION.md` (one sentence, nothing beyond the name, metadata only in the file header). PRD references, other document references, document IDs, issue links, TODOs, and change history in code are findings. Still-useful PRD references move to the PRD-code index.
**Severity:** generally Low; Medium if core public APIs are completely undocumented, or PRD references are scattered across many files.

## 6. API
**Standards:** `docs/API.md`.
**Evidence:** the `api.versioned` check. Read the route definition file, a few response mappings, and the exception handler in the framework's entry/config file. The framework's route-listing command may be used if the environment is ready. Compare success and error responses across endpoints.
**Severity:** inconsistent error format = Medium; collections without pagination = Medium.

## 7. Database and performance
**Standards:** `docs/DATABASE-PERFORMANCE.md`.
**Evidence:** the `db.n-plus-one-guard` check (when the ORM has a known guard). Read the migration files. For N+1, look for loops that access relations: `grep -rn "foreach" <the project's source directories>` then open the results. Frontend: check the build/bundler configuration, client JavaScript size (the server/client rendering boundary), image usage, the server-side fetch cache strategy, and long lists.
**Severity:** N+1 on the main path or a missing index on large tables = High; the rest Medium/Low.

## 8. Security
**Standards:** `docs/SECURITY.md`.
**Evidence:** rule `secret.possible`, `git.env-committed`, `sql.string-built`, `php.mass-assignment`, `php.raw-sql-interpolation`, `python.shell-true`, `python.eval-exec`, `python.unsafe-deserialization`, `ruby.sql-interpolation`, `ruby.shell-interpolation`, `frontend.token-in-browser-storage`, `frontend.raw-html`, `frontend.public-env-secret`. Also check the framework's server endpoints: whether they check authorization and validation, and whether middleware is made the only guard. Read the CORS configuration, the route definition files, middleware, and authorization policies. Run the dependency audit for each stack. **Never print secret values.**
**Severity:** leaked secret or tracked `.env` = Critical; exploitable vulnerability = Critical/High; endpoint without authorization = High.

## 9. Testing
**Standards:** `docs/TESTING.md`.
**Evidence:** the `tests.backend` and `tests.frontend` checks; the results of running the tests. Look for skipped tests: grep for the test runner's skip markers in the tests directory. Check whether critical flows (auth, payment, authorization) have tests.
**Severity:** critical flow without tests = High; brittle or skipped tests = Medium.

## 10. Git and versioning
**Standards:** `docs/GIT.md`.
**Evidence:** the `git` section of the scanner output; `git log --oneline -30`; `git ls-files | head`. Branch protection cannot be audited from the repo, write "cannot be audited".
**Severity:** tracked `.env` = Critical; no commit convention = Low/Medium.

## 11. CI/CD and tooling
**Standards:** `docs/CI-CD.md`, the Project Context section in `AGENTS.md`.
**Evidence:** the `ci.pipeline`, `tooling.*`, `repo.*` checks. Read the CI configuration (for example `.github/workflows/*.yml`, `.gitlab-ci.yml`) and look for `continue-on-error` or disabled jobs.
**Severity:** no CI = High; missing tooling = Medium.

## 12. Frontend and accessibility
**Standards:** `docs/FRONTEND.md`, `docs/CODE-STANDARDS.md`.
**Evidence:** rule `frontend.*`, `react.*`, `ts.*`, and the `ts.strict` check. Read core UI components. Check contrast on the main color pairs. Look for an error boundary (by class/hook convention and by name) and the framework's error/convention files (the per-segment error file, a global error file, a loading file, a not-found file). Check whether the route/view file only composes components and whether the client-rendering boundary is placed as close to the leaf as possible. Check that every state (loading, empty, error) is handled.
**Severity:** missing Error Boundary or an unhandled state on the main flow = Medium; accessibility problems on the main flow = High.

## Sampling for large repos
If the repo is larger than ± 500 code files, do not read everything. Use:
1. **Churn:** `git log --since="6 months ago" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -20` (frequently changed files are the riskiest).
2. **Size:** `metrics.biggest_files` and `metrics.longest_functions` from the scanner.
3. **Per layer:** at least one example of each class/component type.
4. **Critical path:** auth, payment, and operations that change important data.

Write in the report which modules were sampled and which were not, so readers know the coverage.
