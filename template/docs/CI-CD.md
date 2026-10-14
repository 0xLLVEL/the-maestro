# CI/CD

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

## CI pipeline (GitHub Actions)
Runs on every Pull Request and every push to `main`. All jobs must be green before merging (*required status checks*). Use action versions that are stable and actively maintained.

| Job | Steps |
|---|---|
| **Backend** | Set up the backend runtime (per AGENTS.md § Project Context), install dependencies with cache, the formatter (check mode), static analysis, the test runner with coverage, the dependency audit command |
| **Frontend** | Set up Node LTS, install dependencies with cache (including the build cache), the linter, typecheck, test, the production build, the dependency audit command |
| **Optional** | E2E (Playwright, Cypress) for critical flows, only if there is already a flow worth testing end-to-end |

- **Coverage**: set a minimum threshold (e.g. 80% for new code, especially Services/Actions) and **coverage must not decrease**. Do not chase numbers; prioritize business logic and critical paths.
- Failing CI jobs **must not** be skipped, disabled, or set to `continue-on-error` to make them green. Fix the cause.
- Secrets are stored in GitHub Secrets or the platform environment, never in the repository.
- Environment variables that are baked into the bundle at build time are set in the build step, not only at runtime.

## CD (deploy)
- Deploy from `main` or a release tag (docs/GIT.md), through a **staging then production** flow.
- Migrations run with a safe strategy (docs/DATABASE-PERFORMANCE.md). Prepare a rollback plan before any deploy that includes migrations.
- The backend and the frontend are two applications that run separately. Define deploy targets for both, and if the API contract changes, deploy the backward-compatible backend first.
- Provide a *health check* after deploy, for both backend and frontend. CD automation is built only if deploy targets already exist (YAGNI).

Definition of Done (including the green CI and review requirements) is in [`AGENTS.md`](../AGENTS.md).
