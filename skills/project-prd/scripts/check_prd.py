#!/usr/bin/env python3
"""Structural and consistency checker for PRDs written with the project-prd skill.

It checks the document, not the quality of the ideas: required sections, ID
consistency (features, acceptance criteria, screens, endpoints, tests), coverage,
leftover placeholders, size, and a few API/design conventions. Traceability is
computed from the tables (no hand-written matrix). Read-only, standard library only.

Usage:
    python check_prd.py <prd.md> [--root <project-root>] [--require-design-files]
                        [--phase N] [--trace] [--max-lines N]

--phase N restricts the design-file check to screens whose features belong to
phases <= N (a backend-only phase must not be blocked by later screens).
--trace prints the computed feature -> AC / screen / API / test matrix.

Exit code 1 when there are errors, 0 otherwise (warnings do not fail).
"""
import argparse
import re
import sys
from pathlib import Path

# (keyword in the section title, fallback number). Sections are found by keyword so
# that renumbering or reordering a PRD never breaks the checker.
REQUIRED = [
    ("summary", 1), ("feature", 2), ("acceptance", 3), ("rule", 4), ("design", 5),
    ("technical", 6), ("testing", 7), ("implementation", 8), ("risk", 9),
]
PRIORITIES = {"essential", "important", "optional"}
ORIGINS = {"requested", "implicit essential", "recommended"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PATH_SEG = re.compile(r"^([a-z0-9]+(-[a-z0-9]+)*|\{[a-zA-Z_][a-zA-Z0-9_]*\})$")


def split_sections(text):
    sections, cur, buf, infence = {}, None, [], False
    for line in text.splitlines():
        if line.startswith("```"):
            infence = not infence
        m = None if infence else re.match(r"^## (\d+)\.\s+(.*)$", line)
        if m:
            if cur is not None:
                sections[cur[0]] = (cur[1], "\n".join(buf))
            cur, buf = (int(m.group(1)), m.group(2)), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sections[cur[0]] = (cur[1], "\n".join(buf))
    return sections


def find_section(sections, keyword, fallback):
    """Return (number, title, body) of the section whose title has keyword, else the fallback number."""
    for n, (title, body) in sections.items():
        if keyword in title.lower():
            return n, title, body
    if fallback in sections:
        title, body = sections[fallback]
        return fallback, title, body
    return None, "", ""


def parse_tables(body):
    """Return a list of tables; each table is a list of dict rows keyed by header."""
    tables, lines, i = [], body.splitlines(), 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip().lower() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                rows.append(dict(zip(header, cells)))
                j += 1
            tables.append(rows)
            i = j
        else:
            i += 1
    return tables


def first_col_ids(body, pattern):
    ids = {}
    for table in parse_tables(body):
        for row in table:
            first = next(iter(row.values()), "")
            if re.fullmatch(pattern, first):
                ids[first] = row
    return ids


def strip_code(text):
    out, infence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            infence = not infence
            continue
        if not infence:
            out.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(out)


def feature_ids(cell):
    return re.findall(r"F-\d{3}", cell or "")


def phase_of(row):
    m = re.search(r"\d+", (row or {}).get("phase", ""))
    return int(m.group()) if m else None


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prd")
    ap.add_argument("--root", help="project root, to check docs/design/screens/<slug>.md")
    ap.add_argument("--require-design-files", action="store_true", help="missing design files become errors")
    ap.add_argument("--phase", type=int, help="only require design files for screens of features in phases <= N")
    ap.add_argument("--trace", action="store_true", help="print the computed traceability matrix")
    ap.add_argument("--max-lines", type=int, default=450, help="warn when the PRD is longer than this (default 450)")
    a = ap.parse_args()

    text = Path(a.prd).read_text(encoding="utf-8")
    errors, warnings = [], []
    sections = split_sections(text)

    found = {}
    for kw, fallback in REQUIRED:
        n, title, body = find_section(sections, kw, fallback)
        if n is None:
            errors.append(f"Section '{kw}' not found. Use heading '## <number>. ... {kw} ...'.")
        found[kw] = body
    body = lambda kw: found.get(kw, "")

    n_lines = len(text.splitlines())
    if n_lines > a.max_lines:
        warnings.append(f"PRD {n_lines} lines (> {a.max_lines}): compact it (one sentence per item, no standard repetition, no unrequested sections).")

    # --- features
    features = first_col_ids(body("feature"), r"F-\d{3}")
    if not features:
        errors.append("Feature catalog: no feature with ID F-### in the table.")
    for fid, row in features.items():
        pr = row.get("priority", "").lower()
        og = row.get("origin", "").lower()
        if pr not in PRIORITIES:
            errors.append(f"{fid}: priority '{row.get('priority', '')}' is not valid (essential / important / optional).")
        if og not in ORIGINS:
            errors.append(f"{fid}: origin '{row.get('origin', '')}' is not valid (requested / implicit essential / recommended).")
        if not re.search(r"\d", row.get("phase", "")):
            warnings.append(f"{fid}: Phase column is empty; the build cannot tell which phase this feature belongs to.")
    essential = {f for f, r in features.items() if r.get("priority", "").lower() == "essential"}
    if features and not essential:
        warnings.append("Feature catalog: no feature with priority 'essential' (empty MVP?).")

    # --- acceptance criteria
    ac_text = body("acceptance")
    ac_ids = set(re.findall(r"\bAC-F\d{3}-\d+\b", ac_text))
    ac_by_feature = {}
    for ac in ac_ids:
        ac_by_feature.setdefault("F-" + re.match(r"AC-F(\d{3})-", ac).group(1), []).append(ac)
    for fid in features:
        if not ac_by_feature.get(fid):
            (errors if fid in essential else warnings).append(f"{fid}: has no acceptance criteria yet (AC-F###-n).")
    for fid in ac_by_feature:
        if fid not in features:
            errors.append(f"Acceptance criteria refer to feature {fid} that is not in the catalog.")
    for ac in sorted(ac_ids):
        line = next((l for l in ac_text.splitlines() if re.search(rf"\b{ac}\b", l)), "")
        if line and not re.search(r"(?i)\bthen\b|\bmaka\b", line):
            warnings.append(f"{ac}: does not contain 'then' (a testable result).")

    # --- screens
    screens = first_col_ids(body("design"), r"SCR-\d{3}")
    for sid, row in screens.items():
        slug = row.get("slug", "")
        if not SLUG.match(slug):
            errors.append(f"{sid}: slug '{slug}' is not lowercase English kebab-case.")

    # --- endpoints
    apis = first_col_ids(body("technical"), r"API-\d{3}")
    for aid, row in apis.items():
        spec = next((v for k, v in row.items() if "path" in k or "endpoint" in k), "")
        m = re.match(r"^`?([A-Z]+)\s+(/\S*?)`?$", spec)
        if not m:
            errors.append(f"{aid}: endpoint column must be in the format 'METHOD /api/v1/path' (found '{spec}').")
            continue
        method, path = m.groups()
        if method not in METHODS:
            errors.append(f"{aid}: method '{method}' is not valid.")
        if not re.match(r"^/api/v\d+/", path):
            errors.append(f"{aid}: path '{path}' must start with /api/v<number>/ (docs/API.md).")
        segs = [s for s in path.strip("/").split("/")[2:] if s]
        bad = [s for s in segs if not PATH_SEG.match(s)]
        if bad:
            errors.append(f"{aid}: path segments {bad} must be lowercase kebab-case or {{param}} (docs/API.md).")

    # --- extra tests (outside AC); the table may be empty
    tests = first_col_ids(body("testing"), r"T-\d{3}")

    # --- consistency: every table row points to a feature that exists
    for kind, table in (("Screen", screens), ("Endpoint", apis), ("Test", tests)):
        for rid, row in table.items():
            refs = feature_ids(row.get("feature", ""))
            if not refs:
                warnings.append(f"{rid}: Feature column is empty.")
            for f in refs:
                if f not in features:
                    errors.append(f"{rid}: refers to {f} that is not in the feature catalog.")

    # --- coverage (computed traceability)
    trace = {}
    for fid, row in features.items():
        trace[fid] = {
            "ac": sorted(ac_by_feature.get(fid, [])),
            "scr": [s for s, r in screens.items() if fid in feature_ids(r.get("feature", ""))],
            "api": [i for i, r in apis.items() if fid in feature_ids(r.get("feature", ""))],
            "t": [t for t, r in tests.items() if fid in feature_ids(r.get("feature", ""))],
        }
        if fid in essential and not trace[fid]["scr"] and not trace[fid]["api"]:
            warnings.append(f"{fid}: feature with priority 'essential' has no screen and no endpoint (internal job/CLI? make sure it is intentional).")

    # --- placeholders (outside code): hard for fill-ins, soft for TBD/TODO
    clean = strip_code(text)
    for pat, label in ((r"_fill_", "_fill_"), (r"(?i)lorem ipsum", "lorem ipsum"), (r"<fill[^>]*>", "<fill ...>")):
        n = len(re.findall(pat, clean))
        if n:
            errors.append(f"Placeholder '{label}' is still present ({n}x). Fill it in or move it to Open Questions.")
    for pat, label in ((r"\bTBD\b", "TBD"), (r"\bTODO\b", "TODO")):
        n = len(re.findall(pat, clean))
        if n:
            warnings.append(f"'{label}' appears {n}x: turn it into an Open Question (Q-###) or an Assumption (A-###).")

    # --- assumptions and phases
    if not re.search(r"\b[AQ]-\d{3}\b", body("risk")):
        warnings.append("Risk/Assumptions/Questions: no A-### and no Q-###. Are you sure there are none?")
    if not re.search(r"(?i)phase\s*\d|milestone", body("implementation")):
        warnings.append("Implementation plan: no '### Phase N - name' split.")

    # --- design files
    if a.root:
        root = Path(a.root)
        strict = a.require_design_files
        for sid, row in screens.items():
            slug = row.get("slug", "")
            phases = [phase_of(features.get(f)) for f in feature_ids(row.get("feature", ""))]
            phases = [p for p in phases if p is not None]
            if a.phase is not None and phases and min(phases) > a.phase:
                continue
            if slug and not (root / "docs" / "design" / "screens" / f"{slug}.md").exists():
                (errors if strict else warnings).append(f"{sid}: docs/design/screens/{slug}.md does not exist yet.")

    print(f"PRD: {a.prd} ({n_lines} lines)")
    print(f"Features: {len(features)} (essential: {len(essential)}) | AC: {len(ac_ids)} | Screens: {len(screens)} | Endpoints: {len(apis)} | Extra tests: {len(tests)}")
    if a.trace:
        print("\nTraceability (computed automatically):")
        for fid, t in trace.items():
            print(f"  {fid}: AC {len(t['ac'])} | " + " ".join(t["scr"] + t["api"] + t["t"] or ["-"]))
        print()
    for e in errors:
        print(f"[ERROR] {e}")
    for w in warnings:
        print(f"[WARN ] {w}")
    if not errors and not warnings:
        print("All checks passed.")
    elif not errors:
        print("No errors (warnings only).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
