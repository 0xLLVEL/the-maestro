---
name: project-build
description: Builds (implements) a feature or application from a PRD produced by the project-prd skill (docs/prd/<slug>.md), phase by phase, following the content of the PRD and the AGENTS.md and docs/ standards, with a fast flow. Use this skill, including for building a new application from scratch (bootstrap the stack in use), each time the user asks to build from the PRD, build/implement/implement the PRD, start coding from the PRD, work on PRD phase 1/2/3, continue the build, implement feature F-001, or says "the PRD is approved, start", even if the user does not mention the word "skill" or "project-build". If there is no PRD yet for a feature that is large, run project-prd first. English triggers include build from the PRD, implement the PRD, start building phase 1, and continue the build.
---

# Project Build

Turning an approved PRD into code that runs, is tested, and meets the standards: **the PRD decides what, `AGENTS.md` and `docs/` decide how.** The executor of `project-prd`, at the same level as `project-refactor` (the executor of `project-audit`).

## Principles
1. **The PRD is a contract.** Build the features, ACs, endpoints, screens, data, and tests that are written, with the same names and IDs. Nothing is cut, nothing is added (YAGNI). Optional features are not built unless requested.
2. **Standards win over approach.** The shape of the code follows `AGENTS.md` and `docs/`. The Absolute Prohibitions (`AGENTS.md` § 6) cannot be traded away by the PRD or by a request raised mid-build.
3. **Tests follow ACs.** Every AC becomes a test that can fail, written together with the implementation in the same task; **tests first** only for bug fixes and critical business rules (authorization, status, money, concurrency).
4. **Fast, tiered.** Per task: targeted verification. Full verification, review, and documents: **once at phase close**.
5. **No surprises.** Deviations are recorded (see Conflicts and deviations); findings outside the PRD are reported, not worked on.
6. **Honest.** Report what fails, is delayed, or cannot be verified. Never claim "passing" without running it.

## Pace rules
- **One initial call** (`prd_tasks.py start`), not a separate preflight, plan, and manual checks.
- **Read only what you need** (pace rules: `AGENTS.md` § 3): `AGENTS.md` + `docs/QUICK-RULES.md`; full documents only for the areas that are touched. The AC text is already in the `plan` output; do not open the PRD again and do not re-read files that have not changed.
- **Lightweight baseline in the background:** only lint/format/static analysis/typecheck on the stack touched by the phase, without running the test suite and without `build`.
- **Merge small tasks:** similar Effort S tasks (e.g. migration + model + factory) are done in one cycle; write many files in one step; chain commands with `&&`.
- **Parallel and conditional verification at phase close:** backend and frontend run at the same time; only the stack that changed; `build` only if the frontend changed; dependency audit only if the lockfile changed.
- **Time limit:** wrap long commands with `timeout 900`. A command that exceeds the limit or shows no progress: stop, report, ask for direction; do not run it again repeatedly.
- **Documents once:** progress, the PRD index, and design files are updated at phase close, not per task.

## Workflow

### Step 0: Start (one call)
Run it from the repository folder (the `scripts/` path is relative to this skill's folder):
```bash
python scripts/prd_tasks.py start docs/prd/<slug>.md --root . --phase <N>
```
It runs a readiness check and then prints the phase plan (tasks, ACs, endpoints, screens, tests, migration markers, open questions). `[MISS]` blocks and the plan is not printed: for a PRD error or a missing design file, go back to `project-prd`; never build on a broken PRD, and never invent design files to get through. `[?]` needs action:
- **PRD status `Draft`** and the user has not yet stated approval: ask; record the approval in the progress file. Without that, never start coding.
- **`Q-###`** that affects this phase: answer it first; the rest is recorded.
- **`_fill_` placeholder in `AGENTS.md`:** fill it from the detected facts (the dependency manifests, `project-audit/scripts/scan.py` if present), show it as a diff, confirm the ambiguous ones.
- **`git.branch` on `main`:** resolved in Step 1. **`project.scaffold`:** a new project, read `references/bootstrap.md` and do it as Phase 0.
- **The PRD version has changed** since the last session: review the new/changed IDs and update the plan.
- The progress file `docs/build/<slug>.md` already exists: a continuation session, continue from the last status (`plan` shows it).

Without a PRD for a small and clear change (one feature, no new screen): a mini-plan from `AGENTS.md`, show it, continue. A large feature without a PRD: run `project-prd`.

After that, show the **plan summary** (tasks, order, risks). If the user has already asked for that phase, **continue directly**; ask for approval only for high risk (a risky migration, a new dependency, auth/authorization/payment).

### Step 1: Branch and baseline
1. Working tree clean (if it is dirty, ask for a commit or a stash). Create a branch from the latest `main` according to Section 8 of the PRD (`feature/<slug>`). Never work on `main`.
2. Lightweight baseline, in the background, only the stack touched by the phase:
   ```bash
   (<formatter check> && <static analysis>) > <temp>/base-backend.log 2>&1 &
   (<lint> && <typecheck>) > <temp>/base-frontend.log 2>&1 &
   ```
   (Use a temp dir outside the project: `/tmp/` on Linux/macOS, `%TEMP%\` on Windows.)
   (adjust to the commands in `AGENTS.md`). Continue to Step 2 without waiting; read the log only if there is a failure. A command that cannot run: write "cannot be run: <reason>".
3. Conventions of the touched area: healthy, follow its pattern; messy, report and ask (`docs/REBUILD.md`); never restructure outside the PRD.

### Step 2: Progress notes
Create `docs/build/<slug>.md` from `references/progress-template.md` (concise: tasks, deviations, notes). This is the only place for progress; the PRD is not changed to record progress.

### Step 3: Cycle per task (or per group of small tasks)
Details per layer are in `references/build-playbook.md`; read only the relevant parts.
1. **Write the tests and the implementation** in the right layer (`docs/BACKEND.md`, `docs/FRONTEND.md`) with class, endpoint, column, and translation key names exactly as in the PRD. `@author`/`@ai` headers on created files and public API doc comments according to `docs/CODE-DOCUMENTATION.md`; descriptive test names without IDs.
2. **UI:** read `docs/design/screens/<slug>.md` and build its skeleton first: semantic HTML tags with no styling at all, exactly the structure the screen file specifies. Styling is a separate later step, only when the user asks for it; commit skeleton and styling separately. Reuse existing components before creating new ones.
3. **Targeted verification and commit in one call:** related tests + lint/format/typecheck only on the changed files (the formatter's changed-files mode, the linter on single files, the test runner's `--filter`), then `git add -A && git diff --staged --stat && git commit -m "<type(scope): ...>"`. The result must be the same as or better than the baseline.
4. **Ask the user before continuing** for auth/authorization/payment, a destructive migration, a new dependency, or a breaking API change (`AGENTS.md` § 4).

**Two failures on the same step, or unexpectedly changed behavior:** stop, report the cause, ask for direction. Never fiddle with it, skip it, or delete tests to make it green.

### Step 4: Phase close (once, in this order)
1. **Full verification, one call, parallel and conditional.** Determine what changed: `git diff --name-only <base>...HEAD`. Run the full suite + lint + static analysis for the stack that changed (backend and frontend at the same time); `build` only if the frontend changed; the dependency audit only if the lockfile changed. A failure in a test that does not touch the changed files: run that test alone on the original commit (`git worktree add <temp>/base <sha>`, link the dependency folders) to confirm it is an old failure; report it, never fix it. New failures are fixed before continuing.
2. **PRD index to code.** Create the skeleton with `python scripts/prd_tasks.py scaffold docs/prd/<slug>.md --root . --phase <N>` (only if `docs/prd-reference/<slug>.md` does not exist yet), fill in the Test file / Test name / Code columns for the entire phase at once (`references/prd-reference-template.md`), then:
   ```bash
   python scripts/prd_tasks.py verify docs/prd/<slug>.md --root . --phase <N> --ac-table
   ```
   `[MISS]` is resolved or explained; `[?]` is verified manually. No AC is left without a status.
3. **Update the documents once and commit:** `docs/build/<slug>.md`; screen files **only if** the PRD defines new screens; OpenAPI and `CHANGELOG.md` if relevant.
4. **Report** using the `AGENTS.md` § 4 format (`references/progress-template.md`) and prepare the title and description of the PR (what, why, how to test, risks, PRD ID). **Never merge or push to `main`, never create tags or releases.** End with one question: continue to the next phase? After all the phases are done and the PR is merged, offer `project-release`.

## Conflicts and deviations
Order of authority: **The Absolute Prohibitions of `AGENTS.md` § 6 > the `AGENTS.md` and `docs/` standards > PRD > playbook**.
- **The PRD violates the standards** (e.g. an endpoint without `/api/v1`, business logic in the HTTP layer): follow the standards with the smallest possible change, record `D-###` in the progress file, and **continue**. Ask (one question + recommendation) only if it cannot be reversed: database schema, public API contract, data deletion.
- **The PRD is ambiguous or the ACs contradict each other:** one specific question referring to the ID in question; never guess.
- **Findings outside the PRD:** record them in the "Notes" section of the progress file; never work on them.
- **The PRD changes mid-build:** review the new/changed IDs, update the plan, record the version in the progress file.

## Common mistakes
- Starting to code before the PRD is approved or before `check_prd.py` is clean.
- Adding features outside the PRD, or skipping an implicit Essential feature.
- Running the full suite, `build`, or an audit per task; updating progress/index per task.
- Running a full baseline (including the test suite and `build`) before starting.
- Renaming an endpoint, class, column, or translation key from the PRD without recording the deviation.
- Business logic in the controller, route, UI component, or a server endpoint.
- PRD IDs, PRD names, or TODO in comments, doc comments, test names; a made-up `@author`/`@ai`.
- UI before the design files exist, or hardcoded visual values.
- One giant commit that mixes migration, backend, and UI.
- Claiming "done" without full verification and `prd_tasks.py verify`.
