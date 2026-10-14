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
| Wall time | ~30 minutes, 0 user roundtrips | ~2.5 hours, 4 user roundtrips (questions, PRD approval, two gos) |

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

- Cost ratio for this scope: ~5x time, 4 roundtrips, ~10x lines (mostly docs and tests).
- What the cost bought, measured: 14 passing tests, 9/9 ACs connected, 0 known
  vulnerabilities vs 2 (XSS, session forgery) plus 4 hardening gaps on the freestyle side.
- Break-even logic: the freestyle blog needs one stored-XSS incident or one support
  session answering "why does this code exist" to cost more than the kit's upfront hours.
- Limits: n = 1 task, one operator, no replication; operator knew both sides (bias toward
  the kit); only zero-dependency Node was tested; six-month maintenance behavior is still
  projected (see `blog-comparison.md`).
