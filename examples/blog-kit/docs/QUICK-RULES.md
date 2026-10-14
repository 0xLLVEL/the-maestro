# Quick Rules

> Compact card of the core rules. **Read this first**, then open the full documents (map in [`AGENTS.md`](../AGENTS.md)) only for the areas touched by the task. If there is a difference, the full document wins.

## Working
- Determine the task size (Small / Medium / Large, `AGENTS.md` § 3). Read the files touched and their neighbors, not the entire repository.
- Do only what is asked. Findings outside the scope are reported, not fixed silently.
- Read many files at once, write many files in one step, combine shell commands. Do not re-read or re-run things whose result will certainly be the same.
- Verify per task: related tests + lint/format/typecheck on the files that changed. The full suite and `build` only at phase close or before a PR.
- Fail twice on the same step: stop and report.

## Architecture
- Thin entry point -> service/use case -> data access -> response mapping. **Business logic only in the backend**: not in routes, handlers, UI components, server-rendered parts, route handlers, or server actions/endpoints defined in the frontend.
- Frontend: server-rendered parts by default, client-rendered boundary as close as possible to leaf components; all HTTP calls to the backend through a single API client in `lib/`; server state through a server state library; handle loading, error, and empty.
- Best practice: idiomatic code and the built-in mechanism of each language, library, and framework (at the installed version) before a custom one or a new package (`docs/CODE-STANDARDS.md`).
- Aim for functions ≲ 30 lines, files ≲ 300 lines, nesting ≤ 3 (guidelines, `AGENTS.md` § 2). DRY on the third occurrence. YAGNI: no parameters, config, or dependencies "just in case".

## Language and naming
- Everything in the code is in English: identifiers, file names, comments, log/exception messages, test names, commits, branches. Naming follows `docs/CODE-STANDARDS.md`.
- Display text for users goes through translation files, not hardcoded.

## Comments
- Comment content is limited to: code explanations, `@author` (name from `git config`), `@ai`. Forbidden: PRD ID or name, document links, issue numbers, TODO/FIXME, change history, commented-out code.
- Every code file you create has a header containing a summary + those two tags (no version, no email). Existing headers are left alone. Fetch `git config user.name` once per session. Do not invent the author or the AI.
- Doc comments are required for public APIs: **one sentence** that explains the contract, never a repeat of the name. No PRD references in code or test names (`docs/CODE-DOCUMENTATION.md`).

## Tests
- Tests are written together with the implementation in the same task. Bug fixes and critical business rules: write the failing test first.
- Test names explain the behavior, without PRD IDs. Do not delete, skip, or circumvent tests, lint, or CI.

## UI
- Reuse existing components; every state (loading, empty, error) is implemented; AA contrast, visible focus, and `prefers-reduced-motion` are respected (`docs/FRONTEND.md`).

## Security and Git
- Authoritative validation and authorization in the backend; the frontend is only for UX. Anything reachable from the browser (including frontend endpoints and actions) is a public endpoint. No secrets in code, logs, or commits; values with the framework's public env prefix are public. Details: `docs/SECURITY.md`.
- Work in a working branch with Conventional Commits; check `git diff --staged` before committing. Do not push to `main`, do not force push, do not create tags or releases, do not run destructive commands without explicit approval (`AGENTS.md` § 6).
- Behavior changed: update the relevant doc comment, OpenAPI, and README/docs in the same PR; `CHANGELOG.md` is updated at release time through the release flow ([docs/GIT.md](GIT.md)).
