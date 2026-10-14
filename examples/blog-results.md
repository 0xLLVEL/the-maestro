# Blog experiment: measured results (Phase 1: auth and posts)

Same scope built twice with zero-dependency Node.js 26 and SQLite: `examples/blog-kit`
(full kit workflow) vs `examples/blog-nokit` (freestyle, one pass). All numbers below
are measured, not projected.

## Raw numbers

| Metric | Without kit | With kit |
|---|---|---|
| App code | 1 file, 104 lines | 7 files, ~660 lines (`db`, `auth`, `posts`, `views`, `server`, `seed`, styles) |
| Project-authored docs | 0 | ~330 lines (PRD, 4 screens, progress, PRD-code index; template guide copy excluded) |
| Tests | 0 (one-off smoke script, uncommitted) | 14 (`node --test`), 9/9 ACs + 2/2 T scenarios connected in the index |
| Commits | 1 | 8 (planning, approval, auth, posts, style, PRD fix, index, comment fix) |
| Verification | smoke: register, create, list, homepage | `check_prd` clean, `verify` 33 OK / 13 explained MISS, tests 14/14 |
| Wall time | ~0.5 h rough estimate: single run incl. smoke-harness debugging, 0 user roundtrips | ~2.5 h rough estimate: single run incl. 4 user roundtrips and planning docs |

## Code comparison

### File structure

Without kit — one file does everything:

```text
examples/blog-nokit/
  blog.js   # routing + SQL + HTML + CSS + auth + posts (104 lines)
```

With kit — one layer per file, dependencies point inward:

```text
examples/blog-kit/
  server.js   # thin routes: parses, calls services, responds
  auth.js     # hashing, users, sessions, rate limit
  posts.js    # posts rules, visibility, pagination
  views.js    # HTML templates + escaping (no logic)
  db.js       # schema only
  styles.css  # styling only (separate commit)
  lang/en.json
  tests/      # auth.test.js, http.test.js
  scripts/seed.js
```

### Backend

| Practice | Without kit (`blog.js`) | With kit |
|---|---|---|
| Layering | SQL, HTML, and auth checks inline in route handlers | handlers call `auth.js`/`posts.js`; no SQL outside services; `views.js` holds no logic |
| Error shape | ad hoc strings (`{error: 'forbidden'}`) mixed with pages | uniform `{error: {code, message}}` with `UNAUTHORIZED/FORBIDDEN/NOT_FOUND/VALIDATION/CONFLICT` |
| Validation | none: empty titles accepted, fixed page size, uncaught bad JSON in places | username/password/title/body/status/page validated at the service boundary, 422 shapes |
| SQL | parameterized, but one interpolated fragment would go unnoticed | parameterized; the single interpolated fixed `WHERE` fragment was flagged by the scanner and verified safe |
| AuthZ | owner check inline; no role management; signature TODO | owner-or-admin in services, admin role endpoint, deny-by-default, all tested |

### Frontend

| Practice | Without kit | With kit |
|---|---|---|
| Styling | inline `<style>` + `style=` attributes from the first commit | unstyled skeleton first (`index.html` equivalent: `views.js` with zero `class`/`style`), `styles.css` later in its own commit |
| Output encoding | none: `${p.title}` raw (stored XSS, AF-001) | `escapeHtml` on every interpolation |
| Display text | hardcoded (`<h1>My Blog</h1>`, `Cannot divide…` absent) | `lang/en.json` keys; a test fails if a key is missing |
| States | empty list handled; 404 ad hoc (`'nope'` on editor path) | loading/empty/error per screen file; uniform 404/403/422 pages |

### Writing style and best practice

| Practice | Without kit | With kit |
|---|---|---|
| Naming | `me`, `J`, `H`, `clr`, `neg`, `pct`, single letters (`u`, `r`, `p`) | `sessionUser`, `sendJson`, `parsePaging`, `atLeast`; no cryptic abbreviations |
| Magic numbers | `7 * 864e5`, `LIMIT 10`, `32` scattered inline | `SESSION_TTL`, `LOGIN_LIMIT`, `MAX_PER_PAGE`, `MAX_BODY` constants |
| Function size | whole app is one 104-line file with a ~90-line request callback | all units small except `createApp` (169 lines, AF-006 — caught, not prevented) |
| Comments/docs | one `TODO`, no headers | one-sentence doc comments on every public unit, `@author`/`@ai` headers, doc comments 100% |
| Language | English code, but display text hardcoded | English code plus English keys; user text in translation files |
| Git | 1 commit, informative message | 8 Conventional Commits, one logical change each, verified with `diff --staged` |

### Tests

Without kit: no test files; behavior checked once with a throwaway smoke script (register,
create, list, homepage) that was never committed — the next change re-verifies nothing.
With kit: 14 tests, 6 service-level (hashing, sessions, forgery, roles) and 8 end-to-end
over HTTP, each named after the behavior it proves and mapped to AC/T IDs in the index,
so a future failure points at the broken requirement, not just a broken line.

## Security posture (verified by reading the code)

| Property | Without kit | With kit |
|---|---|---|
| Stored XSS via post title/body | **vulnerable**: rendered unescaped, no escape function exists | safe: `escapeHtml` on every output, covered by review |
| Session cookie forgery | **vulnerable**: signature never verified (`TODO` in code) | safe: HMAC verified constant-time, forgery test included |
| Password storage | scrypt, but compared with `!==` (timing leak) | scrypt with per-user salt, constant-time compare |
| Login rate limit | none | 50/hour per IP, in memory |
| Input validation | none (empty posts accepted) | username/password/title/body/status/page validated, 422 shapes |
| Authorization | owner check present, no role management at all | owner-or-admin on edits, admin role changes, reader/author/admin tests |
| Draft visibility | anonymous list hides drafts, but detail check is ad hoc | owner/admin-only drafts, tested both ways (T-002) |

## Scanner evidence (`scan.py` on both)

Without kit: 1 file scanned, 4 findings (`console.log`, hardcoded color, `TODO`, missing
file header). The XSS, the missing signature check, and the missing rate limit produced
**zero** findings: confirmed detector blind spots, now measured rather than suspected.

With kit: 9 files scanned, doc comments 100% of 33 units. Findings: 12 hardcoded colors
(design tokens would be over-engineering here; accepted), `console.log` in the CLI entry
and seed script (accepted practice, blunt rule), `process.env` reads in server bootstrap
(config layer, accepted), one HIGH `sql.string-built` on a template literal that only
interpolates a fixed `WHERE` fragment with fully parameterized values (verified safe:
true-positive pattern, false-positive risk — exactly the "heuristic, confirm it" contract),
and one self-caught `comment.prd-reference` violation in `auth.js`, fixed the same session.

The scanner also caught a real guideline breach on the kit side: `createApp` is 169 lines
against the 30-line guideline. The kit does not prevent breaches; it makes them visible.

## `verify` honesty check (kit side)

33 OK includes every AC, both T scenarios, all 9 endpoints' code refs, and all 4 screens.
13 MISS are all route/page heuristics that only recognize framework conventions; this
server dispatches manually. Each listed route is exercised live by the passing HTTP tests,
which is stronger evidence than the heuristic. Nothing was renamed or restructured to
make the checker green.

## Verdict

- Cost ratio for this scope: several-fold time on this single run (rough estimate, not
  stopwatch-measured), 4 roundtrips, ~10x lines (mostly docs and tests).
- What the cost bought, measured: 14 passing tests, 9/9 ACs connected, 0 known
  vulnerabilities vs 2 (XSS, session forgery) plus 4 hardening gaps on the freestyle side.
- Break-even logic: the freestyle blog needs one stored-XSS incident or one support
  session answering "why does this code exist" to cost more than the kit's upfront hours.
- Limits: n = 1 task, one operator, no replication; operator knew both sides (bias toward
  the kit); time figures are rough retrospective estimates, not stopwatch measurements
  (countable proxies: 8 vs 1 commits, 4 vs 0 roundtrips); only zero-dependency Node was
  tested; six-month maintenance behavior is still projected (see `blog-comparison.md`).
