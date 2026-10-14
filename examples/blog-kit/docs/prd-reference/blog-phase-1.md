# PRD Reference: Blog Phase 1 (auth and posts)

| Field | Value |
|---|---|
| PRD | docs/prd/blog-phase-1.md (version 0.2) |
| Last updated | 2026-10-14 |

## Features
| Feature | Code |
|---|---|
| F-001 | `auth.js::createUser` |
| F-002 | `posts.js::createPost` |
| F-003 | `posts.js::listPosts` |

## Acceptance criteria
| AC | Test file | Test name | Code |
|---|---|---|---|
| AC-F001-1 | `tests/http.test.js` | `creates the first user as admin` | `auth.js::createUser` |
| AC-F001-2 | `tests/http.test.js` | `sets a session cookie on login` | `auth.js::createSession` |
| AC-F001-3 | `tests/http.test.js` | `answers 403 when a reader creates a post` | `server.js` |
| AC-F001-4 | `tests/http.test.js` | `applies role changes on the next request` | `auth.js::setUserRole` |
| AC-F002-1 | `tests/http.test.js` | `keeps drafts invisible until published` | `posts.js::createPost` |
| AC-F002-2 | `tests/http.test.js` | `keeps drafts invisible until published` | `posts.js::updatePost` |
| AC-F002-3 | `tests/http.test.js` | `answers 403 when editing someone else post` | `posts.js::updatePost` |
| AC-F003-1 | `tests/http.test.js` | `paginates the public list with page links data` | `posts.js::listPosts` |
| AC-F003-2 | `tests/http.test.js` | `renders a post page with title, body, author, and date` | `posts.js::getPost` |

## Test scenarios
| Scenario | Test file | Test name |
|---|---|---|
| T-001 | `tests/auth.test.js` | `rejects a forged session cookie signature` |
| T-002 | `tests/http.test.js` | `keeps drafts invisible until published` |

## Endpoints
| Endpoint | Code |
|---|---|
| API-001 | `server.js` |
| API-002 | `server.js` |
| API-003 | `server.js` |
| API-004 | `server.js` |
| API-005 | `server.js` |
| API-006 | `server.js` |
| API-007 | `server.js` |
| API-008 | `server.js` |
| API-009 | `server.js` |

## Screens
| Screen | Code |
|---|---|
| SCR-001 | `views.js::authPage` |
| SCR-002 | `views.js::listPage` |
| SCR-003 | `views.js::detailPage` |
| SCR-004 | `views.js::editorPage` |
