# Backend Standards

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

## Layered architecture

```
Entry point (input validation) -> Handler (thin) -> Service / use case (business logic)
                              -> Data access layer (data) -> Response mapping (output)
```

| Layer | Responsibility | Must not |
|---|---|---|
| **Route / entry point** | Endpoint definition, middleware | Any logic |
| **Input validation object** | Input validation & authorization | Business logic |
| **Handler** | Accept request, call service/use case, return response | Complex queries, business logic |
| **Service / use case** | Business logic, orchestration, transactions | Reading the raw request directly, HTTP response formatting |
| **Model** | Relations, scopes, accessors/mutators, casts | Heavy business logic |
| **Repository / data access object** *(optional, only for complex queries or when an abstraction is needed)* | Data access behind an interface | Business logic |
| **Response mapping / serializer** | Data transformation to the response structure (e.g. JSON) | Queries |
| **Authorization policy** | Per-model authorization | Input validation |

## Rules
- Use the language's strict typing mode (strict types, `strict: true`, or the equivalent) and declare type hints on parameters and return types; use `final` / `readonly` (or the language's equivalent) where appropriate.
- Follow the style and naming standards in [docs/CODE-STANDARDS.md](CODE-STANDARDS.md), format with **the project's formatter**, and run **static analysis**. Doc comments follow [docs/CODE-DOCUMENTATION.md](CODE-DOCUMENTATION.md).
- Validation in an **input validation object**, not in the handler.
- Use a **response object / serializer** for structured responses (e.g. JSON); do not return raw models.
- Use **the ORM** with *eager loading* to prevent N+1 issues. Avoid queries inside loops.
- Use a **database transaction** for multi-step operations.
- Use **migrations** for all schema changes, **factories** and **seeders** for test data. Do not modify migrations that have already run in production; create a new migration.
- Use **enums**, **authorization policies**, **queues/jobs**, **events/listeners**, and **the framework's config** for their intended purposes. Read environment variables only in the configuration layer, never in business code.
- Use a **DTO** or structured arrays for data passed between layers when there are too many parameters.
- Handle errors with specific exceptions and a centralized handler. Do not swallow exceptions (empty `catch`).
- Register interface to implementation bindings in a service provider / the framework's **service container**.
- Security: protect against mass assignment (an explicit allow-list of writable fields), SQL injection (parameter binding), XSS, CSRF; apply rate limiting and authorization on every sensitive endpoint.

## Correct pattern example
```
// Thin handler: validate, delegate, map
function store(request) {
    payload = validate(request, StoreOrderInput)   // input validation object
    order   = createOrderUseCase.execute(payload)  // service / use case
    return ok(OrderResponse.from(order))           // response mapping
}
```

## Logging and Error
- Use the framework's logger with the correct level (`debug`, `info`, `warning`, `error`) and **structured context** (a map/array), rather than embedding data in the message string.
- Include a *request/correlation ID* in logs (e.g. via middleware and the logger's context facility) so a single request can be traced.
- Do not log sensitive data (see [docs/SECURITY.md](SECURITY.md)). Unexpected exceptions are still reported to the centralized handler, not swallowed.
- Observability tooling (error tracking, APM, dashboard) is added only when it is actually needed (YAGNI).
