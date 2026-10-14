# Roadmap

Every item below traces to a measured finding: the defect audit, the calculator/blog
experiments, or the read-only audit of both blog builds. Items without such a root are
not listed. Versioning follows [Semantic Versioning](https://semver.org).

## 0.1.2 — small fixes with proof

- [ ] Split `examples/blog-kit/server.js:createApp` (169 lines, AF-006) into route tables
  per area; scanner must report no `generic.long-function` on the examples. (Open.)
- [ ] Teach `collect_pages` the root `index.html` case (static sites report
  `SCR-*.page` MISS today; explained, not fixed). (Open.)
- [x] Ghost-audit scanner self-fixes (F-1–F-4, done 2026-10-14): `.env.example` excluded
  from `git.env-committed`; trailing word boundary on the `KEY` alternative;
  shallow-clone warning plus test/product file split in metrics; `N/A (culture
  mismatch)` status in the report template.
- [x] Merge the pending example/audit PRs (done: #8–#18).

## 0.2.0 — enforcement before scale claims

The large-scale advantage (see `examples/blog-comparison.md`) stays projected until these
close. Each item ships with a detector or gate plus a self-test, never prose alone.

- [ ] Detectors for the risky rules that are text-only today: missing authorization check
  per mutating endpoint, missing rate limit on auth endpoints, CORS wildcard with
  credentials, unsafe upload handling, query-in-loop (N+1 heuristic). The blog-nokit
  findings AF-002/AF-003 produced zero scanner hits — that must become impossible.
- [ ] Sampling rules for large repos: replace "about 500 files, use sampling" with a
  deterministic method (churn + size + layer coverage) and a required scope statement in
  the audit report, so partial audits cannot pose as full ones.
- [ ] Evidence-backed gates: `cannot be run` must attach command output; progress
  `Verification` columns must reference logs; PRD approval must be a verbatim quote.
  Kills the self-attested `pass` class of loopholes.
- [ ] Strict-typing and naming checks beyond PHP/TS (`docs/BACKEND.md` already demands
  them for every stack; the scanner only checks two).
- [ ] Scanner coverage for plain frontends: dependency-free `.html`/`.js` pages currently
  scan as 0 files with 0 findings (measured on both freestyle demos).

## Later — unknown, needs data first

- [ ] Artifact expiry: when a PRD index or progress file may be archived or deleted
  (stale traceability misleads more than none; no rule exists yet).
- [ ] Multi-agent conventions: branch/PR ownership when two agents work one repo.
- [ ] Agent-behavior evals: the `evals/` folders describe checks that need an agent to
  run them; automate what is automatable before claiming workflow compliance.
- [ ] Re-measure the with/without cost ratio on a second task with an independent
  operator (current ratio ~5x time is n = 1 with a pro-kit operator).

## Non-goals

- New skills before the five existing ones are enforced by script where enforceable.
- Framework-specific scaffolding or dependencies: the kit stays standard-library-only.
- Style opinions beyond what a project already configures (`--style-checks` stays opt-in).
