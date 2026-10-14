# Blog comparison: freestyle vs kit workflow (Phase 1: auth and posts)

Same scope built twice with zero-dependency Node.js 26 and SQLite: `examples/blog-nokit`
(one pass, no guide) vs `examples/blog-kit` (PRD v0.2, 4 screen skeletons, auth and post
services, 14 tests, light theme, PRD-code index). All numbers are measured; time figures
are rough retrospective estimates from a single run, not stopwatch measurements — they
include chat roundtrips. The hard, countable proxies are commits, files, and roundtrips
(8 vs 1 commits, 4 vs 0 roundtrips).

## File structure

Without kit — one file does everything (104 lines):

```text
examples/blog-nokit/
  blog.js   # routing + SQL + HTML + CSS + auth + posts
```

With kit — one layer per file, dependencies point inward:

```text
examples/blog-kit/
  server.js   # thin routes: parses, calls services, responds
  auth.js     # hashing, users, sessions, rate limit
  posts.js    # post rules, visibility, pagination
  views.js    # HTML templates + escaping (no logic)
  db.js       # schema only
  styles.css  # styling only (separate commit)
  lang/en.json
  tests/auth.test.js
  tests/http.test.js
  scripts/seed.js
  docs/prd/blog-phase-1.md
  docs/design/screens/   # 4 screens with unstyled skeletons
  docs/build/blog-phase-1.md
  docs/prd-reference/blog-phase-1.md
```

## Code style

| Practice | Without kit (`blog.js`) | With kit |
|---|---|---|
| Layering | SQL, HTML, and auth checks inline in route handlers | handlers call `auth.js`/`posts.js`; no SQL outside services; `views.js` holds no logic |
| Error shape | ad hoc strings (`{error: 'forbidden'}`) mixed with pages | uniform `{error: {code, message}}` (`UNAUTHORIZED/FORBIDDEN/NOT_FOUND/VALIDATION/CONFLICT`) |
| Validation | none: empty titles accepted, fixed page size | username/password/title/body/status/page validated at the service boundary, 422 shapes |
| Naming | `me`, `J`, `H`, `clr`, `neg`, single letters (`u`, `r`, `p`) | `sessionUser`, `sendJson`, `parsePaging`, `atLeast` |
| Magic values | `7 * 864e5`, `LIMIT 10`, `32` inline | `SESSION_TTL`, `LOGIN_LIMIT`, `MAX_PER_PAGE`, `MAX_BODY` constants |
| Function size | one ~90-line request callback | all units small except `createApp` (169 lines — caught by the scanner, see below) |

## Comment style

| Practice | Without kit | With kit |
|---|---|---|
| File headers | none (`comment.missing-metadata`) | `@author`/`@ai` on every created file |
| Doc comments | none | one-sentence contract per public unit; doc comments 100% of 33 units per the scanner |
| Dead comments | one `TODO` left in code (`TODO: verify cookie signature` — and the signature is indeed never verified) | no TODOs, no commented-out code, no PRD references (one self-found violation was fixed the same session) |

## Commit style

Without kit: 1 commit with an informative message, but no trace of decisions.
With kit: 8 Conventional Commits, one logical change each (planning docs, approval record,
auth plus tests, posts plus routes plus HTTP tests, styling, PRD fix, PRD-code index,
comment fix), each staged selectively and verified before committing.

## Best practice and verification

| Practice | Without kit | With kit |
|---|---|---|
| Tests | 0 (one-off smoke script, uncommitted; next change re-verifies nothing) | 14/14 `node --test`: 6 service-level, 8 end-to-end over HTTP, each mapped to AC/T IDs |
| Static checks | none | `check_prd` clean; `verify` 33 OK / 13 explained MISS (collectors only recognize framework conventions; every route is exercised live by the HTTP tests) |
| Security | stored XSS (unescaped output), unverified session signatures, `!==` password compare, no rate limit | escaping everywhere, HMAC verified constant-time (with forgery test), scrypt plus salt, 50/hour login limit, owner-or-admin checks |
| Time (rough) | ~0.5 h single run incl. smoke-harness debugging | ~2.5 h single run incl. 4 roundtrips and planning docs |

## Scanner evidence (`scan.py` on both)

Without kit: 1 file scanned; 4 findings (`console.log`, hardcoded color, `TODO`, missing
header). The XSS, the missing signature check, and the missing rate limit produced zero
findings: confirmed detector blind spots.

With kit: 9 files scanned. Findings: 12 hardcoded colors (tokens would be over-engineering
here; accepted), `console.log` in CLI entry/seed (accepted practice), `process.env` reads
in bootstrap (config layer; accepted), one HIGH `sql.string-built` on a template literal
that interpolates only a fixed `WHERE` fragment with fully parameterized values (verified
safe — true-positive shape, false-positive risk), and the long-function breach above.

## Verdict

- Cost for this scope: several-fold time on this run, 4 roundtrips, ~10x lines (mostly
  docs and tests).
- What the cost bought, measured: 14 passing tests, 9/9 ACs plus 2/2 scenarios connected,
  0 known vulnerabilities vs 2 High (XSS, session forgery) plus 4 hardening gaps.
- Break-even: one stored-XSS incident or one support session answering "why does this
  code exist" costs more than the upfront hours — true for operated code, false for
  throwaway code.
- Scale reading (projected, not measured): payoff grows with lifespan times contributors,
  not feature count. Preconditions for the large-scale claim: detectors for the risky
  rules, sampling rules for large repos, evidence-backed approvals (see `ROADMAP.md`).

## Limits

n = 1 task, one operator with a pro-kit bias, no replication; only zero-dependency Node
was tested; maintenance behavior is projected, not measured.
