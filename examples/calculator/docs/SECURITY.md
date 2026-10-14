# Security

> Part of the agent guide. The summary and core rules are in [`AGENTS.md`](../AGENTS.md).

Applies to all new and modified code. Reference: OWASP Top 10.

## Backend
- **Authentication**: use the framework's built-in authentication (session, token, or OAuth). Do not build your own auth system. Passwords are hashed with the framework's password hashing helper, never stored or logged as plaintext. Use the built-in email verification and password reset.
- **Authorization**: use authorization checks (policy, guard, or middleware) on every action, with the **deny by default** principle. Prevent IDOR: queries must be scoped to the owner or authorized per model.
- **Validation and mass assignment**: use input validation (schema, DTO, or validation object), and pass only the validated fields forward. Passing the raw request payload straight into a create/update call is prohibited. Declare the writable fields explicitly in the model/entity definition.
- **SQL injection**: use the ORM/query builder with bound parameters. Do not interpolate input into raw queries without binding.
- **XSS**: the templating layer escapes output by default; avoid the raw-output escape hatch for user input.
- **CSRF**: active for web/session routes; for an SPA with a token-based auth setup, use the CSRF-cookie handshake flow of that mechanism.
- **CORS**: whitelist origins explicitly in the framework's configuration and bootstrap files. Never use `*` with credentials.
- **Rate limiting**: mandatory on login, password reset, and public or expensive endpoints.
- **File upload**: validate type and size, do not trust the extension, store on a non-public disk under a random name, serve via a signed URL when needed.
- **Configuration**: debug mode off and production environment in production, HTTPS mandatory, `secure` + `httpOnly` + `sameSite` cookies, plus security headers (HSTS, `X-Content-Type-Options`, CSP where possible).
- **Logging**: do not record passwords, tokens, or personal/sensitive data. Mask PII.
- **Errors**: the user receives a generic message without a stack trace; details go only to the log.

## Frontend
- Do not store sensitive tokens in browser web storage such as `localStorage` (vulnerable to XSS). Prefer `httpOnly` cookies.
- Do not put secrets in environment variables that the framework exposes to the browser bundle: their value is embedded at build time and is public. Secrets belong only in server-only variables, read by server code.
- Props passed from a server-rendered component to a client-rendered component are sent to the browser. Send only the fields the UI needs, not the full response object.
- **Server-side functions (server actions, route handlers, and any server-rendered endpoint) are public HTTP endpoints.** Authentication, authorization, and authoritative validation stay in the backend. If a server-side function does something itself, check its authorization and input validation inside it with the *deny by default* principle. Where the framework compares the `Origin` and `Host` headers for server-side calls, that does not replace CSRF protection in the backend.
- For a cookie/session-based SPA setup, the frontend and API must share the same parent domain, and requests made from the frontend's server must forward the session cookie to the API explicitly. Verify the flow in the documentation of the installed framework versions.
- Do not make frontend framework middleware the sole authorization gate (there was once a vulnerability that allowed a middleware bypass in older versions). Checks there are for UX only; enforcement is in the backend.
- Avoid the framework's raw-HTML injection escape hatch; if unavoidable, sanitize first. Validate redirect URLs to prevent *open redirects*.
- Role/permission checks in the frontend are for UX only. Enforcement is always in the backend.

## Dependency and supply chain
- Run the dependency audit command for every stack in CI as well. Apply security patches as soon as possible, including for the frontend framework itself: monitor its security advisories and update to patch releases immediately. Minor/major upgrades still need an explicit request ([`AGENTS.md`](../AGENTS.md) § 1).
- Commit the lockfile. Add packages only from trusted, still-maintained sources.
- Enable an automated dependency-update bot (e.g. Dependabot, Renovate) for automatic dependency updates (via PR, still passing CI and review).

## When finding a security problem
If an agent finds a vulnerability or a leaked secret, **stop**, report it to the user clearly, and do not fix it quietly outside of scope. Never write a secret to code, logs, commits, or output.
