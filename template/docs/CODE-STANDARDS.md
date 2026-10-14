# Code and Language Standards

> Part of the agent guide. The summary and core rules are in [`AGENTS.md`](../AGENTS.md).
> Conversation with the user follows the user's own language (`AGENTS.md` § 4); this document covers what is written into files.

## Language rule: everything in code is in English

**English** is mandatory for:
- **Identifiers**: variables, functions, methods, classes, interfaces, enums (names and cases), constants, parameters, and types.
- **File and folder names**, routes/URLs, table and column names, API JSON keys, config keys, environment variable names, as well as event, job, and queue names.
- **Comments** and **doc comments** (see [docs/CODE-DOCUMENTATION.md](CODE-DOCUMENTATION.md); contents are limited to code explanations, author, and AI).
- **Log messages, exception messages**, and internal error messages.
- **Test names and descriptions**, e.g. `it('cancels a pending order')`.
- **Commit messages, branch names, and PR titles** (see [docs/GIT.md](GIT.md)).

How to write them:
- Use plain, clear English, with **one consistent spelling** across the whole project (e.g. American English).
- **Do not mix languages** and do not create half-local-language names (`getDataUser`, `hapusData`, `userNama`).
- Domain terms that have no standard English equivalent (e.g. official local document names) may be used as-is. Explain them in a doc comment where they are used.

**End-user display text** (UI labels, validation messages, email contents) is not covered by this rule, but it **must not be hardcoded** in logic or components. Store it in translation files (the backend's language files, JSON locale files in the frontend) with English keys. The display language follows product needs (e.g. `id`, `en`).

```
// Good: clear intent, one language, typed
function calculateOrderTotal(order: Order): int

// Bad: mixed language, vague name, no types
function hitungTotal(data)
```

## International standards in use

| Area | Standard | Reference in the project |
|---|---|---|
| Language style | The language's style guide and the framework's coding standard (classes, autoloading/module resolution, file layout), enforced by the formatter | The "Code style" section below |
| Lint, format, static analysis | The project's linter, formatter, and static analyzer run on every change | docs/BACKEND.md, docs/FRONTEND.md, docs/CI-CD.md |
| Editor | EditorConfig | `.editorconfig` |
| Characters | UTF-8, LF line endings | `.editorconfig` |
| Code documentation | The doc-comment format of the language | docs/CODE-DOCUMENTATION.md |
| Commit | Conventional Commits 1.0.0 | docs/GIT.md |
| Version | Semantic Versioning 2.0.0 | docs/GIT.md |
| Changelog | Keep a Changelog | docs/GIT.md |
| API | OpenAPI 3, HTTP semantics (RFC 9110) | docs/API.md |
| Time | ISO 8601 / RFC 3339, UTC | docs/API.md |
| Currency, country, language | ISO 4217, ISO 3166-1 alpha-2, BCP 47 | docs/API.md |
| Security | OWASP Top 10 | docs/SECURITY.md |
| Accessibility | WCAG 2.2 level AA | docs/FRONTEND.md |

## Naming

| Context | Convention | Example |
|---|---|---|
| Class, interface, trait, enum, type | `PascalCase` | `OrderService`, `OrderStatus` |
| Function, method, variable, property | `camelCase` | `calculateTotal()`, `orderItems` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Enum case | Pick one style in the project (`PascalCase` recommended) | `OrderStatus.Pending` |
| Component (UI) | `PascalCase`, filename matches the component | `OrderCard` |
| Custom hook | `useCamelCase` | `useOrders` |
| File | Same as the main symbol it contains; one casing style per area | `OrderService`, `api-client` |
| Database tables and columns | See [docs/DATABASE-PERFORMANCE.md](DATABASE-PERFORMANCE.md) | `order_items`, `created_at` |
| Route / URL | kebab-case, plural nouns ([docs/API.md](API.md)) | `/api/v1/order-items` |
| API JSON key | `snake_case` | `created_at` |
| Framework convention files | Fixed framework names, lowercase | `layout`, `error`, `not-found` |
| Environment variable | `UPPER_SNAKE_CASE`; the framework's public prefix only for public values | `APP_URL`, `PUBLIC_API_URL` |

General rules:
- **Names express intent.** Functions start with a verb (`calculateTotal`, `fetchOrders`). Booleans start with `is`, `has`, `can`, or `should` (`isActive`, `hasPaid`). Collections are plural (`orders`).
- Abbreviations are treated as ordinary words: `userId`, `ApiClient` (not `userID`, `APIClient`). Avoid uncommon abbreviations.
- No type prefixes (Hungarian notation) and no single-letter names, except for small loop indices or short lambdas.
- Avoid generic names (`data`, `info`, `temp`, `manager`) and do not make `helpers` / `utils` a dumping ground. Name them according to their responsibility.
- If frontend JSON keys are wanted as `camelCase`, do the mapping in **one place** (the API client); do not mix styles throughout the code.

## Code style

### Backend (server-side language)
- Enable the language's strict typing declaration in every file. Use type hints for parameters, return types, and properties; make use of `readonly`/`final` and enums (not string literals).
- One class per file; the namespace or module path follows the folder structure.
- Format with **the project's formatter** using the preset defined in its configuration file. Static analysis with the project's analyzer; the level is raised gradually and never lowered.

### Frontend (client-side language)
- `const` by default, `let` when needed, no `var`. Use ES modules.
- `strict` mode, no `any`. Do not blanket-ignore type errors; if unavoidable, use the language's expect-error directive with a reason.
- Format with the project's formatter and lint with the project's linter (including the framework's component and hook rules). One main component per file.
- Where the framework requires an explicit directive for a client-rendered file, write it on the first line and only on files that need it.
- Do not leave `console.log` behind; use a logger or centralized error reporting.

### General
- UTF-8, LF line endings, newline at the end of the file, indentation per `.editorconfig` (do not mix tabs and spaces).
- No dead code and no unused imports.
- Follow the official best practice of each language, library, and framework **at the version installed in the project**: idiomatic code, the API surface that actually exists, and the tool's own configuration. Verify against the official documentation of that version, never from memory or an old tutorial. A deliberate deviation from best practice is written as a short comment stating the technical reason (see [docs/CODE-DOCUMENTATION.md](CODE-DOCUMENTATION.md)).
- Tooling configuration (formatter, linter, static analysis, EditorConfig) is the **only source of style**. Do not add style rules elsewhere and do not fight the formatter.
