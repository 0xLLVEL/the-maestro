---
name: project-audit
description: Audit the entire project against the standards in AGENTS.md and docs/, then draw up a plan to bring it into compliance. Use this skill whenever the user asks for an "audit", "audit project", "full audit", a review of the whole codebase, a health check, a compliance check against AGENTS.md, a check of whether the code is messy or spaghetti, a tech debt assessment, "bring the project in line with the standards", or an examination of security, architecture, code quality, testing, Git, and CI at once, even if the user never says the word "skill". Also use it for a partial audit (e.g. "audit security only"). English triggers include audit the project, codebase review, compliance check against AGENTS.md, and tech debt assessment.
---

# Project Audit

Checking the whole project against the standards written in `AGENTS.md` and `docs/`, reporting findings with evidence, then drawing up (and, once approved, carrying out) a plan to bring the project into line with those standards.

**The standards belong to the project, not to this skill.** Always read `AGENTS.md` and `docs/` first. If the content of the documents differs from `references/` in this skill, the project documents win.

## Principles

1. **Evidence-based.** Every finding has a location (`file:line`) and a standard that is violated (docs file + section). Do not report something you cannot point at, and do not make things up.
2. **Scripts are heuristics.** `scripts/scan.py` is fast but can be wrong (false positives). Open the location and read the code before marking a finding as **Confirmed**. Findings that have not been verified are written as **Needs verification**. Discard false positives.
3. **Read-only by default.** An audit does not change source code. The only file written is the report in `docs/audit/`. Fixes are only carried out after the user approves (Step 7).
4. **Safe.** Do not read or print the contents of `.env` or secret values; report only their locations. Do not run destructive commands (dropping or wiping a database, resetting migrations, `git reset --hard`). Run tests only if it is clear they use the testing environment; if in doubt, do not run them and note the reason. Do not install dependencies without permission.
5. **Honest about limits.** Things that cannot be audited from the repository (branch protection, production configuration, human review) are recorded as "cannot be audited", not judged.

## Workflow

### Step 1: Load the standards
- Read `AGENTS.md`, then all files in `docs/` that are relevant (the document map is at the top of `AGENTS.md`).
- If `AGENTS.md` does not exist, stop, say so clearly, and offer to create it first. An audit without standards has no reference.
- Note: `_fill_` placeholders that are not yet filled in, project commands, heuristic thresholds (file/function size, the definition of "big change", coverage), language rules, and the rebuild policy.

### Step 2: Reconnaissance and baseline
1. Run the scanner (path relative to this skill folder):
   ```bash
   python scripts/scan.py <root-project> --json /tmp/audit-scan.json
   ```
   Thresholds can be adjusted with `--max-file-lines` and `--max-func-lines` to match the numbers in `AGENTS.md`. Style heuristics (`design.slop-*`) are off by default because nothing in `docs/` defines them; add `--style-checks` only if the project's own design guidance asks for them. The language checks (`lang.*`) flag words that are not English, using a language pack: pass `--lang-pack` with the language the team writes instead of English (`id`, `es`, `pt`, `fr`, `de`, the path of your own JSON file, several separated by commas, or `none`; the default is `id`). A pack is a small JSON file in `scripts/langpacks/`, so adding a language needs no code. The scanner is stack-neutral: it recognises PHP, Node/TypeScript (React, Vue, Svelte, Angular, Next, Nuxt, ...), Python, Go, Ruby, Java/Kotlin, Rust, and .NET projects, including several in one repository, and applies the tooling checks and detector rules that belong to each (`scripts/stacks.py` and `scripts/detectors.py`; `python scripts/selftest.py` verifies them). For an ecosystem it does not know, fall back to reading the code and run the project's own commands. The output contains detected facts (stack, package manager, database, architecture), checks for the existence of tooling/documents, a Git summary, metrics, and heuristic findings.
2. Run the quality commands from `AGENTS.md` (the Project Context section) one at a time: format, static analysis, test, lint, typecheck, build, dependency audit. Note the results briefly (pass/fail and the number of issues). If a command cannot run because of the environment (no database, dependencies not installed, no network), write **"cannot be run: <reason>"**. Do not guess its result.
3. On large repos (more than about 500 code files), use sampling as described in `references/audit-dimensions.md`.

### Step 3: Review by dimension
Open `references/audit-dimensions.md`. There are 12 dimensions (agent documentation, architecture, code principles, standards and language, doc comments, API, database and performance, security, testing, Git, CI and tooling, frontend and accessibility). Its checklists live in the `docs/` standard files referenced by each dimension (not repeated here); the reference file only holds how to look for evidence, the relevant scanner rules, and severity guidance.

Read sample code, do not rely on script output alone. Good samples: the largest files, the most frequently changed files (Git churn), and one example from each layer (entry point/handler, service or use case, data layer, request validation, response mapping, authorization, migration, UI component, hook, API client, test). Verify every script finding by opening its location.

For a **partial audit** (e.g. "audit security only"), do Steps 1-2 as needed, then only the requested dimension, with the same evidence rules.

### Step 4: Convention verdict
Give a verdict per area (backend, frontend, API, database, testing, tooling and process) using the **indicator table in `docs/REBUILD.md`** as the only criteria (Healthy, Partly healthy, Messy), together with the strategies in that document's "Step 2 - Decision" section. Do not invent your own criteria. Write 1-2 sentences of evidence per verdict. Do not suggest a rebuild without "messy" evidence.

### Step 5: Report
Write the report to `docs/audit/audit-YYYY-MM-DD.md` using `references/report-template.md`. In chat, give a **brief summary**: verdict per area, number of findings per severity, the top 3-5 findings, and the report file location. Do not paste the whole report into chat.

Severity scale:

| Severity | Meaning | Example |
|---|---|---|
| **Critical** | Real risk right now; handle immediately | Committed secret, tracked `.env`, exploitable SQL injection |
| **High** | Serious bug/risk or a major standard violation | Unvalidated input binding (mass assignment), endpoint without authorization, token in browser storage, secret in a build-time public env variable, no test for critical flows |
| **Medium** | Degrades quality and adds tech debt | Business logic in the entry point, file/function too large, `any`, hardcoded color |
| **Low** | Cleanliness and consistency | `console.log`, missing doc comment, TODO without an issue |
| **Info** | Note, not a violation | Stack facts, things that are already good |

### Step 6: Compliance plan
Draw up a phased plan at the end of the report:
- **Phase 0, critical:** leaked secrets, vulnerabilities, tracked `.env`. Do it immediately.
- **Phase 1, foundation:** tooling (formatter, static analysis, linter, `.editorconfig`), CI, `AGENTS.md` placeholder, language and format standards, basic tests for critical flows.
- **Phase 2, structure:** fix layer separation, per module, according to the convention verdict.
- **Phase 3, refinement:** doc comments, performance, documentation.

Each item contains: what, where, which standard is violated, estimated effort (S/M/L), risk, and dependencies. End with **one** question: which phase to start with?

### Step 7: Compliance work (only after approval)
Hand the execution over to the **`project-refactor`** skill. That skill applies the audit report's plan gradually and safely: a dedicated branch, characterization tests, verification, and before/after comparison.

If `project-refactor` is not available, tell the user and work only by following `AGENTS.md` and `docs/REBUILD.md`: a dedicated branch, one module per step, tests first, Conventional commits, and do not change the project in secret. Two rules from the audit side still apply:
- **Leaked secrets** are not fixed by you. Ask the user to revoke and rotate the secret with the service provider, because removing it from the code does not clean the Git history.
- **Compliance work goes both ways.** If the standards in the documents do not match reality (e.g. a command that does not exist in the dependency manifest), propose fixing the document, not changing the project to match an incorrect document.

## Response format
- Chat follows the user's own language; the report file in `docs/audit/` and identifiers, file names, and commit messages in **English** (per `docs/CODE-STANDARDS.md`).
- Concise and structured. Do not copy the contents of the standards into the report; just refer to the file and its section.

## Common mistakes
- Reporting heuristic numbers as facts, or reporting findings without opening the code.
- Judging by personal preference instead of the standards in `AGENTS.md`.
- Touching installed dependencies or build output (the scanner already excludes them).
- Pasting secret values into the report or chat.
- Working on fixes before the user approves the plan, or doing them yourself instead of through `project-refactor`.
- Suggesting a total rewrite without evidence that the conventions are indeed messy.
