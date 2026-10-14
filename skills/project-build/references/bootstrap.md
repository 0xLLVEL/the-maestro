# New Project Bootstrap (Phase 0)

## When to use
The PRD covers a new application and the repository does not yet have the dependency manifests, or does not yet have tooling and CI per the standards (preflight: `project.scaffold`). Do it as **Phase 0** before Phase 1, with the same workflow (dedicated branch, approval). A project already running: skip this file.

Bootstrap only prepares the foundation; PRD features are not done here. Phase 0 is not in the PRD: record the steps below as Phase 0 tasks in `docs/build/<slug>.md`.

## Initial decisions (one batch, each item with a recommendation)
Fill the `_fill_` placeholders in `AGENTS.md` from the PRD answers (Section 6, Q-###) or ask once; do not ask twice.

| Decision | Recommendation |
|---|---|
| Layout | One repository, `backend/` and `web/` folders; separate only if the team needs it (prefixed tags, `docs/GIT.md`) |
| Routing | The framework's file-based router convention (if it has one) |
| Package manager | One package manager and one lockfile |
| Database | Per the PRD; if not specified, ask |
| Authentication | Per the PRD and `docs/SECURITY.md` (the framework's built-in session/SPA authentication if there is a login) |
| OpenAPI generator | Per `AGENTS.md`; if empty, propose one and ask for approval |

Versions: the latest stable release, recorded in the lockfile. Check the installer's `--help` and the official documentation, not memory.

## Steps: four commits, quality run once per commit
Branch `chore/bootstrap` from `main`. If the installer or network is unavailable, write the exact commands down and ask the user to run them.

1. **`chore(scaffold)`:** scaffold the backend and the frontend (typed, linted, with the framework's file-based router and its `src/` convention) + `.gitignore` (`.env`, the installed-dependency folders, build output) + backend and frontend `.env.example` (the public API URL, no secrets).
2. **`chore(tooling)`:** `.editorconfig`, the formatter configuration, the linter + formatter for the frontend, the compiler `strict: true` option, a runtime-version pin, static analysis at a starting level that is green. Bulk formatting, if any, in a separate commit. Run the quality commands once after this commit.
3. **`chore(foundation)`:** API foundation (`/api/v1`, centralized error handling in the framework's entry/config file, health check, CORS and the framework's built-in authentication per `docs/SECURITY.md`) + frontend foundation (`src/`, `features/`, `components/`, `hooks/`, `lib/` with a centralized API client, the framework's font convention, the framework's error/not-found conventions) + test harness (the stack's test runner for the backend and for the frontend, one smoke test each, plus a health check test). An end-to-end runner only if the PRD has critical flows worth it.
4. **`chore(ci)`:** CI workflow (backend and frontend jobs, `docs/CI-CD.md`) installed **after** the baseline is green, `README.md` (setup and running), `CHANGELOG.md`, and `AGENTS.md` without `_fill_` (show as a diff).

## What is not done
- Packages beyond the standard and PRD needs (global state manager, UI kit, framework accelerators, etc.); every dependency has a written reason.
- PRD features, domain models, or domain migrations. Secrets, production, push/tag/release.

## Exit criteria
- All quality commands in `AGENTS.md` run and are green on the empty repo; the results are recorded as the baseline in `docs/build/<slug>.md`.
- `AGENTS.md` without `_fill_`.
