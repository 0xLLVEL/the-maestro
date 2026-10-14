# Calculator comparison: freestyle vs kit workflow

Same app (standard operations plus history, keyboard support, divide-by-zero handling)
built twice in plain HTML and vanilla JavaScript: `examples/calculator-nokit` (one pass,
no guide) vs `examples/calculator` (PRD, screen skeleton, logic plus tests, skeleton UI,
styling on request, PRD-code index).

Time figures are rough retrospective estimates from a single run, not stopwatch
measurements; they include chat roundtrips. The hard, countable proxies are commits,
files, and roundtrips.

## File structure

Without kit — everything in one file:

```text
examples/calculator-nokit/
  index.html   # markup + inline <style> + inline <script> (80 lines)
```

With kit — one concern per file:

```text
examples/calculator/
  calculator.js          # pure logic, no DOM (125 lines)
  app.js                 # DOM wiring only (83 lines)
  index.html             # unstyled skeleton markup (44 lines)
  styles.css             # styling, separate commit (123 lines)
  lang/en.json           # display strings (9 lines)
  tests/calculator.test.js
  docs/prd/calculator.md # approved PRD (80 lines)
  docs/design/screens/calculator.md
  docs/build/calculator.md
  docs/prd-reference/calculator.md
```

## Code style

| Practice | Without kit | With kit |
|---|---|---|
| Separation | logic, DOM, and CSS mixed in one file | pure logic (`calculator.js`) vs DOM wiring (`app.js`) vs style (`styles.css`) |
| Styling | inline `<style>` and `style=` from the first commit | unstyled skeleton first (zero `class`/`style`, verified by grep), `styles.css` later on user request |
| Display text | hardcoded in markup | `lang/en.json` keys; a test fails if a key is missing |
| Naming | short ad-hoc names | descriptive names, English throughout |
| Magic values | inline literals | named constants |

## Comment style

| Practice | Without kit | With kit |
|---|---|---|
| File headers | none | `@author`/`@ai` header on every created file |
| Doc comments | none | one-sentence contract comments on public units |
| Dead comments | n/a | no TODOs, no commented-out code, no PRD references in code |

## Commit style

Without kit: 1 commit, informative message, but no trace of decisions.
With kit: 6 Conventional Commits, one logical change each (planning docs, approval record,
logic plus tests, skeleton UI, styling, PRD-code index), each verified with
`git diff --staged` before committing.

## Best practice and verification

| Practice | Without kit | With kit |
|---|---|---|
| Tests | 0 (opened once in a browser, manually) | 9/9 `node --test`; every AC mapped to a test in the index |
| Static checks | none | `check_prd.py` clean; `verify` 12 OK / 1 explained MISS (page heuristic misses root-level static pages) |
| Time (rough) | ~10 min, 0 roundtrips | ~1 hour, 3 roundtrips (questions, PRD approval, styling) |

## Prompts used (verbatim, Indonesian)

Kit version — user: *"test langsung di real world case pakai agents nya. buat saja
aplikasi kalkulator dari html dan javascript"*. Agent ran `project-prd` (one batched
question round) and `project-build` (phased, with approval gates). Further user
inputs: PRD answers, *"setujui, tapi buat di dalam folder example"*, *"coba kasih
desain"* (styling approval).

No-kit version — user: *"coba buat lagi aplikasi kalkulator tanpa menggunakan skills
maupun agents.md"*. Agent worked freestyle: no guide or skill files consulted, one pass.

## Verdict

For a throwaway calculator the freestyle version is rational: the kit's overhead (PRD,
screens, index, 6 commits) buys nothing the task needs. For code that must be kept,
the kit version answers "why does this exist" for every line and re-verifies itself
with one command.

## Limits

n = 1 task, one operator with a pro-kit bias, no replication. Times are estimates
(see top). Only vanilla HTML/JS was tested.
