#!/usr/bin/env python3
"""Builds a throwaway Git repo for project-release evals.

Usage: python make_fixture.py <target-dir> [--merged-release] [--with-remote]

Default: tag v1.2.0, then feat/fix/docs/chore commits on `main` (a migration, a
.env.example change and a lockfile change are included so the risk flags fire).
--merged-release : adds the commit `chore(release): v1.3.0` as if the release PR was merged.
--with-remote    : adds a bare repository as `origin` (<target-dir>-origin.git) and pushes main + v1.2.0.
"""
import subprocess
import sys
from pathlib import Path


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def commit(d, msg, files):
    for n, c in files.items():
        p = Path(d, n)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(c, encoding="utf-8")
    sh(d, "git", "add", "-A")
    sh(d, "git", "commit", "-qm", msg)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = Path(sys.argv[1]).resolve()
    d.mkdir(parents=True, exist_ok=True)
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "eval@example.com")
    sh(d, "git", "config", "user.name", "eval")
    commit(d, "chore: initial commit", {
        "AGENTS.md": "# Agent Guide (fixture)\n\nRead docs/GIT.md. Agents must not create tags or releases without explicit instructions, and must not push to main.\n",
        "package.json": '{"name": "acme/shop", "version": "1.2.0", "dependencies": {"express": "^4.19.0"}}',
        "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-08-01\n\n### Added\n\n- **order:** list orders (aaaaaaa)\n\n[Unreleased]: https://github.com/acme/shop/compare/v1.2.0...HEAD\n[1.2.0]: https://github.com/acme/shop/releases/tag/v1.2.0\n",
    })
    sh(d, "git", "tag", "-a", "v1.2.0", "-m", "Release v1.2.0")
    commit(d, "feat(order): add cancel order endpoint (#41)", {"db/migrations/2026_09_01_000000_add_cancelled_at.js": "// migration"})
    commit(d, "fix(auth): refresh token on 401 (#42)", {"src/auth.js": "// fix"})
    commit(d, "fix(security): scope orders to owner (#43)", {"src/policy.js": "// policy"})
    commit(d, "docs: update readme", {"README.md": "# Shop"})
    commit(d, "chore: bump deps", {".env.example": "APP_NAME=Shop\nNEXT_PUBLIC_API_URL=\n", "composer.lock": "{}"})
    if "--merged-release" in sys.argv:
        commit(d, "chore(release): v1.3.0", {"CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## [1.3.0] - 2026-10-08\n\n### Added\n\n- **order:** add cancel order endpoint (#41)\n"})
    if "--with-remote" in sys.argv:
        remote = Path(str(d) + "-origin.git")
        sh(d.parent, "git", "init", "-q", "--bare", str(remote))
        sh(d, "git", "remote", "add", "origin", str(remote))
        sh(d, "git", "push", "-q", "origin", "main", "v1.2.0")
    print(f"Fixture ready at {d}")


if __name__ == "__main__":
    main()
