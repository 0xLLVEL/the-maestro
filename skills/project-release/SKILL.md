---
name: project-release
description: Prepares a project release according to docs/GIT.md and docs/CI-CD.md - determining the next SemVer version from Conventional Commits, assembling the CHANGELOG (Keep a Changelog), checking release readiness and risk (migration, env, dependency, breaking change), creating the release PR `chore(release): vX.Y.Z`, writing release notes, deploy and rollback plans, and the hotfix flow. Use this skill each time the user asks for a release, release, bump the version, determine the next version, write the changelog or release notes, prepare a deploy to production, create a tag, or hotfix, even without mentioning the word "skill" or "project-release". This skill does not create tags, merge, push to main, or deploy without explicit instructions. English triggers include prepare a release, bump the version, write the changelog, and cut a hotfix.
---

# Project Release

Preparing a release that is safe and traceable: the right version, an honest changelog, risks visible before deploy, and clear handoff steps. This skill is the final step of the `project-prd` -> `project-build` -> release flow.

The standards belong to the project. Read `AGENTS.md`, `docs/GIT.md` (Versioning, Tagging and releases, Release and hotfix flow), and `docs/CI-CD.md` first. If `references/` in this skill differs from the project docs, the project docs win.

## Principles

1. **Invoking this skill is not a command to create a tag.** `docs/GIT.md` forbids an agent from creating tags, releases, or bumping a version without explicit instructions. By default the skill stops at a **ready release PR** and hands the tag command over to the user. A tag is only created if the user explicitly asks for it (Step 4).
2. **The version comes from the commit.** The script proposes; the user decides. The first version and a breaking change on `0.y.z` are always asked about.
3. **No commits and no pushes to `main`.** Release changes go through a PR from the `chore/release-vX.Y.Z` branch. A tag is only created on a `main` commit after the release PR is merged.
4. **Tags are immutable.** Never moved, deleted, or reused. A faulty release is fixed with a new PATCH version.
5. **No deploy and no secrets.** The skill prepares a deploy and rollback plan, it does not execute them. Never write secrets, credentials, or user data into the changelog, release notes, or PR.
6. **Honest about what cannot be seen.** CI, staging, and production status are not visible from the repository. Never claim "CI is green" without evidence; ask the user to confirm or show a readable result.

## Workflow

### Step 0: Prerequisites
1. Read the standard documents above. Confirm the type of work: a **normal release**, a **pre-release** (`-rc.1`), a **hotfix**, or just a **version/changelog proposal**. If it is not stated, ask one question.
2. Ensure a Git repository, the latest `main` (`git fetch`), and a clean working tree; if it is dirty, ask the user to commit or stash. Determine the tag prefix (`v`, or `api-v`/`web-v` if released separately, `docs/GIT.md`).

### Step 1: Analysis
```bash
python scripts/release_prep.py --root . [--prefix v] [--pre rc.1]
```
The script only reads (it does not create tags or commits). Run it from the repository folder; the `scripts/` path is relative to this skill's folder. It outputs the last release, the version proposal with its reasoning, risk flags (migration, `.env.example`, lockfile, config, API contract, breaking change, non-conventional commits), and a CHANGELOG draft.
- Show the summary and the **proposed version**. Ask for approval of the final version.
- Non-conventional commits are not counted: mention them, and ask whether they need to be categorized manually.
- No `feat`/`fix` commits: state that a release may not be needed.

### Step 2: Readiness
Go through `references/release-checklist.md` and report the result for each item (ready, needs action, cannot be verified). The most important:
- `main` CI is green (user confirmation), and the dependency audit is clean or the findings are explained.
- Migration in the release: a safe strategy and a written **rollback plan** (`docs/DATABASE-PERFORMANCE.md`).
- New env variables are prepared; remember that a build-time public env variable is embedded at build time.
- API contract: a breaking change means MAJOR and a backend-first deploy order (`docs/CI-CD.md`).
- Documentation, OpenAPI, and the version number in the project files are in sync.

Blocking items are reported clearly; never proceed to a release PR before the user decides.

### Step 3: Release PR
1. Create a branch `chore/release-vX.Y.Z` from the latest `main`.
2. Update the changelog: `python scripts/release_prep.py --root . --version X.Y.Z --apply`. The script does not change files if `[Unreleased]` contains manual notes; move them manually in that case. Tidy up duplicated or unclear entries **without inventing** content; the changelog stays in English like the commits.
3. Sync the version in the project files that carry it, e.g. the dependency manifest (`<package manager> version X.Y.Z --no-git-tag-version`). Only fill in a `version` field where the manifest actually declares one; an injected or non-versioned manifest must be left alone.
4. Run the quality commands in `AGENTS.md`. Commit: `chore(release): vX.Y.Z`. Check `git diff --staged` beforehand.
5. Prepare the PR title `chore(release): vX.Y.Z` and description: the version and the reasoning, a changelog summary, risks, deploy and rollback plans. **Never merge.**

### Step 4: Handoff
Give the user: release notes (template in `references/release-checklist.md`), a deploy and rollback plan, and the tag command to be run after the PR is merged:
```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```
**Only if the user explicitly asks you to create a tag**, run first:
```bash
python scripts/release_prep.py --root . --check-tag vX.Y.Z
```
It checks: being on `main` and identical to `origin/main` after fetch, HEAD being the `chore(release): vX.Y.Z` commit from the already merged PR, a clean working tree, and the tag not existing yet (locally or remotely). A `[MISS]` means the tag is **not created**; explain the cause. Green CI cannot be checked by the script, so ask the user for confirmation. If everything is satisfied, create an annotated tag and push **only that tag**. A GitHub Release and a deploy are not created unless requested.

### Hotfix
Branch `hotfix/<id>-<slug>` from the release tag that carries the problem. The bug is fixed with a failing test first (the usual flow), a PR, a merge, then a PATCH release through Steps 1-4. The old tag is not touched.

### Rollback
Never delete or move a tag. A faulty release is handled with a new PATCH release or a `revert` PR, plus the database rollback plan that was already prepared before the deploy.

## Special situations

| Situation | Action |
|---|---|
| No tag yet | Propose `0.1.0` (early stage) or `1.0.0` (stable API) and let the user choose |
| A breaking change on `0.y.z` | Bump MINOR, then ask whether it is time for `1.0.0` |
| The user asks for a version different from the proposal | Follow it, record the reasoning in the PR, and remind them of the SemVer rules if it does not comply |
| The user asks for a push to `main`, to move/delete a tag, or for a force push | Refuse (`AGENTS.md` § 6 and `docs/GIT.md`); offer the PR path or a new PATCH version |
| The user asks for a deploy | Prepare a plan and checklist; do not run a deploy and do not touch production |
| Backend and frontend are released separately | Use a tag prefix per application and run the script with the respective `--prefix` |
| Release automation (release-please, semantic-release) | Only if releases are already frequent (YAGNI); propose it, never install it without approval |

## Format and language
The conversation with the user follows the user's own language; the release notes for stakeholders are in **English**; the CHANGELOG, commit messages, branch names, and PR titles in **English** (`docs/CODE-STANDARDS.md`). The final report uses the `AGENTS.md` § 4 format and ends with one question.

## Common mistakes
- Creating or pushing a tag just because the skill was invoked.
- Bumping a version without looking at the commits, or ignoring `BREAKING CHANGE`.
- Filling in a `version` field that the manifest does not declare, or forgetting to sync the files that do carry the version.
- Inventing changelog entries that are not in the commits.
- Skipping the rollback plan when the release includes a migration.
- Claiming green CI without evidence.
- Pushing directly to `main` for "just a changelog".
