# PRD: Blog Phase 1 (auth and posts)

| Field | Value |
|---|---|
| Status | Draft |
| Version | 0.2 |
| Date | 2026-10-14 |
| Slug | blog-phase-1 |

## 1. Summary
Phase 1 of the online blog: cookie-session auth with three roles, post CRUD with drafts,
and a public paginated list, in zero-dependency Node.js with SQLite. Key decisions: first
registered user becomes admin; posts are plain text (no markdown library); light readable
style assumed until the user corrects it.

| Role | Main access rights |
|---|---|
| Reader | read published posts |
| Author | reader rights plus create and edit own posts |
| Admin | author rights plus publish any post, delete any post, manage users |

**Not a goal:** comments, likes, image upload, themes, email verification, password reset.

## 2. Feature Catalog
Priority: **Essential** (without this the goal fails), **Important** (the next phase), **Optional**. Origin: **Requested**, **Implicit essential** (derived so the requested feature works; can be rejected), **Recommended**.

| ID | Feature | Description | Priority | Origin | Phase |
|---|---|---|---|---|---|
| F-001 | Auth and roles | Register, login, logout with signed cookie sessions; roles reader, author, admin. | Essential | Requested | 1 |
| F-002 | Post authoring | Authors create, edit, and delete own posts as draft or published. | Essential | Requested | 1 |
| F-003 | Public reading | Paginated published list and post detail as HTML and JSON. | Essential | Requested | 1 |

**Out of scope:** comments, likes, upload, search, password reset, styling beyond the assumed light direction.

## 3. Acceptance Criteria
### F-001 Auth and roles
- AC-F001-1: Given a new username and password, when registering, then the user is created and the first user has the admin role.
- AC-F001-2: Given valid credentials, when logging in, then a signed session cookie is set and protected pages open.
- AC-F001-3: Given a reader session, when creating a post, then the API answers 403 `FORBIDDEN`.
- AC-F001-4: Given an admin session, when changing a user's role, then the new role applies on the next request.

### F-002 Post authoring
- AC-F002-1: Given an author session, when creating a draft, then it is stored unpublished and invisible to the public list.
- AC-F002-2: Given the owning author or an admin, when publishing a draft, then it appears in the public list.
- AC-F002-3: Given a post owned by another author, when editing it, then the API answers 403 `FORBIDDEN`.

### F-003 Public reading
- AC-F003-1: Given 25 published posts, when opening page 2 with `per_page=10`, then posts 11-20 render with page links.
- AC-F003-2: Given a published post id, when opening its URL, then title, body, author, and date render.

## 4. Business Rules and Flow
- Passwords are stored as scrypt hashes with per-user salt, never in plain text.
- Sessions are random 256-bit tokens in signed cookies; logout deletes the server session.
- Only admins assign roles; the first registered user becomes admin automatically.
- Drafts are invisible without an author or admin session; deleted posts are gone (no trash).

## 5. Design

| ID | Slug | Name | Route | Feature | Components | State |
|---|---|---|---|---|---|---|
| SCR-001 | auth-pages | Auth pages | /login | F-001 | Reuse: none / New: auth-form | loading: n/a, empty: n/a, error: invalid credentials |
| SCR-002 | post-list | Post list | / | F-003 | Reuse: none / New: post-card, pager | loading: n/a, empty (no posts), error: n/a |
| SCR-003 | post-detail | Post detail | /posts/{id} | F-003 | Reuse: post-card / New: post-body | loading: n/a, empty: n/a, error: 404 |
| SCR-004 | post-editor | Post editor | /editor | F-002 | Reuse: none / New: editor-form | loading: n/a, empty: n/a, error: validation 422 |

**Translation key:** `blog.title`, `blog.login`, `blog.logout`, `blog.register`, `auth.invalid`, `posts.empty`, `posts.delete-confirm`, `error.forbidden`. Display text is never hardcoded; accessibility (WCAG 2.2 AA) applies by default and is not written again here (`docs/CODE-STANDARDS.md`, `docs/FRONTEND.md`).

## 6. Technical Specification
Only what **cannot** be inferred from the standards.

**Data:** tables `users(id, username unique, hash, salt, role)`, `sessions(token primary key, user_id, expires_at)`,
`posts(id, author_id, title, body, status, created_at, updated_at)`; index on `posts(status, created_at)`.

| ID | Endpoint | Auth | Feature | Summary | Error |
|---|---|---|---|---|---|
| API-001 | `POST /api/v1/auth/register` | none | F-001 | Create user; first user becomes admin. | 422, 409 |
| API-002 | `POST /api/v1/auth/login` | none | F-001 | Start session, set cookie. | 401, 429 |
| API-003 | `POST /api/v1/auth/logout` | session | F-001 | Delete session, clear cookie. | 401 |
| API-004 | `GET /api/v1/posts` | none (drafts need author session) | F-003 | Paginated published list (`page`, capped `per_page`). | 422 |
| API-005 | `POST /api/v1/posts` | author | F-002 | Create draft or published post. | 401, 403, 422 |
| API-006 | `GET /api/v1/posts/{id}` | none (drafts need owner or admin) | F-003 | Single post. | 404 |
| API-007 | `PATCH /api/v1/posts/{id}` | owner or admin | F-002 | Edit title, body, status. | 401, 403, 404, 422 |
| API-008 | `DELETE /api/v1/posts/{id}` | owner or admin | F-002 | Delete post. | 401, 403, 404, 422 |
| API-009 | `PATCH /api/v1/users/{id}` | admin | F-001 | Change a user's role. | 401, 403, 404, 422 |

**Security and performance:** scrypt with per-user salt; deny by default on every mutating endpoint; rate limit on login (50/hour per IP, in-memory); post list uses `LIMIT/OFFSET` with capped `per_page=50`.

## 7. Testing
Every AC becomes a test. This table is only for scenarios **outside AC** (concurrency, idempotency, integration); write `None.` when there are none.

| ID | Level | Feature | Scenario |
|---|---|---|---|
| T-001 | Feature | F-001 | Session cookie cannot be forged (tampered signature is rejected). |
| T-002 | Feature | F-002 | Draft is invisible to anonymous list and detail requests. |

## 8. Implementation Plan
Phases in order by dependency. Tasks the size of one build cycle (merged when small and of the same kind). The Notes column: branch name (`feature/...`) and commit scope.

### Phase 1 - auth and posts
| Task | Feature | Effort | Notes |
|---|---|---|---|
| Auth + roles + tests | F-001 | M | example/blog-kit branch, users/sessions layer first |
| Posts + pagination + tests | F-002, F-003 | M | same branch, service layer then routes |
| Skeleton UI + style | F-001, F-002, F-003 | S | same branch, separate commits; light direction per A-002 |

Release: no flag needed (new app); roll back by reverting the merge.

## 9. Risks, Assumptions, and Open Questions
| ID | Type | Description | Mitigation / impact if wrong |
|---|---|---|---|
| A-001 | Assumption | Single-node SQLite is enough for Phase 1 traffic. | Move sessions/posts to a server database later. |
| A-002 | Assumption | Light readable style with system fonts is acceptable. | Restyle after user feedback. |
| Q-001 | Open question | Public registration open, or invite-only? | Assumed open; roles stay deny-by-default either way. |
| R-001 | Risk | Cookie theft on non-HTTPS local use. | `HttpOnly` plus `SameSite=Lax`; `Secure` when served over HTTPS. |
