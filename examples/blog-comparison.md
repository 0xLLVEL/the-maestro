# Large-scale comparison: online blog, with kit vs without kit

Projection for one realistic mid-size product built by AI agents over six months.
Blog scope (3 phases, 11 features): public reader (post list with pagination, post page,
SEO metadata, RSS), accounts (register, login, roles reader/author/admin), authoring
(drafts, markdown editor, image upload, scheduled publish), engagement (comments with
spam guard, likes), admin (moderation queue, user management).

Status labels: **measured** (from the calculator experiment or kit self-tests),
**projected** (reasoned estimate, stated assumptions), **unknown** (no data).

## Lifecycle comparison

### Month 0-1: scaffolding and first features

| Aspect | Without kit | With kit |
|---|---|---|
| Setup | agent picks stack from memory; fast (projected: hours) | first-run detection fills `AGENTS.md` from manifests, then builds (projected: +1 day of docs) |
| Auth foundation | works, but authorization shape varies per endpoint (measured pattern in freestyle code: mixed styles) | `project-prd` forces the Auth column per endpoint; deny-by-default reviewed once (projected) |
| Early tests | happy-path only (measured: 0 tests in the freestyle demo) | every AC becomes a test (measured: 6/6 ACs connected in the demo) |

### Month 2-3: feature rush (comments, uploads, admin)

| Failure mode | Without kit (projected) | With kit (projected) |
|---|---|---|
| Mass assignment on profile/post update | likely: no checklist forces `$fillable`/allowlist review | scanner flags `php.mass-assignment` patterns; gaps remain for filtered-but-unvalidated input (known detector blind spot) |
| Unvalidated image upload (size/MIME, signed URLs) | likely: `SECURITY.md`-equivalent rarely exists freestyle | rule exists, but **no detector**; depends on reviewer discipline (known gap) |
| N+1 on post list and comment threads | likely at 100+ rows | rule exists, but **no detector** for loops; characterization tests only if the agent writes them |
| Missing rate limit on login/comments | likely | rule exists, but **no detector**; same discipline dependency |
| Breaking API change for the mobile reader | discovered by users | `API.md` + OpenAPI update is a Definition-of-Done item; enforced by review, not by script |

Honest summary of this phase: the kit converts "nobody thought about it" into "written rule, human-verified".
It does **not** convert it into "machine-verified" for auth, upload, N+1, or rate limits today.

### Month 4-6: maintenance, staff churn, agent-session churn

| Aspect | Without kit (projected) | With kit (projected) |
|---|---|---|
| New agent (or human) onboarding | reads code cold; asks the user what the intent was (measured pattern: no traceability artifact exists) | reads PRD + progress + index; resumes from `git log` (measured: the demo resumed across sessions from these files) |
| Regression from a "small fix" | full suite rarely run; breakage found in production (projected from freestyle habit: no phase-close gate) | layered verification: targeted per task, full suite at phase close (measured in the demo: 9/9 + verify 12 OK) |
| Stale docs | n/a (no docs to go stale) | **real cost**: PRD/index/progress must be updated on rename or they mislead; the kit has no expiry rule for its own artifacts (known gap) |
| Audit before a security review | manual, weeks (projected) | `scan.py` baseline in minutes + human confirmation per finding (measured: seconds on the demo; scaling to 500+ files is **unknown** — sampling rules are still undefined) |

## Cost model (projected, 6 months, 1-3 agents)

| Cost | Without kit | With kit |
|---|---|---|
| Planning docs | ~0 | PRD per feature (~1-3 h each), screens per new page, index updates per rename |
| Verification time | low upfront, spikes at incidents | steady: targeted per task, full suite per phase |
| Rework from escaped defects | high variance (auth, upload, N+1 are the classic blog incidents) | lower variance for covered rules; unchanged for detector blind spots |
| Onboarding per new contributor | days of code reading + questions | hours of PRD/index reading, **iff** the artifacts were maintained |

## Verdict

- The kit's payoff is proportional to **lifespan times contributors**, not to feature count.
  A blog built in a weekend: freestyle wins. The same blog operated for a year with
  rotating agents: the kit's traceability and gates are the cheaper option **on paper**.
- "On paper" is doing heavy lifting: three preconditions from the audit are still open —
  detectors for the risky rules, sampling rules for large repos, and evidence-backed
  approvals. Until those close, the large-scale advantage is projected, not demonstrated.
- Next honest step: build the blog's Phase 1 (auth + posts) both ways and measure
  escaped defects and onboarding time instead of projecting them.
