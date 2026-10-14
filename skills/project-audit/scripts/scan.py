#!/usr/bin/env python3
"""Heuristic, read-only scanner for any web project.

It never modifies the project and never prints secret values (only locations).
All findings are HEURISTICS: they must be verified by reading the code before
being reported as confirmed. Standard library only.

Usage:
    python scan.py <project-root> [--json out.json] [--max-file-lines 300]
                   [--max-func-lines 50] [--max-per-rule 25] [--style-checks]

Style heuristics (design.slop-*) are off by default: no document in docs/ defines
them, so enable them with --style-checks only if the project's own design
guidance asks for them.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from detectors import (  # noqa: E402
    CODE_EXTS, JS_EXTS, PHP_EXTS, SECRET_PATTERNS, SECRET_SKIP, STYLE_EXTS, TS_EXTS,
    find_functions, ident_tokens, is_comment, iter_file_findings, iter_line_findings,
    iter_unit_findings, prev_code_line, strip_strings, words,
)
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from stacks import (  # noqa: E402
    EXCLUDE_DIRS, EXCLUDE_PREFIXES, MAX_BYTES, detect_facts, iter_files, locate, project_checks, read,
)


# severity, dimension, description, standard (where the rule comes from)
# One row per rule id emitted by detectors.py. Adding a detector row without a
# matching entry here is safe: the report falls back to an "unclassified" row.
RULES = {
    "secret.possible": ("critical", "security", "Possible secret/credential in code", "docs/SECURITY.md"),
    "git.env-committed": ("critical", "security", ".env file tracked in Git", "docs/SECURITY.md"),
    "sql.string-built": ("high", "security", "SQL built with string interpolation or concatenation (injection risk)", "docs/SECURITY.md"),
    "php.mass-assignment": ("high", "security", "Unvalidated input bound straight into the data layer (mass assignment)", "docs/SECURITY.md"),
    "frontend.token-in-browser-storage": ("high", "security", "Token stored in browser storage (vulnerable to script injection)", "docs/SECURITY.md"),
    "frontend.public-env-secret": ("high", "security", "Build-time public environment variable named like a secret (its value is sent to the browser)", "docs/SECURITY.md"),
    "php.raw-sql-interpolation": ("high", "security", "Raw query with variable interpolation (SQL injection risk)", "docs/SECURITY.md"),
    "php.missing-strict-types": ("low", "code-standards", "PHP file without declare(strict_types=1)", "docs/CODE-STANDARDS.md"),
    "debug.leftover": ("medium", "code-quality", "Leftover debug call (dd/dump/var_dump/print_r, console.log, debugger, breakpoint/pdb, byebug/binding.pry, dbg!, printStackTrace)", "AGENTS.md § Definition of Done"),
    "env.read-outside-config": ("medium", "backend", "Environment variable read outside the configuration layer", "docs/BACKEND.md"),
    "error.swallowed": ("medium", "backend", "Error caught and ignored (except/pass, empty catch, empty error branch)", "docs/BACKEND.md"),
    "layer.handler-data-access": ("medium", "architecture", "Handler/controller contains many queries or data access (check SoC)", "docs/BACKEND.md"),
    "ts.any": ("medium", "code-standards", "Use of the any type", "docs/FRONTEND.md"),
    "ts.ts-ignore": ("medium", "code-standards", "@ts-ignore / @ts-nocheck", "docs/CODE-STANDARDS.md"),
    "react.class-component": ("medium", "frontend", "Class component (other than an error boundary)", "docs/FRONTEND.md"),
    "react.legacy-api": ("low", "frontend", "Legacy UI-framework API (forwardRef/defaultProps/propTypes/legacy render)", "docs/FRONTEND.md"),
    "frontend.raw-html": ("medium", "security", "Raw HTML injection without sanitisation (dangerouslySetInnerHTML, v-html, {@html}, innerHTML, bypassSecurityTrust*)", "docs/SECURITY.md"),
    "python.shell-true": ("high", "security", "Shell command built by the shell (subprocess shell=True, os.system): command injection risk", "docs/SECURITY.md"),
    "python.eval-exec": ("high", "security", "eval()/exec() call (code injection risk if the input is not fully trusted)", "docs/SECURITY.md"),
    "python.unsafe-deserialization": ("high", "security", "Unsafe deserialization (pickle/marshal/yaml.load without a safe loader)", "docs/SECURITY.md"),
    "python.mutable-default": ("medium", "code-quality", "Mutable default argument (shared between calls)", "docs/CODE-STANDARDS.md"),
    "ruby.sql-interpolation": ("high", "security", "Query built with string interpolation (SQL injection risk)", "docs/SECURITY.md"),
    "ruby.shell-interpolation": ("high", "security", "Shell command built with string interpolation (command injection risk)", "docs/SECURITY.md"),
    "design.hardcoded-color": ("medium", "design", "Hex color hardcoded outside token files", "docs/FRONTEND.md"),
    "design.inline-style": ("low", "design", "Inline style object (check whether the visual values are not tokens)", "docs/FRONTEND.md"),
    "design.slop-gradient-text": ("low", "design", "Gradient text (background-clip: text)", "opt-in style heuristic (--style-checks)"),
    "design.slop-purple-gradient": ("low", "design", "Purple/violet/indigo/pink gradient", "opt-in style heuristic (--style-checks)"),
    "design.slop-eyebrow-caps": ("low", "design", "ALL CAPS label with wide letter-spacing (eyebrow pattern)", "opt-in style heuristic (--style-checks)"),
    "design.slop-default-font": ("low", "design", "Reflex default font (Inter/Roboto/Poppins/Open Sans)", "opt-in style heuristic (--style-checks)"),
    "design.slop-signature-palette": ("low", "design", "Signature AI palette hex (#D97757 / #F4F1EA)", "opt-in style heuristic (--style-checks)"),
    "design.slop-motion": ("low", "design", "Generic entry animation or hover lift/scale", "opt-in style heuristic (--style-checks)"),
    "design.slop-arrow-text": ("low", "design", "Arrow in UI text (generic call-to-action pattern)", "opt-in style heuristic (--style-checks)"),
    "lang.non-english-identifier": ("medium", "code-standards", "Identifier contains non-English words (language pack: see --lang-pack)", "docs/CODE-STANDARDS.md"),
    "lang.non-english-comment": ("low", "code-standards", "Comment in a language other than English (language pack: see --lang-pack)", "docs/CODE-STANDARDS.md"),
    "lang.hardcoded-non-english-text": ("low", "code-standards", "Hardcoded non-English text (should be in a translation file)", "docs/CODE-STANDARDS.md"),
    "doc.missing": ("low", "documentation", "Public class, function, or exported symbol without a doc comment", "docs/CODE-DOCUMENTATION.md"),
    "generic.large-file": ("medium", "architecture", "File too large", "AGENTS.md § Core Principles"),
    "generic.long-function": ("medium", "architecture", "Function/component too long", "AGENTS.md § Core Principles"),
    "comment.todo": ("low", "documentation", "TODO/FIXME/HACK/XXX in code (forbidden; record it in the issue tracker)", "docs/CODE-DOCUMENTATION.md"),
    "comment.prd-reference": ("medium", "documentation", "PRD/document ID reference in code (F-/AC-/SCR-/API-/T- IDs, the word PRD, docs/ paths); move it to docs/prd-reference/", "docs/CODE-DOCUMENTATION.md"),
    "comment.missing-metadata": ("low", "documentation", "File header without @author/@ai", "docs/CODE-DOCUMENTATION.md"),
}

PACK_DIR = Path(__file__).resolve().parent / "langpacks"


def load_lang_packs(spec):
    """(stopwords, identifier_words, language names) for a comma-separated list of pack names or JSON paths.

    A pack lists words that are NOT valid English, so a hit means the code or comment is not in English.
    `none` disables the language checks. Shipped packs: langpacks/<name>.json.
    """
    stop, idents, names = set(), set(), []
    for item in (x.strip() for x in spec.split(",")):
        if not item or item.lower() == "none":
            continue
        path = Path(item) if (os.sep in item or "/" in item or item.endswith(".json")) else PACK_DIR / f"{item.lower()}.json"
        if not path.is_file():
            shipped = ", ".join(sorted(q.stem for q in PACK_DIR.glob("*.json")))
            sys.exit(f"Unknown language pack '{item}'. Shipped packs: {shipped}; or give the path of a JSON file; or 'none'.")
        data = json.loads(path.read_text(encoding="utf-8"))
        stop |= {w.lower() for w in data.get("stopwords", [])}
        idents |= {w.lower() for w in data.get("identifier_words", [])}
        names.append(data.get("language", path.stem))
    return stop, idents, names


CONVENTIONAL = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w\-./]+\))?!?: .+")
SEMVER_TAG = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][\w.]+)?$")






# data access calls of the common ORMs / query builders, as seen from a handler or controller
DATA_ACCESS_RE = re.compile(
    r"::(?:where|query|find|findOrFail|create|firstOrCreate|updateOrCreate)\(|\bDB::|->(?:save|delete)\("            # Eloquent
    r"|\.objects\.(?:filter|get|create|all|exclude|update_or_create)\(|\bsession\.(?:query|execute|add|commit)\("  # Django, SQLAlchemy
    r"|\bprisma\.\w+\.(?:find\w*|create\w*|update\w*|delete\w*|upsert)\(|\b(?:getRepository|createQueryBuilder)\("  # Prisma, TypeORM
    r"|\.(?:findAll|findOne|findByPk|findAndCountAll)\(|\b[Rr]epository\.(?:save|find\w*|delete\w*)\("             # Sequelize, repositories
    r"|\b[A-Z]\w+\.(?:where|find_by|find_by_sql|create!?|update_all|destroy_all)\(|\bdb\.(?:Query|Exec|QueryRow)\(")  # ActiveRecord, Go


class Scan:
    def __init__(self, root, max_file_lines, max_func_lines, max_per_rule, style_checks=False, stopwords=frozenset(), id_words=frozenset()):
        self.root = root
        self.max_file_lines = max_file_lines
        self.max_func_lines = max_func_lines
        self.max_per_rule = max_per_rule
        self.style_checks = style_checks
        self.stopwords = stopwords
        self.id_words = id_words
        self.findings = defaultdict(list)
        self.counts = Counter()
        self.metrics = {"files": Counter(), "loc": 0}
        self.biggest_files = []
        self.longest_functions = []
        self.docblock = {"total": 0, "missing": 0}

    def add(self, rule, rel, line=0, note=""):
        if rule.startswith("design.slop-") and not self.style_checks:
            return
        self.counts[rule] += 1
        if len(self.findings[rule]) < self.max_per_rule:
            self.findings[rule].append({"file": rel, "line": line, "note": note})


def scan_file(sc, path):
    """Collect findings for one file. All rules live in detectors.py."""
    path = Path(path)
    rel = path.relative_to(sc.root).as_posix()
    ext = path.suffix.lower()
    is_code = ext in CODE_EXTS
    is_style = ext in STYLE_EXTS
    if not (is_code or is_style):
        return
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    lines = text.splitlines()
    sc.metrics["files"][ext] += 1
    sc.metrics["loc"] += len(lines)

    in_lang_dir = bool(re.search(r"(^|/)(lang|locales?|translations?)/", rel))
    is_test = bool(re.search(
        r"(^|/)(?:tests?|spec|__tests__)/|\.(?:test|spec)\.[cm]?[jt]sx?$|(^|/)test_|_test\.(?:py|go|rb)$|_spec\.rb$"
        r"|(?:Tests?|Spec)\.(?:java|kt|cs|php)$|(^|/)src/test/", rel))

    # --- file size is a metric, not a detector
    if is_code and len(lines) > sc.max_file_lines and not re.search(r"(^|/)(?:db/)?migrat(?:ions?|e)/|alembic/versions/", rel):
        sc.add("generic.large-file", rel, 1, f"{len(lines)} lines")
    if is_code:
        sc.biggest_files.append((len(lines), rel))
        for fname, start_line, length in find_functions(lines, ext):
            sc.longest_functions.append((length, rel, start_line, fname))
            if length > sc.max_func_lines:
                sc.add("generic.long-function", rel, start_line, f"{fname}: {length} lines")

    # --- every rule, from the data tables in detectors.py
    for rid, r, line, note in iter_unit_findings(rel, ext, lines, is_test, sc.docblock):
        sc.add(rid, r, line, note)
    for rid, r, line, note in iter_file_findings(rel, ext, text, lines, is_test):
        sc.add(rid, r, line, note)
    for rid, r, line, note in iter_line_findings(rel, ext, lines, is_test, sc.stopwords, sc.id_words,
                                                in_lang_dir, SECRET_PATTERNS, SECRET_SKIP):
        sc.add(rid, r, line, note)

    # --- a handler/controller with data access on many lines is an SoC finding
    if (ext in CODE_EXTS and not is_test
            and re.search(r"(^|/)(?:controllers?|handlers?|routers?|routes?|endpoints?|views?|api)(?:/|\.)|Controllers?\.[a-z]+$|Handlers?\.[a-z]+$", rel, re.I)):
        hits = [i + 1 for i, l in enumerate(lines)
                if DATA_ACCESS_RE.search(l) and not is_comment(l.strip(), ext)]
        if len(hits) >= 3:
            sc.add("layer.handler-data-access", rel, hits[0], f"{len(hits)} data access lines")


def git_info(root):
    info = {"available": False}
    if not (root / ".git").exists():
        return info, []

    def run(*args):
        try:
            r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
            return r.returncode, r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return 1, ""

    info["available"] = True
    info["branch"] = run("rev-parse", "--abbrev-ref", "HEAD")[1]
    info["uncommitted_files"] = len([l for l in run("status", "--porcelain")[1].splitlines() if l])
    tags = [t for t in run("tag", "--list")[1].splitlines() if t]
    info["tags"] = len(tags)
    info["semver_tags"] = len([t for t in tags if SEMVER_TAG.match(t)])
    subjects = [s for s in run("log", "-50", "--pretty=%s")[1].splitlines() if s]
    info["commits_checked"] = len(subjects)
    ok = len([s for s in subjects if CONVENTIONAL.match(s)])
    info["conventional_commits_ratio"] = round(ok / len(subjects), 2) if subjects else None
    findings = []
    if run("ls-files", "--error-unmatch", ".env")[0] == 0:
        findings.append({"file": ".env", "line": 0, "note": "tracked in Git"})
    return info, findings


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--json")
    ap.add_argument("--max-file-lines", type=int, default=300)
    ap.add_argument("--max-func-lines", type=int, default=50)
    ap.add_argument("--max-per-rule", type=int, default=25)
    ap.add_argument("--lang-pack", default="id",
                    help="language(s) the team might write instead of English: shipped pack names (id, es, pt, fr, de), "
                         "a JSON file, comma-separated, or 'none' (default: id)")
    ap.add_argument("--style-checks", action="store_true",
                    help="also report design.slop-* style heuristics (off by default)")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        sys.exit(f"Not a folder: {root}")

    stopwords, id_words, pack_names = load_lang_packs(a.lang_pack)
    sc = Scan(root, a.max_file_lines, a.max_func_lines, a.max_per_rule, a.style_checks, stopwords, id_words)
    secret_exts = {".json", ".yml", ".yaml", ".xml"}
    for p in iter_files(root):
        scan_file(sc, p)
        n = p.name
        if n.startswith(".env"):
            for i, l in enumerate(read(p).splitlines(), start=1):
                if re.match(r"\s*(export\s+)?(NEXT_PUBLIC|NUXT_PUBLIC|VITE|REACT_APP|VUE_APP|GATSBY|EXPO_PUBLIC|PUBLIC)_\w*(SECRET|PASSWORD|PRIVATE|TOKEN)\w*\s*=", l):
                    sc.add("frontend.public-env-secret", p.relative_to(root).as_posix(), i, "variable name")
        if (n.startswith(".env") and n != ".env.example") or (p.suffix in secret_exts and not n.endswith(".lock") and "lock" not in n):
            for i, l in enumerate(read(p).splitlines(), start=1):
                if any(pt.search(l) for pt in SECRET_PATTERNS) and not SECRET_SKIP.search(l):
                    sc.add("secret.possible", p.relative_to(root).as_posix(), i, "value masked")

    facts = detect_facts(root)
    checks = project_checks(root, facts)
    ginfo, gfind = git_info(root)
    for f in gfind:
        sc.add("git.env-committed", f["file"], 0, f["note"])

    result = {
        "root": str(root),
        "thresholds": {"max_file_lines": a.max_file_lines, "max_func_lines": a.max_func_lines},
        "facts": facts,
        "lang_packs": pack_names,
        "git": ginfo,
        "project_checks": checks,
        "metrics": {
            "files": dict(sc.metrics["files"]),
            "loc": sc.metrics["loc"],
            "doc_comment": {**sc.docblock, "coverage": round(1 - sc.docblock["missing"] / sc.docblock["total"], 2) if sc.docblock["total"] else None},
            "biggest_files": [{"lines": n, "file": f} for n, f in sorted(sc.biggest_files, reverse=True)[:10]],
            "longest_functions": [{"lines": n, "file": f, "line": l, "name": nm} for n, f, l, nm in sorted(sc.longest_functions, reverse=True)[:10]],
        },
        "rules": {
            rid: {"severity": sev, "dimension": dim, "description": desc, "standard": std,
                  "count": sc.counts[rid], "samples": sc.findings[rid]}
            for rid in RULES if sc.counts[rid]
            for sev, dim, desc, std in [RULES.get(rid, ("?", "other", rid, ""))]
        },
        "note": "All findings are heuristics. Verify by reading the code before reporting them as confirmed.",
    }
    if a.json:
        Path(a.json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    print(f"Project: {root}\nCode files scanned: {sum(sc.metrics['files'].values())} ({sc.metrics['loc']} lines)")
    print("\nLanguage packs: " + (", ".join(pack_names) if pack_names else "none (language checks off)"))
    print("\nDetected facts:")
    for k, v in facts.items():
        if v not in (None, [], False):
            print(f"  {k}: {v}")
    print("\nProject checks:")
    for c in checks:
        print(f"  [{c['status'].upper():4}] {c['id']}: {c['detail']}")
    if ginfo["available"]:
        print(f"\nGit: branch {ginfo['branch']}, {ginfo['uncommitted_files']} uncommitted files, "
              f"{ginfo['semver_tags']} semver tags, Conventional Commits {ginfo['conventional_commits_ratio']} of the last {ginfo['commits_checked']} commits")
    dc = result["metrics"]["doc_comment"]
    if dc["total"]:
        print(f"Doc comments: {dc['coverage']:.0%} of {dc['total']} units")
    print("\nHeuristic findings (sorted by severity):")
    for rid, r in sorted(result["rules"].items(), key=lambda kv: (order[kv[1]["severity"]], -kv[1]["count"])):
        print(f"  [{r['severity'].upper():8}] {rid}: {r['count']}  - {r['description']}")
        for s in r["samples"][:3]:
            print(f"      {s['file']}:{s['line']} {s['note']}")
    if not result["rules"]:
        print("  (none)")
    if a.json:
        print(f"\nFull JSON: {a.json}")


if __name__ == "__main__":
    main()
