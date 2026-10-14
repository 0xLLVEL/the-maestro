# the-maestro

A small, opinionated kit that keeps AI coding agents disciplined: one **guide** (`AGENTS.md` plus twelve short standards
documents) and five **skills** that turn it into a workflow: write a PRD, build from it, audit the result, refactor what the
audit found, and prepare a release.

It does not generate code by itself. It tells an agent *how* to work in your repository, and ships scripts that check the
agent's work (and your repository) against the same rules.

## What is inside

```
template/            copy into your project
  AGENTS.md          entry point for any agent: principles, workflow, pace rules, definition of done
  docs/              standards: code, documentation, backend, frontend, API, database, security, testing, Git, CI/CD, rebuild
skills/              the five skills (each is a folder with a SKILL.md)
  project-prd/       write a short, executable PRD (no code)
  project-build/     build from an approved PRD, phase by phase, on its own branch
  project-audit/     read-only audit of a project against the standards, then a fix plan
  project-refactor/  apply an approved audit plan in small, tested commits
  project-release/   prepare version, changelog, and release PR (never tags or deploys on its own)
tools/check_kit.py   keeps this repository consistent (see Development)
```

The standards belong to **your project**, not to the skills: every skill reads `AGENTS.md` and `docs/` first.

## Quick start

1. **Copy the guide into your project.** Copy `template/AGENTS.md` and `template/docs/` to the root of your repository.
2. **Install the skills.** Copy the folders in `skills/` to your agent's skills directory (for example `.claude/skills/` in your
   project, or `~/.claude/skills/` for Claude Code).
3. **Start the agent.** The "Project Context" section of `AGENTS.md` is blank on purpose (`_fill_`). On the first run the agent
   detects your stack from the manifests in your repository, fills it in, and asks you one question only if something cannot
   be detected.

Typical flow: *"write a PRD for ..."* then *"build it"* then *"audit the project"* then *"apply the audit plan"* then *"prepare a release"*.

## Evidence: with kit vs without kit

The same apps built twice by the same agent, once freestyle and once through the full workflow:

| App | Without kit | With kit |
|---|---|---|
| Calculator (HTML+JS) | 1 file, 0 tests, inline style | PRD + 9/9 tests + skeleton-first UI, styled after approval |
| Blog Phase 1 (Node+SQLite: auth, posts, pagination) | 1 file; stored XSS and unverified sessions on read | 14/14 tests, 9/9 ACs connected, 0 known vulnerabilities, full traceability |

Details with measured numbers: [calculator comparison](examples/calculator-comparison.md),
[blog comparison](examples/blog-comparison.md) (raw numbers, code style, security, scanner evidence),
[read-only audit of both blog builds](docs/audit/audit-2026-10-14.md).

Honest limits: one task each, one operator, no independent replication. The kit side also
shows its warts (a 169-line function the scanner caught, a HIGH finding that turned out to
be a false positive). Read the limits sections before quoting any number.

## When to use (and when not to)

**Use the full workflow** (PRD → build → audit → refactor → release) when the code must
outlive the session: maintained products, security-sensitive areas (auth, payments, PII),
multi-agent or multi-human work, or anything you will need to explain in six months.

**Use only the Small flow** (`AGENTS.md` §3: read, change, test, commit) for trivial changes
in a codebase you already own. Do not write a PRD for a three-line fix.

**Skip the kit** for throwaway scripts, one-off experiments, and learning spikes. If the
spike survives, rebuild it through the workflow instead of growing it.

**Recommended way to adopt it:**

1. Copy the guide and install the skills (Quick start above).
2. On an existing project, run `project-audit` first for a baseline; fix through
   `project-refactor` before adding features.
3. Write tests alongside code, keep UI skeleton-first, commit small with Conventional Commits.
4. Maintain the PRD index and progress files on rename — stale traceability misleads more
   than none. Run the scanner before and after (`compare_scans.py`) to prove progress.

## With vs without: concrete examples

Taken from the two blog builds above (same scope, same stack). Left: freestyle. Right: kit.

### The prompts

Same job, same stack — the only deliberate difference is whether the agent follows the kit:

```text
Calculator, with kit:    "Test directly in a real-world case using your agents.
                          Just build a calculator app from HTML and JavaScript."
Calculator, without kit: "Now build the calculator again without using skills
                          or AGENTS.md."
Blog, both versions:     "Now try building an online blog app using Node.js and
                          SQLite. Make 2 versions, with kit and without kit."
```

Everything below is what each prompt produced.

**Code** — mixed concerns vs one layer per file:

```js
// without: routing + SQL + HTML in one handler
const user = me(req);                                   // who is me?
const rows = db.prepare(`SELECT ... WHERE status='published' ...`).all(...);
h += `<article><h2>${p.title}</h2>...`;                 // unescaped: stored XSS
```

```js
// with: thin route calls a service, view escapes
const user = sessionUser(db, parseCookies(req.headers.cookie).sid);
sendJson(res, 200, { data: listPosts(db, user, page, perPage) });
// views.js: ${escapeHtml(p.title)}
```

**Comment** — none vs contract plus header:

```js
// without: no header, one TODO left behind
// TODO: verify cookie signature
```

```js
// with: every created file carries this, every public unit a one-liner
/**
 * Resolves a signed cookie value to the public user row, or null.
 *
 * @author  0xLLVEL
 * @ai      Muse Spark 1.3 (OpenCode)
 */
```

**Commit** — one dump vs one logical change each:

```text
// without (1 commit total)
docs(examples): add no-kit blog contrast demo
```

```text
// with (8 commits, e.g.)
feat(examples): add blog auth with roles and tests
feat(examples): add blog posts, routes, and HTTP tests
style(examples): design light theme for blog
```

**API** — ad hoc strings vs uniform shape:

```json
// without
{ "error": "forbidden" }
```

```json
// with
{ "error": { "code": "FORBIDDEN", "message": "Forbidden." } }
```

**Design** — styled immediately vs skeleton first:

```html
<!-- without: inline style in the first commit -->
<style>body{font-family:Arial;background:#f5f5f5...}</style>
<button onclick="eq()" style="grid-column: span 2">=</button>
```

```html
<!-- with: skeleton (no class/style/CSS), styling in a later commit -->
<main>
  <h1 data-i18n="calculator.title"></h1>
  <div id="display" role="status"></div>
</main>
```

**Tests** — none vs every requirement connected:

```text
// without: opened once in a browser, manually
// with: 14/14 node --test; docs/prd-reference maps AC-F001-1..AC-F003-2
//        and T-001/T-002 to test names and code symbols
```

## The audit scanner

`skills/project-audit/scripts/scan.py` is a read-only, standard-library-only scanner. It reports **heuristics**, not verdicts:
every finding must be confirmed by reading the code.

```bash
python skills/project-audit/scripts/scan.py <project-root> --json audit-scan.json
```

| Option | Meaning |
|---|---|
| `--max-file-lines N`, `--max-func-lines N` | size thresholds (defaults 300 and 50) |
| `--max-per-rule N` | how many examples to list per rule |
| `--style-checks` | also report opinionated `design.slop-*` style heuristics (off by default) |
| `--lang-pack id,es,...` | which non-English language(s) to flag in code and comments: `id`, `es`, `pt`, `fr`, `de`, a JSON file, or `none` (default `id`) |

It recognises **PHP, Node/TypeScript** (React, Vue, Svelte, Angular, Next, Nuxt, ...), **Python, Go, Ruby, Java/Kotlin, Rust,
and .NET**, including several in one repository. Per stack it checks the tooling that belongs there (formatter, linter, static
analysis, lockfile, runtime pin, `.gitignore`, tests, CI) and applies the detector rules that make sense for that language.
Language packs are small JSON files in `skills/project-audit/scripts/langpacks/`; adding a language needs no code.

## Development

```bash
python tools/check_kit.py            # consistency checks
python tools/check_kit.py --tests    # ... plus every self-test of the skills
```

`check_kit.py` verifies, among other things, that the template contains no stack-specific API names, that every rule id cited in
the documentation really exists in the scanner, that duplicated files are identical, and that `VERSION`, `CHANGELOG.md`, the
template's version marker, and the skills' front matter agree. CI runs it on Linux, Windows, and macOS (Python 3.9 and 3.12).
Everything uses the Python standard library only.

## Status and limitations

- The scripts were developed and tested on Linux with Python 3.12; CI covers the other platforms and versions.
- The scanner has been exercised on generated projects for each stack and on a corpus of real source files, not yet on large
  real-world repositories, so expect false positives from the newer rules and report them.
- The skills are instructions for an agent. Their scripts are tested; the agent's behaviour when following them is not
  covered by automated tests (the `evals/` folders describe behavioural checks that need an agent to run them).
- The Spanish, Portuguese, French, and German language packs are starting points; add or remove words for your team.

## Versioning

[Semantic Versioning](https://semver.org); see [CHANGELOG.md](CHANGELOG.md). The first line of `template/AGENTS.md` carries the
kit version, so a project can tell which version of the guide it copied.

## License

Not specified yet. Until a `LICENSE` file is added, all rights are reserved by the author.
