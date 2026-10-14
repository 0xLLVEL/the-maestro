#!/usr/bin/env python3
"""Release preparation analyzer for Git projects that use Conventional Commits.

Usage:
    python release_prep.py [--root .] [--prefix v] [--since TAG] [--version X.Y.Z]
                           [--pre rc.1] [--apply] [--json out.json]
    python release_prep.py --root . --check-tag vX.Y.Z

What it does (read-only unless --apply):
  * finds the last release tag and the commits since it
  * proposes the next SemVer version from the commit types (docs/GIT.md rules)
  * drafts a Keep a Changelog section
  * flags release risks: migrations, .env.example, dependency lockfiles, config, routes,
    API contract files, breaking commits, non-conventional commits
  * with --apply: inserts the section into CHANGELOG.md (never touches tags, never commits)

--check-tag vX.Y.Z checks the preconditions for creating that tag (on main, in sync with origin,
HEAD is the merged `chore(release): vX.Y.Z` commit, clean tree, tag absent locally and on the
remote). It only reports; it never creates the tag.

Exit code 0 on success, 1 when --check-tag finds a blocker, 2 on usage/git errors.
It never creates tags, commits or pushes.
Standard library only.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SECTIONS = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
TYPE_TO_SECTION = {"feat": "Added", "fix": "Fixed", "perf": "Changed", "revert": "Changed"}
IGNORED_TYPES = {"docs", "chore", "refactor", "test", "tests", "ci", "style", "build"}
SUBJECT_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
# migration folders of the common stacks: Laravel/Rails/Django/Alembic/Flyway/Prisma/EF/Drizzle
MIGRATION_RE = re.compile(r"(^|/)(?:database/migrations|db/migrate|db/migration|migrations?|Migrations|alembic/versions|prisma/migrations|drizzle)/")
# lockfile -> the dependency audit that belongs to it
LOCK_AUDIT = {
    "composer.lock": "composer audit", "package-lock.json": "npm audit", "yarn.lock": "yarn audit", "pnpm-lock.yaml": "pnpm audit",
    "bun.lockb": "bun audit", "poetry.lock": "pip-audit", "uv.lock": "pip-audit", "Pipfile.lock": "pip-audit", "pdm.lock": "pip-audit",
    "Gemfile.lock": "bundle audit", "go.sum": "govulncheck ./...", "Cargo.lock": "cargo audit",
    "gradle.lockfile": "an OWASP dependency check", "packages.lock.json": "dotnet list package --vulnerable",
}
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def git(root, *args, check=True):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        sys.exit(f"Failed to run git: {e}")
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip() if r.returncode == 0 else ""


def last_tag(root, prefix):
    tag = git(root, "describe", "--tags", "--abbrev=0", "--match", f"{prefix}[0-9]*", check=False)
    return tag or None


def parse_version(tag, prefix):
    m = SEMVER_RE.match(tag[len(prefix):]) if tag and tag.startswith(prefix) else None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)) if m else None


def read_commits(root, since):
    rng = f"{since}..HEAD" if since else "HEAD"
    raw = git(root, "log", "--no-merges", "--format=%h%x1f%s%x1f%b%x1e", rng, check=False)
    commits = []
    for rec in raw.split("\x1e"):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        h, subj, body = (rec.split("\x1f") + ["", ""])[:3]
        m = SUBJECT_RE.match(subj.strip())
        breaking_note = re.search(r"^BREAKING[ -]CHANGE:\s*(.+)$", body, re.M)
        commits.append({
            "hash": h.strip(), "subject": subj.strip(),
            "type": m.group("type").lower() if m else None,
            "scope": m.group("scope") if m else None,
            "desc": m.group("desc").strip() if m else subj.strip(),
            "breaking": bool(m and m.group("bang")) or bool(breaking_note),
            "breaking_note": breaking_note.group(1).strip() if breaking_note else None,
        })
    return commits


def propose_version(cur, commits, pre):
    reasons = []
    brk = [c for c in commits if c["breaking"]]
    feats = [c for c in commits if c["type"] == "feat"]
    fixes = [c for c in commits if c["type"] in {"fix", "perf", "revert"}]
    if cur is None:
        return "0.1.0", ["No release tag yet: the first version must be confirmed by the user (0.1.0 for an early stage, 1.0.0 once the API is stable)."], "first"
    major, minor, patch, prerelease = cur
    if prerelease and not pre:
        reasons.append(f"The last tag is a pre-release ({major}.{minor}.{patch}-{prerelease}); the proposal promotes it to a stable version.")
        return f"{major}.{minor}.{patch}", reasons, "promote"
    if brk:
        if major == 0:
            level = "minor"
            reasons.append("There is a breaking change on a 0.y.z version: MINOR is raised. Ask the user whether it is time for 1.0.0.")
        else:
            level = "major"
            reasons.append(f"{len(brk)} breaking change commit -> MAJOR.")
    elif feats:
        level = "minor"
        reasons.append(f"{len(feats)} feat commit -> MINOR.")
    elif fixes:
        level = "patch"
        reasons.append(f"{len(fixes)} fix/perf/revert commit -> PATCH.")
    else:
        reasons.append("No feat/fix/perf/breaking commit since the last release: a release may not be needed.")
        level = "patch"
    if level == "major":
        v = (major + 1, 0, 0)
    elif level == "minor":
        v = (major, minor + 1, 0)
    else:
        v = (major, minor, patch + 1)
    ver = f"{v[0]}.{v[1]}.{v[2]}" + (f"-{pre}" if pre else "")
    return ver, reasons, level


def build_changelog(version, commits, today):
    buckets = {s: [] for s in SECTIONS}
    ignored = 0
    for c in commits:
        scope = f"**{c['scope']}:** " if c["scope"] else ""
        ref = "" if re.search(r"\(#\d+\)\s*$", c["desc"]) else f" ({c['hash']})"
        line = f"- {scope}{c['desc']}{ref}"
        if c["breaking"]:
            note = f" {c['breaking_note']}" if c["breaking_note"] else ""
            buckets["Changed"].append(f"- **BREAKING:** {scope}{c['desc']}{note}{ref}")
        elif c["type"] == "fix" and (c["scope"] or "").lower() == "security":
            buckets["Security"].append(f"- {c['desc']}{ref}")
        elif c["type"] in TYPE_TO_SECTION:
            buckets[TYPE_TO_SECTION[c["type"]]].append(line)
        else:
            ignored += 1
    out = [f"## [{version}] - {today}", ""]
    for s in SECTIONS:
        if buckets[s]:
            out += [f"### {s}", ""] + buckets[s] + [""]
    return "\n".join(out).rstrip() + "\n", ignored


def risk_flags(root, since, commits, last_version):
    flags = []
    if since:
        names = git(root, "diff", "--name-status", f"{since}..HEAD", check=False).splitlines()
    else:
        names = []
    files = [(l.split("\t")[0], l.split("\t")[-1]) for l in names if "\t" in l]

    def hit(pred):
        return [f for _, f in files if pred(f)]

    mig = hit(lambda f: MIGRATION_RE.search(f) is not None)
    if mig:
        flags.append(("migration", f"{len(mig)} migration file changed or new: prepare a rollback plan and deploy with a safe strategy (docs/DATABASE-PERFORMANCE.md).", mig[:5]))
    env = hit(lambda f: f.endswith(".env.example"))
    if env:
        flags.append(("env", "`.env.example` changed: make sure the new variables are set in staging and production before deploying.", env))
    lock = hit(lambda f: f.split("/")[-1] in LOCK_AUDIT)
    if lock:
        audits = sorted({LOCK_AUDIT[f.split("/")[-1]] for f in lock})
        flags.append(("dependency", "Dependencies changed: run " + ", ".join(f"`{a}`" for a in audits) + " before the release.", lock))
    cfg = hit(lambda f: f.startswith("config/") or "/config/" in f)
    if cfg:
        flags.append(("config", "Config files changed: check the impact on the environment.", cfg[:5]))
    api = hit(lambda f: re.search(r"openapi|swagger|routes/api", f, re.I) is not None)
    if api:
        flags.append(("api", "API contract/route changed: if there is a breaking change, deploy the backward-compatible backend first (docs/CI-CD.md).", api[:5]))
    brk = [c for c in commits if c["breaking"]]
    if brk:
        flags.append(("breaking", f"{len(brk)} breaking change: needs migration notes in the release notes and a clear deploy order.", [c["subject"] for c in brk][:5]))
    bad = [c for c in commits if c["type"] is None]
    if bad:
        flags.append(("non-conventional", f"{len(bad)} commit does not follow Conventional Commits (excluded from the version proposal and the automatic changelog).", [c["subject"] for c in bad][:5]))
    cj = Path(root, "composer.json")
    if cj.exists():
        try:
            if "version" in json.loads(cj.read_text(encoding="utf-8")):
                flags.append(("composer-version", "the dependency manifest declares a `version` field; for Composer, remove it, because the version follows the Git tag (docs/GIT.md).", ["composer.json"]))
        except ValueError:
            pass
    pj = Path(root, "package.json")
    if pj.exists() and last_version:
        try:
            pv = json.loads(pj.read_text(encoding="utf-8")).get("version")
            lv = f"{last_version[0]}.{last_version[1]}.{last_version[2]}"
            if pv and pv != lv:
                flags.append(("package-version", f"package.json version {pv} does not match the last tag {lv}; synchronize it at release time.", ["package.json"]))
        except ValueError:
            pass
    lv = f"{last_version[0]}.{last_version[1]}.{last_version[2]}" if last_version else None
    for name, key in (("pyproject.toml", "pyproject-version"), ("Cargo.toml", "cargo-version")):
        mp = Path(root, name)
        if mp.exists() and lv:
            m = re.search(r'(?ms)^\[(?:project|package|tool\.poetry)\][^\[]*?^version\s*=\s*"([^"]+)"', mp.read_text(encoding="utf-8", errors="ignore"))
            if m and m.group(1) != lv:
                flags.append((key, f"{name} version {m.group(1)} does not match the last tag {lv}; synchronize it at release time.", [name]))
    return flags


def apply_changelog(root, version, section, prefix, tag_prev, today):
    path = Path(root, "CHANGELOG.md")
    if not path.exists():
        header = "# Changelog\n\nAll notable changes to this project are documented in this file.\nThe format follows [Keep a Changelog](https://keepachangelog.com) and this project uses [Semantic Versioning](https://semver.org).\n\n## [Unreleased]\n\n"
        path.write_text(header + section, encoding="utf-8")
        return "CHANGELOG.md created."
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^## \[{re.escape(version)}\]", text, re.M):
        return f"CHANGELOG.md already contains version {version}; not changed."
    m = re.search(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]:\s|\Z)", text, re.M | re.S)
    if m and m.group(1).strip():
        return "The [Unreleased] section holds manual notes: move them to the new version by hand, CHANGELOG.md is not changed."
    if m:
        pos = m.end()
        new = text[:pos].rstrip("\n") + "\n\n" + section + "\n" + text[pos:].lstrip("\n")
    else:
        h = re.search(r"^## \[", text, re.M)
        pos = h.start() if h else len(text)
        new = text[:pos].rstrip("\n") + "\n\n## [Unreleased]\n\n" + section + "\n" + text[pos:]
    msg = "The new version section was inserted into CHANGELOG.md."
    link = re.search(r"^\[Unreleased\]:\s*(\S+?)/compare/\S+\.\.\.\S+\s*$", new, re.M)
    if link and tag_prev:
        base = link.group(1)
        new = new.replace(link.group(0), f"[Unreleased]: {base}/compare/{prefix}{version}...HEAD\n[{version}]: {base}/compare/{tag_prev}...{prefix}{version}")
        msg += " Comparison links updated."
    path.write_text(new.rstrip("\n") + "\n", encoding="utf-8")
    return msg


def _default_branch(root):
    """The repository's default branch: origin/HEAD when known, else a local main/master/trunk."""
    ref = git(root, "symbolic-ref", "refs/remotes/origin/HEAD", check=False)
    if ref.startswith("refs/remotes/origin/"):
        return ref.rsplit("/", 1)[-1]
    for b in ("main", "master", "trunk"):
        if git(root, "show-ref", "--verify", f"refs/heads/{b}", check=False):
            return b
    return "main"


def check_tag(root, tag):
    """Report whether creating `tag` is safe. Returns exit code (1 when blocked)."""
    m = re.match(r"^(.*?)(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$", tag)
    if not m:
        sys.exit(f"'{tag}' is not a SemVer tag (e.g. v1.3.0).")
    version = m.group(2)
    rows = []

    def add(status, name, detail):
        rows.append((status, name, detail))

    base = _default_branch(root)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    add("OK" if branch == base else "MISS", "branch", f"branch '{branch}'" + ("" if branch == base else f": the tag is created on {base} after the release PR is merged"))
    add("OK" if not git(root, "status", "--porcelain", check=False) else "MISS", "tree", "clean working tree" if not git(root, "status", "--porcelain", check=False) else "there are uncommitted changes")
    remote = git(root, "remote", check=False).split()
    if "origin" in remote:
        fetched = subprocess.run(["git", "fetch", "-q", "origin"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace").returncode == 0
        local, upstream = git(root, "rev-parse", "HEAD", check=False), git(root, "rev-parse", f"origin/{base}", check=False)
        if not fetched:
            add("?", "sync", "git fetch failed: synchronization with origin cannot be verified")
        else:
            add("OK" if local and local == upstream else "MISS", "sync", f"HEAD matches origin/{base}" if local == upstream else f"HEAD differs from origin/{base}: pull or push is not in sync")
        remote_tag = git(root, "ls-remote", "--tags", "origin", f"refs/tags/{tag}", check=False)
        add("OK" if not remote_tag else "MISS", "tag-remote", "the tag does not exist on the remote yet" if not remote_tag else "the tag ALREADY exists on the remote (immutable tag: use a new version)")
    else:
        add("?", "sync", "remote 'origin' does not exist: synchronization and the presence of the tag on the remote cannot be verified")
    add("OK" if not git(root, "tag", "-l", tag, check=False) else "MISS", "tag-local", "the tag does not exist locally yet" if not git(root, "tag", "-l", tag, check=False) else "the tag ALREADY exists locally (immutable tag)")
    subject = git(root, "log", "-1", "--format=%s", check=False)
    expected = f"chore(release): {tag}"
    ok = subject.strip().lower().startswith(expected.lower().rstrip())
    add("OK" if ok else "MISS", "release-commit", f"HEAD: '{subject}'" + ("" if ok else f" (expected '{expected}' from the merged release PR)"))
    print(f"Preconditions for tag {tag}:")
    for s, n, d in rows:
        print(f"  [{s:4}] {n}: {d}")
    print("\nGreen CI cannot be checked from the repository: ask the user for confirmation.")
    blocked = any(s == "MISS" for s, _, _ in rows)
    print("Result: " + ("BLOCKED, the tag was not created." if blocked else "preconditions met (get CI confirmation from the user, then create an annotated tag and push only the tag)."))
    return 1 if blocked else 0


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--prefix", default="v", help="tag prefix, e.g. v or api-v")
    ap.add_argument("--since", help="override the base tag")
    ap.add_argument("--version", help="force the version instead of the proposal (X.Y.Z)")
    ap.add_argument("--pre", help="pre-release suffix, e.g. rc.1")
    ap.add_argument("--apply", action="store_true", help="insert the changelog section into CHANGELOG.md")
    ap.add_argument("--json")
    ap.add_argument("--check-tag", metavar="TAG", help="check preconditions for creating TAG (does not create it)")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if git(root, "rev-parse", "--is-inside-work-tree", check=False) != "true":
        sys.exit("Not a Git repository.")
    if a.check_tag:
        sys.exit(check_tag(root, a.check_tag))
    since = a.since or last_tag(root, a.prefix)
    cur = parse_version(since, a.prefix) if since else None
    if since and cur is None:
        sys.exit(f"Tag '{since}' is not SemVer with prefix '{a.prefix}'.")
    commits = read_commits(root, since)
    proposed, reasons, level = propose_version(cur, commits, a.pre)
    version = a.version or proposed
    if a.version and not SEMVER_RE.match(a.version):
        sys.exit("--version must be in SemVer X.Y.Z[-pre] format.")
    if a.version and a.version != proposed:
        reasons.append(f"Version set manually ({a.version}); automatic proposal: {proposed}.")
    today = date.today().isoformat()
    section, ignored = build_changelog(version, commits, today)
    flags = risk_flags(root, since, commits, cur)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False)

    print(f"Last release    : {since or '(none yet)'}")
    print(f"Active branch   : {branch}")
    print(f"Commits since   : {len(commits)} ({ignored} excluded from the changelog: docs/chore/refactor/test/ci/style/build)")
    print(f"Proposed version: {a.prefix}{proposed}  [{level}]")
    if version != proposed:
        print(f"Version used    : {a.prefix}{version}  (set manually)")
    for r in reasons:
        print(f"  - {r}")
    print("\nRisks and items to check:")
    if flags:
        for kind, msg, items in flags:
            print(f"  [{kind}] {msg}")
            for i in items:
                print(f"      - {i}")
    else:
        print("  (no risk flags detected)")
    print("\nCHANGELOG draft:\n")
    print(section)
    if a.apply:
        print(apply_changelog(root, version, section, a.prefix, since, today))
    if a.json:
        Path(a.json).write_text(json.dumps({
            "last_tag": since, "branch": branch, "commits": len(commits), "level": level,
            "proposed_version": proposed, "version": version, "reasons": reasons,
            "flags": [{"kind": k, "message": m, "items": i} for k, m, i in flags],
            "changelog": section}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
