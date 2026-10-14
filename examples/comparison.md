# With-kit vs without-kit: calculator comparison

Same app (standard operations, history, keyboard, divide-by-zero handling) built twice
by the same agent: once freestyle (`examples/calculator-nokit`, one file, no guide),
once through the full kit workflow (`examples/calculator`: PRD, screen skeleton,
logic plus tests, skeleton UI, styling on request, PRD-code index).

## Raw numbers

| Metric | Without kit | With kit |
|---|---|---|
| Source files | 1 (`index.html`) | 5 (`calculator.js`, `app.js`, `index.html`, `styles.css`, `lang/en.json`) |
| Source lines (code, no docs) | ~80 | ~340 |
| Planning/traceability docs | 0 | PRD, screen file, progress file, PRD-code index |
| Commits | 1 | 7 (planning, logic, skeleton, styling, index, release of docs) |
| Automated tests | 0 (syntax checked only) | 9 (`node --test`, every AC connected) |
| Time, wall clock | ~10 minutes | ~1 hour |
| Styling | immediate, inline | skeleton first, styled after user request, separate commit |

## Scanner evidence (`scan.py` on both)

| Check | Without kit | With kit |
|---|---|---|
| Files scanned | 0 (plain `.html` is outside the scanner's extensions) | 4 files, 424 lines |
| Guide presence (`agents.md`, placeholders) | FAIL (no guide) | PASS |
| Doc comments | n/a | 100% of 13 units |
| Heuristic findings | none (nothing scanned) | 1 MEDIUM: `design.hardcoded-color` (14 hex values, no design tokens) |

## Dimension matrix

| Dimension | Small / throwaway | Large / long-lived |
|---|---|---|
| Speed to first working UI | freestyle wins by ~6x | tie: scaffolding cost amortizes over dozens of phases |
| Defect verifiability | freestyle: behavior unverified | kit wins: every AC has a failing-capable test |
| Traceability (why is this code here) | freestyle: none | kit wins: PRD, progress, index |
| Consistency across sessions | irrelevant (one session) | kit wins only if its standards are enforced; otherwise drift equals freestyle |
| Process overhead | freestyle: zero | kit: PRD, screens, index, progress must be maintained or they rot into misinformation |
| Auditability by script | neither (scanner misses plain HTML; styled kit code flags color tokens) | kit wins on stacks the scanner knows; blind spots (auth, rate-limit, CORS) apply equally |

## Verdict

- Small, short-lived code: freestyle is rational. The kit's overhead buys nothing the task needs.
- Large, long-lived code: the kit's design targets the right problems (context loss, drift,
  unverified claims), but the claim is conditional on closing its enforcement gaps:
  detectors for auth/rate-limit/CORS/validation, sampling rules for large repos,
  evidence-backed approvals, and scanner coverage for plain frontends.
- The kit must also define when its own artifacts expire: a stale PRD index is worse than none.

## Limits of this comparison

- n = 1 task, one agent (the kit's author-operator), no independent replication.
- Both demos are tiny; scaling behavior is projected, not measured.
- The kit's own README states the scanner has not been exercised on large real-world
  repositories; neither has this comparison.
