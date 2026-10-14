# Frontend Standards

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

The frontend calls the backend as an API ([docs/API.md](API.md)). The frontend is the presentation layer: business logic, authorization, and database access remain in the backend ([docs/BACKEND.md](BACKEND.md)).

This document is written for component-based web frontends (React, Vue, Svelte, Angular, Solid, and similar) and for the meta-frameworks built on them (Next.js, Nuxt, SvelteKit, Remix, Astro, and similar). Use the vocabulary of the framework recorded in AGENTS.md § Project Context:

| Term used here | React | Vue | Svelte | Angular |
|---|---|---|---|---|
| Reusable logic unit | custom hook (`useXxx`) | composable (`useXxx`) | store or rune-based module | service or signal helper |
| Reactive state | state hook | `ref` / `reactive` | `$state` / store | signal |
| Derived value | computed during render | `computed` | `$derived` | `computed` |
| Error boundary | error boundary component | `onErrorCaptured` | `<svelte:boundary>` / `handleError` | `ErrorHandler` |
| Server-side endpoint inside the frontend | server action, route handler | server route | form action, `+server` | server route (SSR) |

If the project uses an alternative routing style, the file names below change accordingly, but the rules stay the same. Do not add new features in a routing style that is not the project's choice.

## Structure (feature-based)

```
src/
  <route directory>/       # routes: page, layout, loading, error, not-found, server endpoints
  features/<feature>/
    components/            # feature-specific components
    logic/                 # feature-specific reusable logic (hooks, composables, stores)
    api/                   # feature API calls
    types/                 # types/interfaces
    index                  # feature public API (barrel)
  components/              # UI components reusable across features
  logic/                   # reusable logic across features
  lib/                     # API client, utils, constants
```

- Name the logic folder as the framework's convention does (`hooks/`, `composables/`, `stores/`) when the project already follows one.
- The route directory contains only routing and assembly. Page and layout files compose components from `features/` and hold no logic of their own.
- Route folders use `kebab-case` ([docs/CODE-STANDARDS.md](CODE-STANDARDS.md)).

## Server-rendered and client-rendered parts

This section applies where the framework renders on the server (SSR, server components, islands). In a purely client-rendered SPA, only the points about secrets, serialization, and calling the backend API still apply.

- Components are **server-rendered by default** (where the framework supports it). Mark a part as client-rendered only when it needs state, effects, event handlers, or browser APIs, and place the boundary as close as possible to the leaf components so that the JavaScript sent to the browser stays small.
- Reactive-state and effect logic is only used in client-rendered parts.
- Props passed from server-rendered to client-rendered parts must be serializable and **are all sent to the browser**. Send only the fields the UI uses, not the full response object, and never secrets.
- Code that reads server secrets or environment variables may only be imported from server code. The framework's server-only guard (if it exists) may be used as an extra safeguard with the user's approval (YAGNI).
- Server-rendered parts and server-side endpoints inside the frontend only call the backend API. No direct database access, and no duplicating backend business logic or authorization.
- Fetch a page's initial data in the server-rendered part. Interactive data (filtering, polling, mutations) goes through the client-rendered part with a server state library. Do not use an effect to fetch data that can be fetched on the server.
- Set the **cache and revalidation strategy explicitly** on every server-side fetch. Default behavior differs between framework versions, so refer to the documentation for the installed version. User-owned data must not go into a cache shared between users.
- Use the framework's convention files (loading, error, not-found, layout) for their intended function; do not reimplement the mechanism yourself.
- Use the framework's navigation, image, and font modules/loaders for their respective purposes.

## Rules

- Use the framework's **current component model** (for example function components and hooks in React, the Composition API in Vue, runes or stores in Svelte, standalone components and signals in Angular). Legacy styles (class components in React, the Options API in Vue for new code) are forbidden in new code; the only exception is an error boundary that the framework cannot express any other way.
- Use **TypeScript** (if the project uses it) with `strict: true` and avoid `any`; for untrusted data use `unknown` and then narrow the type. If the project uses JavaScript, use the language's type annotations consistently. Do not use the framework's legacy runtime prop-type checking.
- **One component = one responsibility**. Separate *presentational* components (UI) from logic (reusable logic unit or container).
- Extract reusable logic into a **reusable logic unit**. A component must not hold fetching logic, data transformation, and UI all at once.
- All HTTP calls to the backend go through a **single centralized API client layer** in `lib/`. Do not write raw HTTP calls scattered across components. If two variants are needed (server and browser), both share the same types, base URL, and error handling.
- Use a *server state* library in client-rendered parts for data from the API when it is already used in the project, and do not store server data in manual local state.
- Avoid excessive *prop drilling*: use composition, the framework's dependency-injection or context mechanism, or a state manager only when necessary (YAGNI). Context can only be used in client-rendered parts.
- Avoid unnecessary effects and watchers. Derive values from state/props and do not synchronize state with an effect without a reason.
- Use a stable key in lists, and declare effect dependencies completely and correctly. Obey the framework's lint rules.
- Code naming and style follow [docs/CODE-STANDARDS.md](CODE-STANDARDS.md). Doc comments for exported components, reusable logic units, and utils follow [docs/CODE-DOCUMENTATION.md](CODE-DOCUMENTATION.md).
- Accessibility (a11y): use semantic elements, form labels, `alt` attributes, and keyboard support.
- Handle **loading, error, and empty** state on every async data source. In file-based routers, loading uses the framework's loading convention or the equivalent suspense boundary.
- Format with **the project's formatter**, lint with **the project's linter**. No new warnings are allowed.
- Do not store tokens/secrets in frontend code. Values marked with the framework's public environment prefix (for example `NEXT_PUBLIC_`, `VITE_`, `NUXT_PUBLIC_`, `PUBLIC_`) are **public** by definition; the full rule is in [docs/SECURITY.md](SECURITY.md) and the naming rule in [docs/CODE-STANDARDS.md](CODE-STANDARDS.md).

## Frontend - Backend Contract

- API responses must be consistent (the same success/error structure). The frontend does not guess the shape of data; define its types.
- Validation in the frontend is only for UX. **Authoritative validation remains in the backend.**
- Display backend validation error messages (422) on the corresponding field.
- Server-side endpoints inside the frontend that forward requests to the backend pass status and error format through as-is; they do not compose their own error format.

## Error Boundary and Error Handling

- Use the framework's **error convention** per route/feature segment, a root-level error handler for errors in the root layout, and a not-found page for 404. Where the convention file must be client-rendered, it accepts a `reset`/retry function for the "try again" option.
- For areas not covered by convention files, use the framework's error boundary mechanism (see the table above), or an error boundary library where the framework has none.
- Show a meaningful fallback UI together with a "try again" option, and report errors to centralized logging (from the error handler, plus the framework's root error callbacks where relevant). For server-side errors, check the framework's request-error hook (see the documentation for the installed version).
- In production, error messages from server-rendered parts are often masked and carry only a digest/reference ID. Match the digest against server logs and do not leak details to the user.
- An error boundary only catches errors during render. Errors in event handlers and async processes (fetch) **must** be handled explicitly through error state or errors from the server state library. Expected errors sent to a server-side endpoint (for example a validation failure) are returned as a value/state, not thrown.

## State and Form

- Order of preference for where to keep state: local state -> lift to the parent -> shared context (data that rarely changes) -> an external store **only** when proven necessary (YAGNI). Data from the server stays in the server state library.
- **Form**: pick one approach across the whole project (the framework's native form handling, for example a server action or a form action, or a single form library in a client-rendered part) and do not mix them.
- **A server-side form endpoint is a public HTTP endpoint that only forwards to the backend.** Authentication, authorization, and authoritative validation remain in the backend. It holds no business logic and no authorization logic of its own; if forwarding is impossible, treat the need as a backend change instead.
- Client-side validation uses a schema when the language supports it. Display 422 errors from the backend on the corresponding field, disable the submit button while pending, and prevent *double submit*.

## UI and accessibility

- Reuse existing components before creating new ones; a component used in more than one place is made reusable. Do not create two components for the same need.
- **Skeleton first.** Every new screen or component starts as a skeleton: semantic tags in the stack's own syntax (HTML, JSX/TSX, Vue/Svelte templates) and content only, with **no styling at all** (no `class`/`className`, no `style`, no CSS file). Reused existing components keep their styles; the rule covers new structure and new code. Visual design (colors, spacing, typography) is a separate later step and happens only when the user asks for it. Never deliver styled UI unprompted, and never present two visual alternatives unless asked.
- Implement every state (loading, empty, error) and the accessible behavior required by the screen file (when the PRD defines screens, at `docs/design/screens/<slug>.md`, written by the `project-prd` skill).
- Accessibility: AA contrast, visible focus, and `prefers-reduced-motion` respected (see [docs/CODE-STANDARDS.md](CODE-STANDARDS.md)).
- Display text goes through translation files, never hardcoded (see [docs/CODE-STANDARDS.md](CODE-STANDARDS.md)).
