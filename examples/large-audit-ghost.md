# Case study: auditing Ghost (real large codebase) with the kit

Target: TryGhost/Ghost at a shallow snapshot (8,923 files; scanner counted 6,981 code
files, 1,138,573 lines). Method: full `scan.py` run plus targeted verification of every
Critical/High sample and the auth/security areas (sampling is mandatory at this size;
the method and its limits are stated below, not hidden). No code in the target was
changed; nothing was executed (no installs, no tests, no DB). `.env` contents shown
below are the entire files.

Adaptation, stated upfront: Ghost has its own guide (`AGENTS.md`, 4 KB) and a mature
custom culture. It was audited against the-maestro template standards, so mismatches
measure **adoption fit**, not Ghost's quality. A finding marked "culture mismatch" is
not a defect in Ghost.

## Scanner output vs verified reality

| Scanner claim | Verified reality |
|---|---|
| CRITICAL `secret.possible`: 86 | Sampled top hits: test fixtures (`'this-is-sufficiently-secure'`, `'current-password'` in `staff-password.acceptance.test.tsx`). No real secret confirmed in samples. Status: **needs verification per item**; the count alone means nothing. |
| CRITICAL `git.env-committed`: 6 | `.env.example` tracked (intended — and a **false positive introduced by our own batch-1 fix**, which flags any `.env.*` name; see follow-up F-1). `apps/portal/.env` and `apps/comments-ui/.env` tracked but their entire content is `REACT_APP_VERSION=$npm_package_version` — benign, though tracking `.env` files at all is a smell. |
| HIGH `frontend.token-in-browser-storage`: 2 | `auth-notice.ts:18` stores a UI notice enum under key `'ghost-admin:auth-notice'` — not a credential. **False positive**: the rule fires on any identifier containing `auth`. |
| HIGH `frontend.public-env-secret`: 6 | `settings-bread-service.js:384` matched `PUBLIC_SITE_ACCESS_LOCKED_KEYS` — **false positive caused by our own `KEY` addition** (batch 1): the pattern has no trailing boundary, so `KEY` matches inside `LOCKED_KEYS`. Fix proposed in F-2. |
| HIGH `sql.string-built`: 12 | Sampled migration uses ``knex.raw(`show index ... '${INDEX_NAME}'`)`` with a file-level constant — no user input. Verified safe; true-positive shape, false-positive risk. |
| MEDIUM `frontend.raw-html`: 141 | Sampled `feed-item.tsx`: every `dangerouslySetInnerHTML` wraps `sanitizeHtml(...)`. Verified safe pattern; the rule cannot see the sanitizer. |
| MEDIUM `layer.handler-data-access`, `error.swallowed`, `env.read`, `debug.leftover` | Spot-checked: mostly tooling/test/debug-vendor files. Each needs per-item reading; none confirmed as product defects in this pass. |
| LOW `doc.missing` 6200, `comment.missing-metadata` 3969, `comment.todo` 418 | Culture mismatch, not defects: Ghost does not require JSDoc everywhere, uses no `@author`/`@ai` headers, and tracks TODOs in context. Applying foreign header rules here would be vandalism, not quality. |
| LOW `ts.any` 50, `react.legacy-api` 68, `react.class-component` 25 | Plausibly real tech debt; unverified individually (sampling budget went to Critical/High). Recorded, not claimed. |

## Scanner self-diagnostics (the tool auditing itself, in effect)

- `architecture_guess: front end only` — wrong; Ghost has a large Express/Hono backend.
  The guesser failed on this monorepo layout.
- `frameworks` contains garbage values (`'react': 'catalog:'`); `tests.backend` and
  `tests.frontend` report the identical count (2144), i.e. double-counted, not measured twice.
- `Conventional Commits 0.0 of the last 1 commits` — an artifact of the shallow clone
  (1 commit of history), presented as a ratio without warning. Any ratio built on
  truncated history is meaningless; the output does not say the history is truncated.
- `git.env-committed` flags `.env.example` (our batch-1 regression, F-1).
- Counts (`6200`, `3969`, `3690`-line functions in test files) are dominated by tests,
  fixtures, and generated code — the output never separates product code from the rest.

## Verdicts (against the-maestro standards, with the adaptation above)

| Area | Verdict | Evidence |
|---|---|---|
| Backend architecture | Healthy | layered `ghost/core/server/{api,services,data}`, SoC visible in samples |
| Security posture | Healthy with notes | sanitized HTML, no real secrets found in samples; 2 High scanner hits both falsified on reading |
| Testing/tooling | Healthy | 2144 test files, eslint+ts+vitest+playwright configured, pinned runtime, lockfile, CI (25 workflows) |
| Documentation culture | Needs verification | 21% doc-comment coverage by our JSDoc-shaped rule; Ghost documents differently — cannot judge without their convention |
| Agent-guide fit | Partly healthy | own `AGENTS.md` exists; none of the twelve `docs/` files exist, so a the-maestro agent would operate half-blind here |

## What this proves about the kit (measured, this run)

1. Throughput is real: 1.1M lines scanned in one command; a human baseline of this repo
   would take days. The value is triage, not verdicts.
2. Precision collapses without verification: of 7 Critical/High claims sampled, 0 were
   confirmed as defects (5 falsified, 2 benign). An agent that pastes scanner output as
   findings would report fiction with citations.
3. The kit's own recent changes caused 2 of the false positives (F-1, F-2 below) —
   dogfooding caught them the same day.
4. Foreign-convention repos need a "culture mismatch" verdict class, which the current
   report template lacks; without it, audits read as accusations.

## Follow-ups (kit repo, proposed)

- F-1: exclude `.env.example` (and `*.example`) from `git.env-committed`. Effort: S.
- F-2: add a trailing word boundary to the `KEY` alternative in `frontend.public-env-secret`
  (and in `scan.py`'s `.env` content check) so `LOCKED_KEYS` no longer matches. Effort: S.
- F-3: warn when git history is truncated (shallow clone) instead of printing history-based
  ratios silently; separate test/fixture counts from product counts. Effort: M.
- F-4: add a "culture mismatch / not applicable" status to the audit report template so
  foreign-codebase audits do not present convention differences as findings. Effort: S.

## Limits

- Shallow snapshot: no history (churn sampling impossible), one point in time.
- ~10 findings individually verified out of ~13,000 heuristic hits; the rest are ungraded.
- No tests executed, no dependencies installed, no dynamic analysis; Ghost was never run.
- Operator knew the scanner's internals (bias toward finding tool faults over product faults).
