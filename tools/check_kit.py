#!/usr/bin/env python3
"""Checks the internal consistency of this kit (placeholders, language leftovers, line endings, copies).

Run from the kit root: python tools/check_kit.py [--tests]
  --tests   also run every selftest.py of the kit
Exit code 0 when everything is consistent, 1 otherwise. Standard library only.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_EXTS = {".md", ".py", ".json"}
SKIP_DIRS = {"__pycache__", ".git"}

# Files that must stay byte-identical because each skill ships its own copy.
IDENTICAL_COPIES = [
    ("skills/project-build/evals/files/example-prd.md", "skills/project-prd/references/example-prd.md"),
]

# Leftovers that previously drifted away from the canonical English terms.
FORBIDDEN = ["_isi_", "Esensial", "Opsional", "Catatan", "Nama Fitur"]

# The core guide must stay stack-neutral: framework-specific API names belong in examples, not in rules.
STACK_LEAKS = ["lockForUpdate", "chunkById", "Octane", "Scramble", "fillable", "artisan", "Eloquent", "migrate:fresh"]
NEUTRAL_FILES = ("template/",)

# Documents that cite scanner rule ids / check ids in backticks: every cited id must really exist.
ID_DOCS = ["skills/project-audit/SKILL.md", "skills/project-audit/references/audit-dimensions.md"]
ID_RE = re.compile(r"`((?:[a-z]+)(?:\.[a-z0-9*-]+)+)`")


def text_files():
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix in TEXT_EXTS and not (set(path.parts) & SKIP_DIRS):
            yield path


def known_ids():
    """Rule ids (RULES) and project-check ids of the scanner, read from the code itself."""
    sys.path.insert(0, str(ROOT / "skills" / "project-audit" / "scripts"))
    import scan
    import stacks
    with tempfile.TemporaryDirectory() as tmp:
        checks = {c["id"] for c in stacks.project_checks(pathlib.Path(tmp), stacks.detect_facts(pathlib.Path(tmp)))}
        checks |= {c["id"] for c in stacks.project_checks(pathlib.Path(tmp), {"stacks": ["php", "node", "python"], "typescript": True,
                                                                              "frontend_frameworks": ["react"], "orm": ["eloquent"]})}
    return set(scan.RULES) | checks


def check_ids(problems):
    try:
        ids = known_ids()
    except Exception as exc:  # the scanner itself is broken: report it, do not crash
        problems.append(f"cannot load the scanner to verify cited ids: {exc!r}")
        return
    prefixes = {i.split(".")[0] for i in ids}
    for rel in ID_DOCS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for token in sorted(set(ID_RE.findall(text))):
            if token.split(".")[0] not in prefixes:
                continue  # a code token such as console.log, not a rule or check id
            pattern = re.compile("^" + re.escape(token).replace(r"\*", ".*") + "$")
            if not any(pattern.match(i) for i in ids):
                problems.append(f"{rel}: cites '{token}' but no such rule/check exists")


def check_release_metadata(problems):
    """VERSION, CHANGELOG, the template's version marker, and the front matter of every skill must agree."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[\w.]+)?", version):
        problems.append(f"VERSION is missing or not a semantic version: {version!r}")
        return
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") if (ROOT / "CHANGELOG.md").exists() else ""
    if not re.search(rf"^## \[{re.escape(version)}\]", changelog, re.M):
        problems.append(f"CHANGELOG.md has no '## [{version}]' section")
    agents = (ROOT / "template" / "AGENTS.md").read_text(encoding="utf-8")
    if f"<!-- the-maestro {version} -->" not in agents.splitlines()[0]:
        problems.append(f"template/AGENTS.md must start with '<!-- the-maestro {version} -->'")
    for skill in sorted((ROOT / "skills").iterdir()):
        md = skill / "SKILL.md"
        head = md.read_text(encoding="utf-8").split("---")[1] if md.exists() and md.read_text(encoding="utf-8").startswith("---") else ""
        m = re.search(r"(?m)^name:\s*(\S+)", head)
        if not m or m.group(1) != skill.name:
            problems.append(f"skills/{skill.name}/SKILL.md: front matter 'name' must equal the folder name")
        if not re.search(r"(?m)^description:", head):
            problems.append(f"skills/{skill.name}/SKILL.md: front matter has no 'description'")


def run_selftests(problems):
    for path in sorted(ROOT.glob("skills/project-*/scripts/selftest.py")):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
        r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if r.returncode != 0:
            problems.append(f"{path.relative_to(ROOT).as_posix()}: selftest failed\n" + "\n".join(l for l in r.stdout.splitlines() if l.startswith("FAIL")))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    problems = []
    for path in text_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel == "tools/check_kit.py":
            continue
        raw = path.read_bytes()
        if b"\r\n" in raw:
            problems.append(f"{rel}: CRLF line endings (the standard is LF)")
        text = raw.decode("utf-8", errors="replace")
        for term in FORBIDDEN:
            if term in text and rel != "CHANGELOG.md":  # the changelog may quote the old terms it fixed
                problems.append(f"{rel}: contains '{term}'")
        if rel.startswith(NEUTRAL_FILES):
            for term in STACK_LEAKS:
                if term in text:
                    problems.append(f"{rel}: stack-specific term '{term}' in a stack-neutral document")
        if path.suffix == ".py":
            try:
                compile(text, rel, "exec")
            except SyntaxError as exc:
                problems.append(f"{rel}: syntax error line {exc.lineno}")
    for left, right in IDENTICAL_COPIES:
        a, b = ROOT / left, ROOT / right
        if not a.exists() or not b.exists():
            problems.append(f"missing copy: {left} or {right}")
        elif a.read_bytes() != b.read_bytes():
            problems.append(f"copies differ: {left} <-> {right}")
    check_ids(problems)
    check_release_metadata(problems)
    if "--tests" in sys.argv:
        run_selftests(problems)
    if problems:
        print("\n".join(f"[FAIL] {p}" for p in problems))
        return 1
    print("[OK] kit is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
