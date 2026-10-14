# Git Commit, Branching, and Versioning Standards

> Part of the agent guide. Summary and core rules are in [`AGENTS.md`](../AGENTS.md).

## Commit format (Conventional Commits 1.0.0)
```
<type>(<scope>): <subject>

<body>

<footer>
```

| Type | Used for | Version impact |
|---|---|---|
| `feat` | New feature for users | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `refactor` | Code structure change without changing behavior | - |
| `test` | Adding/fixing tests | - |
| `docs` | Documentation only | - |
| `style` | Format/whitespace (not a logic change) | - |
| `build` | Build system, dependencies (package manager, lockfile) | - |
| `ci` | CI/CD configuration | - |
| `chore` | Other routine work that does not change production code | - |
| `revert` | Reverting a previous commit | depends on what is reverted |

Writing rules:
- **Scope** is optional but recommended, lowercase, referring to a module/area: `auth`, `order`, `api`, `ui`, `db`, `deps`.
- **Subject**: imperative sentence, lowercase, no trailing period, maximum 72 characters (ideally ≤ 50). Example: `add`, `fix`, `remove` - not `added` or `adding`.
- **Body** (optional): explain **why** and the context of the change, not *what* (the diff already explains it). Separate it from the subject with one blank line, wrap at ± 72 characters per line.
- **Footer**: issue references (`Closes #123`, `Refs #45`) and `BREAKING CHANGE: <explanation>`.
- **Breaking change** is marked with `!` after the type/scope (`feat(api)!: ...`) and/or a `BREAKING CHANGE:` footer.
- Commit messages, branch names, and PR titles are **always in English** (see docs/CODE-STANDARDS.md).

Example:
```
feat(order): add cancel order endpoint

Customers could not cancel pending orders without contacting support.
Cancellation is only allowed while the order status is "pending".

Closes #128
```
```
fix(auth): prevent token refresh loop on expired session
```
```
refactor(user)!: rename `name` column to `full_name`

BREAKING CHANGE: API responses now return `full_name` instead of `name`.
```

## Commit principles
- **One logical change per PR**: do not mix features, refactoring, and formatting in a single PR. Because the default merge strategy is *squash* (see the Pull Request section), commits on the branch may be granular to make review easier; what is stored in `main` is one commit per PR. If rebase merge is used, every commit on the branch must be atomic and tidy.
- Every commit that lands in `main` must be **buildable and pass tests** (the repository is always in a working state).
- Review before committing: run `git status` and `git diff --staged`. **Do not** blindly `git add .`; stage only the relevant files.
- Do not commit: secrets, `.env`, credentials, dependency directories, build output, logs, or local IDE files. Make sure `.gitignore` is complete and `.env.example` is maintained.
- Do not commit commented-out code, debug output calls (`dump`, `print`, `console.log`, `debugger`, and the like), or "WIP"/"fix again" commits to a shared branch.
- Tidy up local commits (`git commit --amend`, `git rebase -i`) **before** pushing. After pushing to a shared branch, do not rewrite history. For agents this is optional, because the default merge is *squash* (see "Specific rules for agents").

## Branching (GitHub Flow / trunk-based)
- `main` is always **stable and release-ready**; it is protected (*branch protection*): PR, review, and green CI are required. No direct commits to `main`.
- Working branches are **short-lived**, created from the latest `main`, with the format `<type>/<issue-id>-<short-slug>`:
  `feature/128-cancel-order`, `fix/131-token-refresh`, `refactor/user-module`, `docs/update-readme`, `chore/upgrade-dependency`, `hotfix/140-payment-crash`.
- Sync with `main` periodically (`git rebase origin/main` for personal branches) so conflicts stay small and history stays linear.
- Delete the branch after merging.
- If a force push is needed on a **personal** branch, use `--force-with-lease`, **not** `--force`. Never force push to `main` or a shared branch.

## Pull Request
- The PR title follows the Conventional Commits format (because it will become the commit message on *squash merge*).
- Minimal description: **what** changed, **why**, **how to test**, screenshots for UI changes, and a link to the issue.
- Keep PRs small and focused. Large PRs are split (see docs/REBUILD.md: module by module).
- Merge requirements: green CI (test, lint, static analysis) and at least one approving review.
- Default merge strategy: **squash merge** (one PR = one clean commit on `main`, with the PR title as the commit message). Use **rebase merge** only if the commits on the branch are already atomic and tidy. Avoid unnecessary merge commits.

## Versioning (Semantic Versioning 2.0.0)
Format `MAJOR.MINOR.PATCH` (e.g. `2.4.1`):
- **MAJOR**: incompatible changes (breaking change to API/contract/schema).
- **MINOR**: new backward-compatible features.
- **PATCH**: backward-compatible bug fixes.
- Pre-releases: `1.3.0-rc.1`, `1.3.0-beta.2`. Versions `0.y.z` are only for the early development stage before the API is stable.
- The version is determined from the commits since the last release: a `BREAKING CHANGE` means MAJOR; a `feat` means MINOR; otherwise PATCH.
- One version for the whole project (backend + frontend in a single repository). If released separately, use tag prefixes (`api-v1.2.0`, `web-v1.2.0`).

## Tagging and releases
- **Annotated** tags with a `v` prefix on commits in `main`:
  ```bash
  git tag -a v1.2.0 -m "Release v1.2.0"
  git push origin v1.2.0
  ```
- Tags are **immutable**: do not move them, delete them, or reuse them. If a release is wrong, publish a new PATCH version.
- Maintain **`CHANGELOG.md`** in the [Keep a Changelog](https://keepachangelog.com) format (Added, Changed, Deprecated, Removed, Fixed, Security), derived from Conventional Commits. Every release records the date and version.
- Sync the version number in project files that carry it (e.g. `package.json`) with the tag. In ecosystems where the dependency manifest does not track a release version, the version follows the Git tag (do not fill in the `version` field of the manifest).
- Release and changelog automation (e.g. release-please, semantic-release) may be added **only if** releases are already frequent enough (YAGNI).

## Release and hotfix flow
1. Make sure `main` is green on CI.
2. Determine the next version based on the SemVer rules above.
3. Update `CHANGELOG.md` (and the version number if needed) via a `chore(release): vX.Y.Z` PR.
4. After merging, create the annotated tag `vX.Y.Z` and push it.
5. **Hotfix**: create a `hotfix/...` branch from the problematic release tag (or from `main`), fix it with tests, merge via PR, then release a new PATCH version.

## Specific rules for agents
- Agents may make commits on **working branches**, following the format and principles above. Because the default merge is squash, agents do not need to tidy up commits on the branch excessively; focus on a correct PR title.
- Agents **may not** push to `main`, force push, modify (amend/rebase) commits that have already been pushed, or delete other people's branches/tags.
- Agents **may not** create tags, releases, or bump versions without explicit instructions from the user.
- Before committing, agents run the verification commands (AGENTS.md § Project Context) and check `git diff --staged`.
- If a change covers several topics, agents split it into several atomic commits.
