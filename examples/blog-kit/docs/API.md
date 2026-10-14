# API Contract and Error Format

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

This contract locks in the cooperation between backend and frontend. Neither may guess the shape of the other's data.

## Endpoint
- All endpoints are under the version prefix: `/api/v1/...`. Incompatible (*breaking*) changes must be released as a new version (`/api/v2`).
- Resource names are plural nouns, lowercase, and kebab-case: `/api/v1/orders`, `/api/v1/orders/{order}/items`.
- Use HTTP methods according to meaning: `GET` (read), `POST` (create), `PUT/PATCH` (update), `DELETE` (remove). `GET` must not modify data.
- Actions that are not CRUD are modeled as a sub-resource or a clear verb: `POST /orders/{order}/cancel`.

## HTTP status codes
| Code | When used |
|---|---|
| `200` | Success (read/update) |
| `201` | Resource successfully created |
| `204` | Success without content (e.g. delete) |
| `401` | Not yet authenticated |
| `403` | Authenticated but not authorized |
| `404` | Resource not found |
| `409` | State conflict (e.g. order already cancelled) |
| `422` | Validation failed |
| `429` | Hit the rate limit |
| `500` | Server error (generic message, detail only in logs) |

## Response format
Success (the resource envelope shape, the default in most API frameworks):
```json
{ "data": { "id": 1, "status": "pending" } }
```
List with pagination:
```json
{ "data": [ ], "links": { }, "meta": { "current_page": 1, "per_page": 20, "total": 120 } }
```
Validation error (`422`) and other errors:
```json
{ "message": "The given data was invalid.", "errors": { "email": ["The email field is required."] } }
{ "message": "Order cannot be cancelled.", "code": "ORDER_NOT_CANCELLABLE" }
```
- Every error **must** have a `message`. Validation errors have `errors` per field. `code` (optional) is a stable machine-readable code, used by the frontend for logic, not the `message`.
- Error format is handled **centrally** in the framework's configuration and bootstrap files. Controllers and handlers do not compose their own error format.

## Data conventions
- Pagination is mandatory for collections (offset or cursor pagination); limit `per_page` (e.g. max 100).
- Filter, sort, and pagination through a consistent query string: `?status=pending&sort=-created_at&page=2&per_page=20`.
- Dates in ISO 8601 UTC. Money as an integer in the smallest unit or a decimal string, **not a float**.
- Use a single ID type across the entire API (integer, UUID, or ULID).
- Adding a field = compatible. Removing, renaming, or changing a field's type = **breaking change** (see docs/GIT.md).

## Documentation and types
- Document the API with **OpenAPI 3** (generator: see AGENTS.md § Project Context). Update it together with endpoint changes.
- The frontend defines response types in one place (`features/<feature>/types`), ideally generated from OpenAPI.
- Server-rendered components, route handlers, and server-side functions that call this API are ordinary API *clients*: they do not change the contract and do not compose their own error format.
