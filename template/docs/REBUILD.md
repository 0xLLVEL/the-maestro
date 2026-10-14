# Convention Validation and Rebuild Procedure

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

Do this **before** working on the first task in the repository (or in a new code area). Do not simply copy an existing pattern just because it already exists.

## Step 1 - Audit
Check a representative sample: folder structure, entry points/handlers, services and use cases, data models, UI components, hooks, API client, tests, and lint/format configuration. Assess them with the following indicators:

| Indicator | The convention is considered HEALTHY when | The convention is considered MESSY when |
|---|---|---|
| Consistency | Naming, structure, and style are uniform | Many mixed styles for the same thing |
| Layer separation | Per docs/BACKEND.md and docs/FRONTEND.md | Business logic in an entry point, route, UI component, or browser-reachable endpoint |
| Unit size | Functions/classes/components are small and focused | Files > 300 lines, functions > 50 lines, "god class" |
| Duplication | Shared logic has been extracted | Copy-paste scattered in many places |
| Testing | There are running and meaningful tests | No tests, or broken/skipped tests |
| Tooling | Lint, formatter, static analysis are active and clean | None, or full of violations/ignored |
| Visual consistency | Visual values and components are reused consistently across the app | Hardcoded values scattered everywhere, duplicate UI components for the same need |
| Code and documentation standards | Per docs/CODE-STANDARDS.md and docs/CODE-DOCUMENTATION.md | Mixed languages, inconsistent naming, public APIs without doc comments |
| Security & performance | Validation in the backend, no N+1, no hardcoded secrets | N+1 present, hardcoded secrets, validation only in the frontend |
| API contract | Per docs/API.md: version, uniform response and error format, pagination | Inconsistent response/error formats, collections without pagination |
| Process (Git and CI) | Per docs/GIT.md and docs/CI-CD.md: Conventional Commits, CI runs the quality gates | No CI, commit history without conventions |

> The numbers in the table (300 lines per file, 50 lines per function, the scanner defaults) are an **initial heuristic**; the guideline targets in `AGENTS.md` § 2 are stricter for functions. Adjust them to the project's character.
>
> This table is the **single source of criteria** for the Healthy / Partly healthy / Messy verdict. The `project-audit` skill uses it and does not copy its criteria.

## Step 2 - Decision
- **Healthy**: follow the existing pattern. Do not create a new style.
- **Partly healthy**: follow the healthy parts. Fix the messy parts only in the areas touched by the task.
- **Messy**: rebuild the related code and apply the new style per this document's standards (Step 3).

## Step 3 - Rebuild Procedure (if messy)
1. Work in a dedicated branch (`refactor/<area>`), **never** directly on `main`.
2. Write a brief **audit report and rebuild plan** (what is messy, what will be rebuilt, module order) before starting to change code.
3. Write **characterization tests** first to lock in the current behavior (endpoints, output, important UI flows) so the rebuild does not change functionality.
4. Rebuild **module by module**, not as one giant change. One module = one small commit/PR (`refactor: ...`).
5. Apply the new style per AGENTS.md § Core Principles, docs/BACKEND.md, and docs/FRONTEND.md. Preserve behavior and API contracts unless asked otherwise. Database schema changes must go through a new safe migration.
6. Delete old code only after its replacement passes tests, lint, and static analysis.
7. Record the new style in use in `docs/CONVENTIONS.md` so it stays consistent for future work.

## Step 4 - Report
Once finished, report the audit results, the decisions made, the modules rebuilt, and the risks/behavior that need human review.
