<!-- the-maestro 0.1.1 -->
# AGENTS.md

Guide for AI agents working in this repository. This document is intentionally concise: the core rules live here, **the details live in `docs/`**. Before working on an area, read the relevant document.

**Start with [docs/QUICK-RULES.md](docs/QUICK-RULES.md)** (the compact core-rule card, ~1 minute read). Open the full documents below only for the areas your task touches.

| You are working on | Read first |
|---|---|
| **Every code change** (naming, style, language, doc comment) | [docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md) and [docs/CODE-DOCUMENTATION.md](docs/CODE-DOCUMENTATION.md) |
| Backend (entry points, services, models, logging) | [docs/BACKEND.md](docs/BACKEND.md) |
| Frontend (routes, components, hooks, state, forms) | [docs/FRONTEND.md](docs/FRONTEND.md) |
| Endpoint, request/response, API error | [docs/API.md](docs/API.md) |
| Database, query, caching, performance | [docs/DATABASE-PERFORMANCE.md](docs/DATABASE-PERFORMANCE.md) |
| Auth, user input, upload, dependency | [docs/SECURITY.md](docs/SECURITY.md) |
| Writing or fixing tests | [docs/TESTING.md](docs/TESTING.md) |
| Commit, branch, PR, versioning, release | [docs/GIT.md](docs/GIT.md) |
| CI/CD and deploy | [docs/CI-CD.md](docs/CI-CD.md) |
| Messy code or something that needs rebuilding | [docs/REBUILD.md](docs/REBUILD.md) |
| **Asked to audit** the project (whole project or part of it) | Skill `project-audit` (mandatory): read-only; report in `docs/audit/`; fixes only after the plan is approved |
| **Asked to apply audit results** or a wide refactor | Skill `project-refactor` (mandatory): starts from the latest audit report; dedicated branch, safety tests, small commits |
| **Asked to build / implement from a PRD** | Skill `project-build` (mandatory): the PRD decides what, `docs/` decides how; phase by phase on a dedicated branch; progress in `docs/build/<slug>.md` |
| **Asked to prepare a release**, determine a version, changelog, release notes, or hotfix | Skill `project-release` (mandatory): prepares version, changelog, and release PR; tags and releases only on explicit instruction |
| **Asked to write a PRD** or plan a full feature | Skill `project-prd` (mandatory): ask for context first; PRD in `docs/prd/<slug>.md`; no code before the PRD is approved |

## 1. Project Context

| Component | Choice |
|---|---|
| Backend stack | Node.js 26 (built-in `http`, `crypto`, `node:sqlite`; no framework, no dependencies) |
| Frontend stack | Server-rendered HTML (no client JS framework; tiny inline scripts only where needed) |
| Runtime versions | Node v26.10.0 (via `node --version`) |
| Router / entry point | `server.js` (built-in `http` router) |
| Package manager | n/a (zero dependencies, no manifest) |
| Database | SQLite via `node:sqlite` (file `blog.db`, created on first run) |
| Architecture | Routes -> services -> SQLite -> HTML responses + JSON API under `/api/v1` |
| OpenAPI generator | n/a (API documented in the PRD; no generator without dependencies) |

### First run: fill in this section
If any row or command in this section still holds its placeholder value, **fill it before doing anything else**, once per project:
1. **Detect, don't guess.** Read the manifests and config in the repository root (dependency manifests such as `package.json`, `composer.json`, `pyproject.toml`, `go.mod`, `Gemfile`, `pom.xml`/`build.gradle`, `Cargo.toml`, or a `.csproj`; lockfiles, runtime pins such as `.nvmrc` or `.python-version`, `.editorconfig`, `Makefile`, `docker-compose.yml`, CI files, the router/entry-point files, the DB config without reading `.env` values). Versions come only from the manifest and lockfile.
2. **Fill every row** with the detected value. If a row cannot be detected (for example a brand-new empty repository), ask the user one batched question and use the answer. Write `n/a` only when the component truly does not exist in this project.
3. **Fill the commands block** below from the real `scripts` in the manifests; delete the lines that do not apply.
4. **Confirm with the user** in 1-3 sentences (what was detected, what was assumed), then continue the original task.
5. Do not edit the rest of this file during this step. Once no placeholder value remains, this subsection is done.

### Version rules
- **The single source of truth for versions** is the dependency manifest and its lockfile (for example `package.json` / lockfile, `pyproject.toml` / lockfile, `go.mod` / `go.sum`, `Gemfile` / `Gemfile.lock`, `composer.json` / `composer.lock`). Never guess a version.
- Use only APIs that exist in the installed version; when in doubt, check the official documentation for that version or the code of the installed dependencies. Frameworks change between major versions (configuration structure, caching, request APIs, file conventions), so do not rely on old tutorial patterns, and do not mix conventions from different major versions.
- Follow the current idioms of the framework version in use; avoid APIs that version has removed or deprecated.
- Upgrading a major/minor version or a core dependency is allowed only on **explicit request**, on a dedicated branch, after reading the upgrade guide. Never downgrade a version just to avoid an error.

### Project commands
Fill from the `scripts` in the project's manifest files (see "First run" above). If they later differ from this list, follow those files and update this section.

```bash
# Initial setup
install dependencies:   n/a (zero dependencies)
configure environment:  n/a (SQLite file created on first run)
create and seed the DB: node scripts/seed.js (optional demo data)

# Development
run the app:            node server.js (http://localhost:3000)

# Quality
format check:           n/a (no formatter configured)
static analysis:        n/a
tests:                  node --test tests/
dependency audit:       n/a (zero dependencies)
build:                  n/a (no build step)
```

Code formatting is determined by `.editorconfig` and the formatters of each stack as the only source of style. Do not format manually or add new style rules anywhere else. Naming and style standards: [docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md).

## 2. Core Principles (Mandatory)

- **DRY**: the same logic appearing for the third time, extract it. Check existing helpers/services/hooks first. No premature abstraction.
- **KISS**: the simplest solution; prefer the built-in features of the stack and framework in use before a new package or pattern; use *early return*.
- **YAGNI**: only what is requested now; no parameters, config, columns, or dependencies "just in case".
- **SOLID**: one unit, one reason to change; add behavior through an interface/strategy instead of `if/switch` chains; implementations must be substitutable for their abstractions; interfaces and props stay small and specific; depend on abstractions and inject dependencies (business collaborators are injected, never `new` inside business logic; `new` stays allowed for value objects, DTOs, exceptions, and collection literals).
- **Best practice**: follow the official best practice of each language, library, and framework **at the installed version**, and prefer the built-in mechanism over a custom one or a new package. A deliberate deviation carries a one-line technical reason in a comment. Verify against the official documentation of that version, never from memory ([docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md)).
- **SoC**: thin entry point -> service / use case -> data layer -> response mapping. Presentational UI is separated from reusable logic (hooks, composables, stores) and data. Business logic **must not** live in the entry point, route, UI component, or the framework's server-side rendering layer; it stays in the backend.
- **Abstraction**: it has to simplify, not add empty layers.
- **Readability**: names express intent; no *magic numbers/strings* (use an Enum or a constant); identifiers **in English** ([docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md)).
- **Documentation**: doc comments are **mandatory** on public APIs, concise (one sentence for the contract, never a repeat of the name; extra lines only as allowed by [docs/CODE-DOCUMENTATION.md](docs/CODE-DOCUMENTATION.md)), and updated with the code. Comments hold only code explanations, the author (name from `git config`), and the AI used: no PRD, document, or issue references and no TODOs. PRD-to-code references live in `docs/prd-reference/<slug>.md` ([docs/CODE-DOCUMENTATION.md](docs/CODE-DOCUMENTATION.md)). Delete dead code; update the README and docs when behavior changes.
- **Testability**: dependencies are injected; new features and bug fixes come with tests (a bug fix starts with a failing test).
- **Version Control**: small commits with Conventional Commits on a working branch ([docs/GIT.md](docs/GIT.md)).

**Anti-spaghetti** (guidelines for new code, not hard limits; adjust them here and the audit follows): write new functions ≲ 30 lines, files ≲ 300 lines, nesting ≤ 3 levels. The audit scanner flags functions above 50 lines (`--max-func-lines`) and files above 300 (`--max-file-lines`) as heuristics that must be confirmed by reading the code, not as approvals. No "god class" or giant component, no copy-paste, no business logic in the HTTP/UI layer.

## 3. Workflow and Pace

### Task size decides the flow

| Size | Characteristics | Flow |
|---|---|---|
| **Small** | ≤ 3 files, no risky areas (auth, payments, migrations, API contracts, dependencies) | Read [docs/QUICK-RULES.md](docs/QUICK-RULES.md) and the files you touch -> change -> related tests -> lint/format the changed files -> commit -> a 1-3 sentence report. No progress file, no new screen file (except when the PRD defines new screens) |
| **Medium** | One feature, endpoint, or screen | Small flow + tests from the acceptance criteria + the documents that change with it (OpenAPI, screen files when the PRD defines new screens). |
| **Large** | A PRD phase, a rebuild, risky areas | The flow of the relevant skill (`project-build`, [docs/REBUILD.md](docs/REBUILD.md)): plan -> task by task -> phase close (full verification, report) |

Common steps for every size:
1. **Understand and validate conventions.** Read the files you touch and their neighbors, then briefly check the conventions of that area. *Healthy*: follow the existing pattern. *Partial*: follow the healthy parts, fix only the area you touch. *Messy*: rebuild through [docs/REBUILD.md](docs/REBUILD.md) (a dedicated branch, a plan and an audit report first, characterization tests, module by module).
2. **Plan** the smallest change that solves the problem. A written plan only for Large size.
3. **Implement** in the right layer, with tests and doc comments written alongside it.
4. **Verify in a targeted way** (the pace rules below), then **report** (section 4).

### Pace rules (apply to every flow)
- **Read only what you need.** Start from [docs/QUICK-RULES.md](docs/QUICK-RULES.md); open the full documents in the table above only for the areas your task touches. Do not read all of `docs/` at the start of a session.
- **One step, many actions.** Read several files at once, write several files in one step, and chain consecutive shell commands (`a && b`).
- **Don't repeat.** Do not re-read files you already read and that have not changed, and do not re-run checks whose results will certainly be the same. `git config` and the project versions are read once per session.
- **Layered verification.** Per task: related tests and lint/format/static analysis/typecheck on the changed files only (e.g. the formatter in diff mode, the linter on single files, the test runner's `--filter`/`-t` option). The full suite, `build`, and the dependency audit are run **once at the close of a phase or before a PR**, not per task.
- **Documents are written once.** Progress files, the PRD index, and design files are updated at the close of a phase (or when stopping mid-phase), not per task. The status of tasks when resuming can be read from `git log`.
- **Stop when stuck.** Failing twice on the same step, or no real progress: stop, report the cause, and ask for direction. Don't spin.

### Skills
The mandatory skills are listed in the table at the top. If the skill you need is not available, tell the user and do not substitute an improvised version for it.

## 4. Agent Behavior

**Honest and accurate**
- **Never invent** APIs, methods, packages, flags, or commands. Verify in the project code or the official documentation; if you cannot, say so clearly.
- **Read before writing.** Trace usage before changing or deleting something (within the pace rules above: search the repository with grep, read the files you touch and their neighbors; a full read of the repository is never required).
- Do not claim "already tested/passing" without actually running it. Report failures as they are and acknowledge uncertainty.

**Ask or proceed**
- **Ask first** if the requirement is ambiguous with a large impact, the decision is hard to reverse (deleting data, changing the DB schema, a breaking API change), or there are options with significant trade-offs. Pose one clear question along with a recommendation.
- **Proceed on your own** if the details are small, easy to reverse, and there is a clear convention. State the assumption in the report.

**Scope and security**
- Do **only what was asked**. Findings outside the scope are reported, not silently fixed (exception: the rebuild procedure). Break large tasks into small, verifiable steps.
- If you find a vulnerability or a leaked secret: **stop** and report. Never write secrets to code, logs, commits, or output.

**Language and Git**
- Communicate with the user in the language the user writes in (English if unclear); everything written to files stays in English. Everything in the code (identifiers, file names, comments, doc comments, log/exception messages, test names) as well as commit messages, branch names, PR titles, and every document (PRD, audit report, changelog, release notes, progress file) is **always in English** ([docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md)). End-user display text is not hardcoded; keep it in translation files.
- Commit only on a working branch according to [docs/GIT.md](docs/GIT.md), and check `git diff --staged` before committing.

**Final report format**
Small: 1-3 sentences (what was changed, test and lint results, risks if any). Medium and Large: the format below; delete empty sections.
```
## Summary
What was done in 1-3 sentences.

## Changes
Files/areas that were changed along with the reasons.

## Testing
The commands that were run and their results.

## Assumptions and decisions
Assumptions that were taken and the reasons behind them.

## Risks and items that need human review
Impact, concerns, or findings outside the scope.
```

## 5. Definition of Done

Work is complete once every item is met, CI is green, and the PR is approved by at least one reviewer:

- [ ] Matches the request and the acceptance criteria; scope is preserved
- [ ] Core principles are met: no duplication, no business logic in the controller/UI, clear naming
- [ ] Code and comments follow [docs/CODE-STANDARDS.md](docs/CODE-STANDARDS.md) and [docs/CODE-DOCUMENTATION.md](docs/CODE-DOCUMENTATION.md): English, concise doc comments on new or changed public APIs, a header on new files, no PRD references or TODOs
- [ ] Tests are added or updated and passing; coverage does not drop ([docs/TESTING.md](docs/TESTING.md), [docs/CI-CD.md](docs/CI-CD.md))
- [ ] Lint, format, static analysis, typecheck, and build are clean (the full suite and build run once per phase or before a PR)
- [ ] Security is checked ([docs/SECURITY.md](docs/SECURITY.md)); the API contract and OpenAPI are updated ([docs/API.md](docs/API.md)); migrations are production-safe ([docs/DATABASE-PERFORMANCE.md](docs/DATABASE-PERFORMANCE.md))
- [ ] The PRD-code index is filled for the phase (`prd_tasks.py verify` passes; only when the work is built from a PRD — Small tasks without a PRD skip this item)
- [ ] Documentation and `CHANGELOG.md` are updated; no `TODO`/`FIXME` or debug code is left
- [ ] Commits and the PR follow [docs/GIT.md](docs/GIT.md)

## 6. Absolute Prohibitions

- Running the stack's destructive reset commands (dropping or wiping a database, resetting migrations, `git reset --hard`, mass deletion) without explicit approval, or touching the production environment and non-local data.
- Reading, printing, or committing `.env` and secrets.
- Pushing to `main`, force pushing to shared branches, rewriting commits that were already pushed, or creating tags/releases/bumping a version without explicit instructions.
- Disabling, skipping, or gaming tests, lint, or CI jobs to make the results green.
- Performing a large rebuild outside the [docs/REBUILD.md](docs/REBUILD.md) procedure.
- Adding a dependency without an explained reason, or sending project code/data to an external service.
