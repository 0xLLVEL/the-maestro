#!/usr/bin/env python3
"""Self-test for release_prep.py. Builds throwaway Git repos and asserts the results.

Run:  python selftest.py        (exit code 0 = all passed)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "release_prep.py"
FAILS = []


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def commit(cwd, msg, files=None):
    for name, content in (files or {}).items():
        p = Path(cwd, name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    if not files:
        Path(cwd, "f.txt").write_text(msg + "\n", encoding="utf-8")
    sh(cwd, "git", "add", "-A")
    sh(cwd, "git", "commit", "-qm", msg)


def repo():
    d = tempfile.mkdtemp()
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "t@t.t")
    sh(d, "git", "config", "user.name", "t")
    return d


def run(d, *args):
    out = Path(d, "out.json")
    r = subprocess.run([sys.executable, str(SCRIPT), "--root", d, "--json", str(out), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r, (json.loads(out.read_text()) if out.exists() else None)


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))
    if not cond:
        FAILS.append(name)


# 1. minor bump + changelog sections + risk flags
d = repo()
commit(d, "chore: init", {"package.json": '{"name":"acme/shop","version":"1.2.0"}'})
sh(d, "git", "tag", "-a", "v1.2.0", "-m", "Release v1.2.0")
commit(d, "feat(order): add cancel endpoint", {"database/migrations/2026_01_01_x.php": "<?php"})
commit(d, "fix(auth): refresh token on 401")
commit(d, "fix(security): block IDOR on orders")
commit(d, "docs: update readme")
commit(d, "do something odd")
commit(d, "chore: bump", {".env.example": "A=1\n", "composer.lock": "{}"})
r, j = run(d)
check("exit 0", r.returncode == 0, r.stderr)
check("minor bump 1.3.0", j and j["proposed_version"] == "1.3.0", j and j["proposed_version"])
cl = j["changelog"] if j else ""
check("Added has feat", "### Added" in cl and "**order:** add cancel endpoint" in cl)
check("Fixed has fix", "### Fixed" in cl and "refresh token on 401" in cl)
check("Security section from fix(security)", "### Security" in cl and "block IDOR" in cl)
check("docs excluded", "update readme" not in cl)
kinds = {f["kind"] for f in j["flags"]} if j else set()
check("flags migration/env/dependency/non-conventional", {"migration", "env", "dependency", "non-conventional"} <= kinds, kinds)
check("package-version mismatch not flagged when equal", "package-version" not in kinds)

# 2. breaking on >=1.0 -> major; footer note
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v2.4.1", "-m", "x")
commit(d, "feat(api)!: rename status field")
r, j = run(d)
check("major bump 3.0.0", j and j["proposed_version"] == "3.0.0", j and j["proposed_version"])
check("breaking listed", j and "**BREAKING:**" in j["changelog"])

# 3. breaking on 0.y.z -> minor
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v0.3.2", "-m", "x")
commit(d, "fix: a", None)
Path(d, "g.txt").write_text("g")
sh(d, "git", "add", "-A")
sh(d, "git", "commit", "-qm", "feat: b", "-m", "BREAKING CHANGE: removed old param")
r, j = run(d)
check("0.y.z breaking -> minor 0.4.0", j and j["proposed_version"] == "0.4.0", j and j["proposed_version"])
check("breaking footer note in changelog", j and "removed old param" in j["changelog"])

# 4. patch only
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v1.0.0", "-m", "x")
commit(d, "fix: typo")
r, j = run(d)
check("patch 1.0.1", j and j["proposed_version"] == "1.0.1", j and j["proposed_version"])

# 5. nothing releasable
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v1.0.0", "-m", "x")
commit(d, "docs: x")
r, j = run(d)
check("no releasable commits warns", j and any("may not be needed" in x for x in j["reasons"]), j and j["reasons"])

# 6. first release (no tag)
d = repo()
commit(d, "feat: first")
r, j = run(d)
check("first release proposes 0.1.0 and asks confirmation", j and j["proposed_version"] == "0.1.0" and any("must be confirmed by the user" in x for x in j["reasons"]))

# 7. pre-release promote + --pre
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v1.3.0-rc.1", "-m", "x")
commit(d, "fix: y")
r, j = run(d)
check("pre-release tag promotes to 1.3.0", j and j["proposed_version"] == "1.3.0", j and j["proposed_version"])
r, j = run(d, "--pre", "rc.2")
check("--pre appends suffix", j and j["proposed_version"].endswith("-rc.2"), j and j["proposed_version"])

# 8. --apply: creates / inserts / respects manual Unreleased / updates links; never tags or commits
d = repo()
commit(d, "chore: init", {"CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- x\n\n[Unreleased]: https://github.com/o/r/compare/v1.0.0...HEAD\n[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0\n"})
sh(d, "git", "tag", "-a", "v1.0.0", "-m", "x")
commit(d, "feat: shiny")
before = subprocess.run(["git", "tag"], cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
r, j = run(d, "--apply")
text = Path(d, "CHANGELOG.md").read_text()
check("apply inserts section under Unreleased", "## [1.1.0]" in text and text.index("## [Unreleased]") < text.index("## [1.1.0]") < text.index("## [1.0.0]"))
check("apply updates compare links", "[Unreleased]: https://github.com/o/r/compare/v1.1.0...HEAD" in text and "[1.1.0]: https://github.com/o/r/compare/v1.0.0...v1.1.0" in text, text[-300:])
check("apply is idempotent", "already contains version" in subprocess.run([sys.executable, str(SCRIPT), "--root", d, "--apply", "--version", "1.1.0"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout)
check("no tag created", subprocess.run(["git", "tag"], cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout == before)
d = repo()
commit(d, "chore: init", {"CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n- manual note\n"})
sh(d, "git", "tag", "-a", "v1.0.0", "-m", "x")
commit(d, "fix: z")
r, j = run(d, "--apply")
check("manual Unreleased content blocks apply", "manual" in r.stdout and "1.0.1" not in Path(d, "CHANGELOG.md").read_text())

# 8b. changelog omits hash when PR number present; manual override label
d = repo()
commit(d, "chore: init")
sh(d, "git", "tag", "-a", "v1.0.0", "-m", "x")
commit(d, "feat(order): add cancel (#41)")
commit(d, "fix: no pr number")
r, j = run(d)
check("entry with PR number has no hash", j and "add cancel (#41)\n" in j["changelog"] and "(#41) (" not in j["changelog"], j and j["changelog"])
check("entry without PR number keeps hash", j and "no pr number (" in j["changelog"])
out = subprocess.run([sys.executable, str(SCRIPT), "--root", d, "--version", "2.0.0"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
check("override shows proposed and used versions", "Proposed version: v1.1.0" in out and "Version used    : v2.0.0" in out, out)

# 8c. --check-tag
def checktag(d, tag):
    r = subprocess.run([sys.executable, str(SCRIPT), "--root", d, "--check-tag", tag], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout

base = repo()
commit(base, "chore: init")
sh(base, "git", "tag", "-a", "v1.2.0", "-m", "x")
remote = tempfile.mkdtemp()
sh(remote, "git", "init", "-q", "--bare")
sh(base, "git", "remote", "add", "origin", remote)
commit(base, "feat: a (#1)")
sh(base, "git", "push", "-q", "origin", "main", "v1.2.0")
code, out = checktag(base, "v1.3.0")
check("check-tag blocks when HEAD is not the release commit", code == 1 and "[MISS] release-commit" in out, out)
commit(base, "chore(release): v1.3.0")
code, out = checktag(base, "v1.3.0")
check("check-tag blocks when release commit is not pushed (out of sync)", code == 1 and "[MISS] sync" in out, out)
sh(base, "git", "push", "-q", "origin", "main")
code, out = checktag(base, "v1.3.0")
check("check-tag passes on synced main with merged release commit", code == 0 and "preconditions met" in out, out)
sh(base, "git", "tag", "-a", "v1.3.0", "-m", "x")
code, out = checktag(base, "v1.3.0")
check("check-tag blocks when tag already exists (immutable)", code == 1 and "[MISS] tag-local" in out, out)
sh(base, "git", "tag", "-d", "v1.3.0")
sh(base, "git", "checkout", "-qb", "chore/release-v1.3.0")
code, out = checktag(base, "v1.3.0")
check("check-tag blocks on non-main branch", code == 1 and "[MISS] branch" in out, out)
sh(base, "git", "checkout", "-q", "main")
Path(base, "dirty.txt").write_text("x")
code, out = checktag(base, "v1.3.0")
check("check-tag blocks on dirty tree", code == 1 and "[MISS] tree" in out, out)

# 9. not a git repo
r = subprocess.run([sys.executable, str(SCRIPT), "--root", tempfile.mkdtemp()], capture_output=True, text=True, encoding="utf-8", errors="replace")
check("non-git dir exits non-zero", r.returncode != 0)

# 10. risk flags understand the conventions of other stacks
sys.path.insert(0, str(HERE))
import release_prep  # noqa: E402

check("migration folders: Rails, Django, Alembic, Flyway, Prisma, EF",
      all(release_prep.MIGRATION_RE.search(f) for f in (
          "db/migrate/2024_add.rb", "app/migrations/0002_x.py", "alembic/versions/ab12.py",
          "src/main/resources/db/migration/V2__x.sql", "prisma/migrations/1_init/migration.sql", "Data/Migrations/Init.cs"))
      and not release_prep.MIGRATION_RE.search("src/orders.py"), "")
check("lockfiles map to the audit command of their ecosystem",
      release_prep.LOCK_AUDIT["Gemfile.lock"] == "bundle audit" and release_prep.LOCK_AUDIT["uv.lock"] == "pip-audit"
      and release_prep.LOCK_AUDIT["go.sum"].startswith("govulncheck") and release_prep.LOCK_AUDIT["Cargo.lock"] == "cargo audit", "")
ver = Path(tempfile.mkdtemp())
sh(ver, "git", "init", "-q", "-b", "main")
sh(ver, "git", "config", "user.name", "t")
sh(ver, "git", "config", "user.email", "t@t.t")
Path(ver, "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.9.0"\n')
Path(ver, "Cargo.toml").write_text('[package]\nname = "x"\nversion = "1.2.0"\n')
sh(ver, "git", "add", "-A")
sh(ver, "git", "commit", "-qm", "chore: init")
flags = {f[0] for f in release_prep.risk_flags(str(ver), None, [], (1, 2, 0))}
check("manifest version drift is flagged for pyproject.toml but not when Cargo.toml matches the tag",
      "pyproject-version" in flags and "cargo-version" not in flags, str(flags))

print(f"\n{'ALL PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
