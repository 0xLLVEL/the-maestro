---
name: project-refactor
description: Apply the AGENTS.md and docs/ standards to a project based on an audit report (docs/audit/audit-*.md), gradually and safely. Use this skill whenever the user asks for a refactor, tidy up the code, fix audit findings, apply an audit plan, bring the project in line with the standards, start phase 0/1/2/3, rebuild a messy module, clean up spaghetti code, or says "continue fixing" after an audit, even if the user never says the word "skill". If there is no audit report yet for a broad refactor, run the project-audit skill first. English triggers include refactor the project, apply the audit plan, and fix audit findings.
---

# Project Refactor

Carrying out the compliance plan from the audit report: changing code to match the standards in `AGENTS.md` and `docs/`, **without changing the application's behavior** except where a plan item asks for it, in small steps that always end green.

This skill is the executor of `project-audit`. The standards still belong to the project: read `AGENTS.md` and `docs/` first, and if `references/` in this skill differs from the project documents, the project documents win.

## Principles

1. **Audit first, refactor after.** The source of the plan is the latest audit report in `docs/audit/`. For a broad refactor without a report, run `project-audit` first. For a small and clear refactor (one module, one problem), just draw up your own mini-plan based on `AGENTS.md` and show it to the user.
2. **Behavior stays.** Refactoring changes structure, not function. Lock behavior with tests before changing anything. Tests must not be changed or skipped to turn the result green.
3. **Small and gradual.** One item or module per step, one logical change per commit, and every step ends in a green state. Giant changes cannot be reviewed and cannot be reverted safely.
4. **Approval.** The plan must be approved before it is carried out. High-risk items (database schema, breaking API, data deletion, public API rename) need explicit confirmation per item.
5. **No surprises.** Work only on items that are in the plan. New findings are recorded in the "found during refactor" list, not done in secret.
6. **Safe.** Do not touch `.env` or secrets, do not run destructive commands, do not touch production or a non-local database, and do not push to `main`, force push, or create tags.
7. **Honest.** Report what failed, what was deferred, and what could not be verified.

## Workflow

### Step 0: Prerequisites and safety
1. Read `AGENTS.md`, `docs/`, and the latest audit report. Check whether the report is still relevant: compare the audited commit against `HEAD` (`git diff --stat <commit-audit>..HEAD`). If much has changed, rescan with `project-audit` before continuing.
2. Make sure the working tree is clean (`git status`). If it is dirty, ask the user to commit or stash first. Do not overwrite unsaved work.
3. **Baseline:** run the quality commands from `AGENTS.md` (format, static analysis, test, lint, typecheck, build) and note their results. This shows what was already red before you start, so old failures are not blamed on the refactor. Commands that cannot run are noted as "cannot be run: <reason>".
4. Save the initial scan if it does not exist yet: `python <folder-project-audit>/scripts/scan.py <root> --json /tmp/scan-before.json`.
5. Create a branch from the latest `main`: `refactor/<area>` or `chore/<topic>` (English, kebab-case). Do not work on `main`.

### Step 1: Pick and approve items
Take items from the audit plan (Phase 0 through 3) or the phase/items requested by the user. Show the list for this session along with the order and risk, then ask for approval if it is not yet explicit. The safe order:
1. **Critical** (secrets, vulnerabilities): see "Special cases".
2. **Foundation:** tooling, CI, tests for critical flows. This is the safety net for the next steps.
3. **Structure:** layer separation, per module.
4. **Refinement:** doc comments, performance.

Limit one session to a batch you can finish and verify fully. Better a little but complete.

### Step 2: Per-item cycle
Repeat for each item:
1. **Understand.** Read the code and all of its usages (`grep` across the whole repo) before changing or deleting it.
2. **Lock behavior.** Make sure there are tests protecting that area. If not, write a *characterization test* first: a test that describes the current behavior as it is (including its quirks), and a separate commit `test(scope): add characterization tests for ...`. For frontend, test the behavior visible to the user.
3. **Change.** Follow the relevant playbook in `references/playbooks.md`.
4. **Targeted verification.** Run the related tests and lint/static analysis/typecheck on the changed files in a single call; the result must be the same as or better than the baseline. The full suite and `build` are run once at the end of the batch (and immediately only for risky items).
5. **Commit.** Conventional Commits in English (`refactor(scope): ...`), and update the related documents in the same commit: doc comments, API documentation, `CHANGELOG.md` where relevant. Audit finding IDs and PRD IDs are not written into code or comments; in the files touched, remove old PRD/TODO references and move whatever is still useful to the PRD-code index (docs/CODE-DOCUMENTATION.md).
6. **Record** the item status in the progress report (written once at the end of the batch).

**If verification fails twice, or behavior changes unexpectedly:** stop, revert that step (only your own local commits), report the cause, and ask for direction. Do not fiddle with tests to make them green.

### Step 3: Special cases
- **Leaked secret or tracked `.env`.** Do not work on it yourself before the user **revokes and rotates** the secret with the service provider, because removing it from the code does not clean the Git history. After confirmation: move it to env/config, `git rm --cached .env`, update `.gitignore` and `.env.example`. Rewriting Git history (`filter-repo`) only on explicit request.
- **Database schema.** Follow the safe migration rules in `docs/DATABASE-PERFORMANCE.md` (additive first, *expand/contract*, never change a migration that has already run). Confirm per item.
- **Breaking API.** Publish a new version or mark it according to docs/API.md, and sync the frontend in the same step.
- **Public API rename** (route, JSON key, table/column name) is a breaking change and needs confirmation. An internal rename (variable, private method, internal class) may be done right away.
- **Rebuilding a messy module.** Follow `docs/REBUILD.md`. Build the new version side by side, move users to the new version, and delete the old code only after its replacement passes tests.
- **Bulk formatting.** One separate commit `style: apply formatter` with no other changes, so the review diff stays clean. Record its hash in `.git-blame-ignore-revs` if the project uses it.
- **`_fill_` placeholder in `AGENTS.md`.** Fill it from detected facts and show it as a diff. Confirm ambiguous values (e.g. architecture).
- **Documents that do not match reality.** Propose fixing the document. Do not change the project to match an incorrect document.
- **Design.** If the PRD defines a new screen, its specification file goes in `docs/design/screens/<slug>.md` (read by `prd_tasks.py verify`). Brand values (color, font, logo) that the user has already chosen are written into the screen file; the agent does not invent them.
- **Doc comments.** On old code, complete the units you touch. Bulk completion only if it is a plan item (per module).

### Step 4: Phase close
1. Rescan and compare:
   ```bash
   python <folder-project-audit>/scripts/scan.py <root> --json /tmp/scan-after.json
   python scripts/compare_scans.py /tmp/scan-before.json /tmp/scan-after.json
   ```
   A drop in the number of findings is an indicator of progress, not proof of correctness. Check the **"Regressions" (findings increased)** section printed by `scripts/compare_scans.py`: rules whose count rose must be explained or fixed.
2. Re-run all quality commands and compare them with the baseline.
3. Update the "Adjustment results" section (section 9) in the audit report, or write `docs/audit/refactor-YYYY-MM-DD.md`, with a before/after table and the remaining findings.
4. Report to the user: what is done, what is deferred along with the reason, new findings, and next steps. Prepare a PR title and description (Conventional Commits, containing what, why, how to test, risk). **Do not merge or push to `main`.**

## Progress report format
```
## Refactor: <area/phase>
Branch: <name> | Baseline: <brief>

| Item | Status | Commit | Verification |
|---|---|---|---|
| AF-001 ... | done / deferred / failed | <hash> | test, lint, build: pass |

### Found during the refactor (not yet done)
### Deferred, with the reason
### Scan results (before -> after)
### Next steps
```

## Language and format
Conversation with the user follows the user's own language; the progress report file and everything else written to files is in **English**. Identifiers, comments, doc comments, branch names, and commit messages in English (docs/CODE-STANDARDS.md).

## Common mistakes
- Changing structure and behavior at the same time, so a regression cannot be traced.
- Refactoring without protective tests, or changing tests to make them pass.
- One giant commit that mixes formatting, renames, and logic changes.
- Working on items outside the plan, or starting before the plan is approved.
- Rotating or cleaning up secrets yourself, when it is the user who must revoke them with the service provider.
- Reporting "done" before re-running verification and the scan.
