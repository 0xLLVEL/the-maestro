#!/usr/bin/env python3
"""Task planner and conformance checker for builds driven by project-prd PRDs.

Subcommands:
    plan   <prd.md> [--phase N] [--progress docs/build/<slug>.md] [--json out.json]
        Turns section 12 of the PRD into a task list, enriched with the acceptance
        criteria, endpoints, screens and tests of each task's features. Task status is
        read from the progress file (auto-detected at docs/build/<slug>.md) on resume.

    preflight <prd.md> --root <project-root> [--phase N] [--check-prd path/to/check_prd.py]
        Checks readiness before coding: AGENTS.md and placeholders, project scaffold
        (greenfield detection), clean git tree and working branch, PRD status and validity
        (design files are required only for screens of phases <= N when --phase is given),
        open questions, and PRD version drift against docs/build/<slug>.md.
        Exit code 1 when something blocks the build.

    start <prd.md> --root <project-root> [--phase N]
        preflight + plan in ONE call (saves a round trip at the start of a session).

    scaffold <prd.md> --root <project-root> [--phase N]
        Creates docs/prd-reference/<slug>.md pre-filled with every ID of the PRD (rows to be
        completed with test file, test name and code symbols). Never overwrites an existing file.

    verify <prd.md> --root <project-root> [--phase N] [--ac-table] [--json out.json]
        Checks, heuristically, that what the PRD describes exists in the code:
        API routes, front-end pages, design files, the PRD reference index (docs/prd-reference/<slug>.md:
        tests and acceptance criteria mapped to test files, test names and code symbols), PRD IDs leaking
        into code (forbidden: docs/CODE-DOCUMENTATION.md), and (without --phase) new database columns and
        translation keys.
        Exit code 1 when something is missing ([MISS]); [?] needs a manual check.

Read-only (writes only the optional --json file). Standard library only.
All verify results are HEURISTICS: confirm them by reading the code.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", "vendor", "node_modules", "storage", "dist", "build", ".next", ".nuxt", ".svelte-kit",
                "backup", "coverage", ".idea", ".vscode", "__pycache__", ".turbo", ".cache",
                ".venv", "venv", "env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
                "target", ".gradle", "bin", "obj", ".bundle"}
MAX_BYTES = 1_500_000
TEXT_EXTS = {".php", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".py", ".go", ".rb",
             ".java", ".kt", ".cs", ".rs", ".json"}
PAGE_EXTS = {".tsx", ".jsx", ".ts", ".js", ".py", ".rb"}
LOCALE_DIRS = {"lang", "locales", "locale", "messages", "i18n", "translations"}


# --------------------------------------------------------------------------- parsing
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


def parse_tables(body):
    """Return a list of tables; each table is a list of dict rows keyed by lowercase header."""
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


def rows_with_id(body, pattern):
    out = {}
    for table in parse_tables(body):
        for row in table:
            first = next(iter(row.values()), "")
            if re.fullmatch(pattern, first):
                out[first] = row
    return out


def ids_in(text, pattern):
    return list(dict.fromkeys(re.findall(pattern, text or "")))


# Sections are found by a keyword of their title (fallback: the number), so a PRD that is
# reordered or renumbered still parses.
SECTION_KEYS = {"feature": 2, "acceptance": 3, "design": 5, "technical": 6,
                "testing": 7, "implementation": 8, "risk": 9}


def section_body(sections, key):
    for _, (title, body) in sections.items():
        if key in title.lower():
            return body
    return sections.get(SECTION_KEYS[key], ("", ""))[1]


def load_prd(path):
    text = Path(path).read_text(encoding="utf-8")
    sections = split_sections(text)
    bodies = {k: section_body(sections, k) for k in SECTION_KEYS}
    body = lambda k: bodies[k]
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), Path(path).stem)
    meta = {}
    for table in parse_tables(text.split("\n## 1.")[0]):
        for row in table:
            if "field" in row:
                meta[row["field"].lower()] = row.get("value", "")

    features = rows_with_id(body("feature"), r"F-\d{3}")
    stories = {}
    cur = None
    for line in body("acceptance").splitlines():
        m = re.match(r"^###\s+(F-\d{3})\b", line)
        if m:
            cur = m.group(1)
            stories[cur] = {"acs": [], "edge": ""}
            continue
        if cur:
            m = re.match(r"^-\s+(AC-F\d{3}-\d+):\s*(.*)$", line)
            if m:
                stories[cur]["acs"].append({"id": m.group(1), "text": m.group(2).strip()})
            elif re.match(r"^-\s+\*\*Edge", line):
                stories[cur]["edge"] = re.sub(r"^-\s+\*\*[^*]+\*\*:?\s*", "", line).strip()

    screens = rows_with_id(body("design"), r"SCR-\d{3}")
    endpoints = rows_with_id(body("technical"), r"API-\d{3}")
    tests = rows_with_id(body("testing"), r"T-\d{3}")
    notes = rows_with_id(body("risk"), r"[AQR]-\d{3}")

    phases, cur = [], None
    for line in body("implementation").splitlines():
        m = re.match(r"^###\s+Phase\s+(\d+)\s*[-–—:]?\s*(.*)$", line)
        if m:
            cur = {"phase": int(m.group(1)), "name": m.group(2).strip(), "tasks": [], "_lines": []}
            phases.append(cur)
        elif cur is not None:
            cur["_lines"].append(line)
    for ph in phases:
        for table in parse_tables("\n".join(ph.pop("_lines"))):
            for row in table:
                if "task" in row:
                    ph["tasks"].append(row)
    release = [l.strip() for l in body("implementation").splitlines() if l.strip().lower().startswith("release")]

    return {"title": title, "meta": meta, "features": features, "stories": stories,
            "screens": screens, "endpoints": endpoints, "tests": tests, "notes": notes,
            "phases": phases, "release": release, "sections": sections, "bodies": bodies}


def features_of(row, key="feature"):
    return ids_in(row.get(key, ""), r"F-\d{3}")


def feature_phase(prd, fid):
    try:
        return int(re.search(r"\d+", prd["features"][fid].get("phase", "")).group())
    except (KeyError, AttributeError):
        return None


# --------------------------------------------------------------------------- plan
def task_info(prd, task):
    feats = features_of(task)
    note = task.get("notes", "")
    name = task.get("task", "")
    return {
        "task": name,
        "features": feats,
        "effort": task.get("effort", ""),
        "notes": note,
        "branch": next(iter(re.findall(r"(?:feature|fix|refactor|chore)/[\w./-]+", note)), None),
        "scope": next(iter(re.findall(r"scope\s+`?([\w-]+)`?", note)), None),
        "ponytail": "ponytail" in note.lower(),
        "migration": bool(re.search(r"migration", name + " " + note, re.I)),
        "acs": [ac for f in feats for ac in prd["stories"].get(f, {}).get("acs", [])],
        "endpoints": [i for i, r in prd["endpoints"].items() if set(features_of(r)) & set(feats)],
        "screens": [i for i, r in prd["screens"].items() if set(features_of(r)) & set(feats)],
        "tests": [i for i, r in prd["tests"].items() if set(features_of(r)) & set(feats)],
    }


def read_progress(prd, explicit):
    """Return ({normalized task name: status}, path) from docs/build/<slug>.md, if any."""
    path = Path(explicit) if explicit else Path("docs") / "build" / f"{prd['meta'].get('slug', '')}.md"
    if not path.is_file():
        return {}, None
    status = {}
    for table in parse_tables(path.read_text(encoding="utf-8")):
        for row in table:
            if "task" in row and "status" in row:
                status[row["task"].strip().lower()] = row["status"].strip().lower()
    return status, path


def cmd_plan(a):
    prd = load_prd(a.prd)
    phases = [p for p in prd["phases"] if a.phase in (None, p["phase"])]
    if not phases:
        sys.exit("No matching phase. Make sure the Implementation Plan section uses the heading '### Phase N - name' and a table with a 'Task' column.")
    progress, progress_path = read_progress(prd, a.progress)
    status = prd["meta"].get("status", "?")
    out = {"title": prd["title"], "status": status, "version": prd["meta"].get("version", "?"),
           "slug": prd["meta"].get("slug", ""), "phases": [], "release": prd["release"]}
    lines = [f"# Build plan: {prd['title']}", "",
             f"PRD: v{out['version']} | Status: {status} | Slug: {out['slug']}"]
    if status.strip().lower() == "draft":
        lines.append("ATTENTION: PRD status is still Draft. Confirm user approval before writing code.")
    if progress_path:
        lines.append(f"Progress read from {progress_path.as_posix()} (task status shown below).")
    all_acs, counts = {}, {}
    for ph in phases:
        tasks = [task_info(prd, t) for t in ph["tasks"]]
        for t in tasks:
            t["status"] = progress.get(t["task"].strip().lower()) if progress_path else None
            counts[t["status"] or "not in the progress file"] = counts.get(t["status"] or "not in the progress file", 0) + 1
            for ac in t["acs"]:
                all_acs[ac["id"]] = ac["text"]
        out["phases"].append({"phase": ph["phase"], "name": ph["name"], "tasks": tasks})
        lines += ["", f"## Phase {ph['phase']} - {ph['name']}"]
        for n, t in enumerate(tasks, 1):
            flags = [f for f, on in (("migration", t["migration"]), ("ponytail", t["ponytail"])) if on]
            st = f" -> {t['status']}" if t["status"] else ""
            lines.append(f"\n### Task {n}: {t['task']} [{t['effort'] or '?'}] {' '.join(f'({f})' for f in flags)}{st}".rstrip())
            lines.append(f"- Features: {', '.join(t['features']) or '-'}" + (f" | Branch: {t['branch']}" if t["branch"] else "")
                         + (f" | Scope commit: {t['scope']}" if t["scope"] else ""))
            if t["notes"]:
                lines.append(f"- PRD notes: {t['notes']}")
            if t["acs"]:
                lines.append("- AC: " + ", ".join(ac["id"] for ac in t["acs"]))
            if t["endpoints"]:
                lines.append("- Endpoint: " + ", ".join(f"{i} {prd['endpoints'][i].get('endpoint', '')}" for i in t["endpoints"]))
            if t["screens"]:
                lines.append("- Screens: " + ", ".join(f"{i} ({prd['screens'][i].get('slug', '')})" for i in t["screens"]))
            if t["tests"]:
                lines.append("- Test: " + ", ".join(t["tests"]))
    if all_acs:
        lines += ["", "## Acceptance criteria for this phase"] + [f"- {i}: {txt}" for i, txt in all_acs.items()]
    if progress_path:
        lines += ["", "## Progress summary", "- " + ", ".join(f"{k}: {v}" for k, v in counts.items())]
    cutoff = max(p["phase"] for p in phases)
    open_q = [(i, r) for i, r in prd["notes"].items() if i.startswith("Q-")]
    if open_q:
        lines += ["", "## Open questions (answer first if they affect this phase)"]
        lines += [f"- {i}: {r.get('deskripsi', '')}" for i, r in open_q]
    assumptions = [(i, r) for i, r in prd["notes"].items() if i.startswith("A-")]
    if assumptions:
        lines += ["", "## PRD assumptions"] + [f"- {i}: {r.get('deskripsi', '')}" for i, r in assumptions]
    if prd["release"]:
        lines += ["", "## Release"] + [f"- {r}" for r in prd["release"]]
    lines += ["", f"(scope through Phase {cutoff}; Optional features are not built unless requested)"]
    print("\n".join(lines))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- verify
_FILE_INDEX = {}


def file_index(root):
    """All project files, computed ONCE per run. Uses `git ls-files` (tracked + untracked,
    .gitignore respected, so node_modules/vendor are never visited); falls back to an
    os.walk that prunes EXCLUDE_DIRS in place (rglob would descend into them)."""
    key = str(root)
    if key in _FILE_INDEX:
        return _FILE_INDEX[key]
    files = []
    try:
        r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root,
                           capture_output=True, timeout=60)
        if r.returncode == 0 and r.stdout:
            for rel in r.stdout.decode("utf-8", "ignore").split("\0"):
                if rel and not any(part in EXCLUDE_DIRS for part in Path(rel).parts[:-1]):
                    f = root / rel
                    if f.is_file():
                        files.append(f)
    except (OSError, subprocess.SubprocessError):
        pass
    if not files:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            files.extend(Path(dirpath) / n for n in filenames)
    _FILE_INDEX[key] = files
    return files


def iter_files(root):
    yield from file_index(root)


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore") if p.stat().st_size <= MAX_BYTES else ""
    except OSError:
        return ""


def norm_path(p):
    p = "/" + p.strip().strip("/")
    p = re.sub(r"\{[^}]*\}", "{}", p)
    p = re.sub(r"\[\.\.\.[^\]]*\]", "{}", p)
    p = re.sub(r"\[[^\]]*\]", "{}", p)
    return p if p == "/" else p.rstrip("/")


ROUTE_CALL_PATTERNS = [
    # a route framework: Route::get('path', ...)
    re.compile(r"Route::(get|post|put|patch|delete|options|any)\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Express / Koa / Hapi and friends: app.get('path', ...), router.post('path', ...)
    re.compile(r"\b(?:app|router|server|api)\s*\.\s*(get|post|put|patch|delete|options|all|use)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Generic method-style call: .get('path', ...)
    re.compile(r"\.\s*(get|post|put|patch|delete|options)\s*\(\s*['\"](/[^'\"]+)['\"]", re.I),
    # Flask / Bottle / FastAPI / AIOHTTP decorators
    re.compile(r"@\w+\s*\.\s*route\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    re.compile(r"add_api_route\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Django: path('route/', view)
    re.compile(r"\bpath\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    # Go net/http, chi, gorilla: Handle("/x", h), HandleFunc("/x", h)
    re.compile(r"\bHandle(?:Func)?\s*\(\s*\"([^\"]+)\""),
    # Spring: @GetMapping("/x"), @RequestMapping("/x")
    re.compile(r"@(Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:(?:value|path)\s*=\s*)?\"([^\"]+)\""),
    re.compile(r"@RequestMapping\s*\(\s*(?:(?:value|path)\s*=\s*)?\"([^\"]+)\""),
    # ASP.NET: [HttpGet("x")], [Route("api/x")]
    re.compile(r"\[Http(Get|Post|Put|Patch|Delete)\(\s*\"([^\"]+)\""),
    re.compile(r"\[Route\(\s*\"([^\"]+)\""),
    # Rails routes.rb: get '/x', to: ...
    re.compile(r"(?m)^\s*(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]"),
]
ROUTE_RESOURCE_PATTERNS = [
    re.compile(r"Route::(?:api)?[rR]esource\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"\bresource\s*\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?m)^\s*resources?\s+:(\w+)"),  # Rails: resources :orders
]
ROUTE_FILE_RE = re.compile(r"(^|/)(routes?|urls?|routers?|endpoints?|handlers?)([/.])", re.I)
ROOT_ENTRY_NAMES = {"app", "main", "server", "index", "program", "asgi", "wsgi"}


def _is_route_file(root, f):
    rel = f.relative_to(root).as_posix()
    if ROUTE_FILE_RE.search(rel) or re.search(r"controller", f.name, re.I):
        return True
    return f.parent == root and f.stem.lower() in ROOT_ENTRY_NAMES and f.suffix in TEXT_EXTS


_API_PREFIX_RE = re.compile(r"^/api(/v\d+)?", re.I)
_API_VERSION_RE = re.compile(r"^/api/(v\d+)", re.I)
DYNAMIC_PATH_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def _strip_api_prefix(p):
    q = _API_PREFIX_RE.sub("", p)
    return q if q.startswith("/") else "/" + q


def _api_version(p):
    m = _API_VERSION_RE.match(p)
    return m.group(1).lower() if m else None


def norm_dynamic(path):
    """Normalise dynamic segments to the PRD's `{param}` form (`:param`, `<param>`, `[param]`)."""
    out = re.sub(r"<(?:\w+:)?([A-Za-z_][A-Za-z0-9_]*)>", r"{\1}", path)  # <param> and Django's <int:param>
    out = DYNAMIC_PATH_RE.sub(r"{\1}", out)
    out = re.sub(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", r"{\1}", out)
    return out


def collect_routes(root):
    """API routes found on disk, across the route conventions of common stacks."""
    routes, resources = set(), []
    for f in iter_files(root):
        if f.suffix not in TEXT_EXTS or not _is_route_file(root, f):
            continue
        t = read(f)
        rel = f.relative_to(root).as_posix()
        for pat in ROUTE_CALL_PATTERNS:
            for m in pat.finditer(t):
                groups = [g for g in m.groups() if g]
                if len(groups) >= 2:
                    method, path = groups[0].upper(), groups[1]
                else:
                    method, path = "ANY", groups[0]
                routes.add((method, norm_path(norm_dynamic(path)), rel))
        for pat in ROUTE_RESOURCE_PATTERNS:
            for m in pat.finditer(t):
                resources.append((m.group(1), rel))
    return routes, resources


DYNAMIC_SEGMENT_RE = re.compile(r"^\[(.+)\]$|^:(.+)$|^\{(.+)\}$|^<(.+)>$")
PAGE_DIRS = ("app", "pages", "views", "screens", "templates")
PAGE_STEM_SKIP = {"_app", "_document", "_error", "404", "500", "layout", "loading", "error", "not-found"}
TEMPLATE_EXTS = {".html", ".hbs", ".ejs", ".pug", ".blade.php", ".vue", ".svelte", ".astro", ".erb", ".twig",
                 ".jinja", ".jinja2", ".j2", ".cshtml", ".razor", ".heex"}


def _page_route_from_parts(parts):
    segs = []
    for s in parts:
        m = DYNAMIC_SEGMENT_RE.match(s)
        if m:
            segs.append("{" + next(g for g in m.groups() if g) + "}")
        elif s.startswith("(") and s.endswith(")"):
            continue
        elif s.startswith("@"):
            continue
        else:
            segs.append(s)
    return norm_path("/".join(segs))


def collect_pages(root):
    """Front-end routes found on disk: the route/view conventions of common stacks."""
    found = {}
    for f in iter_files(root):
        rel = f.relative_to(root).as_posix()
        parts = f.relative_to(root).parts
        if f.suffix == ".blade.php":
            stem = f.name[: -len(".blade.php")]
        else:
            stem = f.stem[:-5] if f.stem.endswith(".html") else f.stem  # show.html.erb -> show
        if stem.lower() in PAGE_STEM_SKIP:
            continue
        for d in PAGE_DIRS:
            if d in parts:
                idx = len(parts) - 1 - parts[::-1].index(d)
                rest = parts[idx + 1:-1]
                if f.suffix in TEMPLATE_EXTS or f.suffix in PAGE_EXTS:
                    tail = [] if stem.lower() in {"index", "page"} else [stem]
                    found[_page_route_from_parts(list(rest) + tail)] = rel
                break
    return found


def collect_test_files(root):
    files = {}
    for f in iter_files(root):
        rel = f.relative_to(root).as_posix()
        is_test = (re.search(r"(^|/)(tests?|spec|__tests__|e2e)/", rel)
                   or re.search(r"\.(test|spec)\.[cm]?[jt]sx?$|^test_.+\.py$|_test\.(py|go|rb)$|_spec\.rb$|(Tests?|Spec)\.(java|kt|cs|php)$", f.name)) and f.suffix in TEXT_EXTS
        if is_test:
            files[rel] = read(f)
    return files


def collect_locale_text(root):
    chunks, found_dir = [], False
    for f in iter_files(root):
        parts = f.relative_to(root).parts
        if any(p in LOCALE_DIRS for p in parts[:-1]) and f.suffix in {".json", ".php", ".ts", ".js", ".yml", ".yaml", ".po", ".pot", ".properties", ".arb", ".toml", ".xlf", ".xliff", ".resx"}:
            found_dir = True
            chunks.append(read(f))
    return "\n".join(chunks), found_dir


# migration folders of the common stacks: Laravel/Rails/Django/Alembic/Flyway/Prisma/EF/Drizzle
MIGRATION_DIR_RE = re.compile(r"(^|/)(?:database/migrations|db/migrate|db/migration|migrations?|Migrations|alembic/versions|prisma/migrations|drizzle)/")
PRD_ID_RE = r"\b(?:F-\d{3}|US-\d{3}|AC-F\d{3}-\d+|SCR-\d{3}|API-\d{3}|T-\d{3}|A-\d{3}|Q-\d{3}|R-\d{3})\b"
CODE_EXTS = {".php", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".py", ".go", ".rb",
             ".java", ".kt", ".cs", ".rs", ".css", ".scss"}
REF_TABLE_KEYS = {"ac": "acs", "scenario": "tests", "feature": "features", "endpoint": "endpoints", "screen": "screens"}


def load_reference(root, slug):
    """Parse docs/prd-reference/<slug>.md into {kind: {id: [row, ...]}}; None when the file is missing."""
    f = root / "docs" / "prd-reference" / f"{slug}.md"
    if not f.is_file():
        return None
    ref = {kind: {} for kind in REF_TABLE_KEYS.values()}
    for table in parse_tables(read(f)):
        for row in table:
            key = next((k for k in REF_TABLE_KEYS if k in row), None)
            if key and row[key]:
                ref[REF_TABLE_KEYS[key]].setdefault(row[key], []).append(row)
    return ref


def code_refs(cell):
    """Backticked `path` or `path::symbol` items of a table cell."""
    return re.findall(r"`([^`]+)`", cell or "")


def broken_code_refs(root, cell):
    """Return problems for each `path[::symbol]` item that does not exist in the code."""
    problems = []
    for item in code_refs(cell):
        path, _, symbol = item.partition("::")
        fp = root / path
        if not fp.is_file():
            problems.append(f"{path} does not exist")
        elif symbol and not re.search(r"(?<![A-Za-z0-9_])" + re.escape(symbol) + r"(?![A-Za-z0-9_])", read(fp)):
            problems.append(f"symbol {symbol} does not exist in {path}")
    return problems


def broken_test_ref(root, row):
    """Return a problem string when the row's test file or test name cannot be found, else None."""
    files = code_refs(row.get("test file", ""))
    names = code_refs(row.get("test name", ""))
    if not files or not names:
        return "Test file / Test name columns are empty"
    fp = root / files[0]
    if not fp.is_file():
        return f"{files[0]} does not exist"
    if names[0] not in read(fp):
        return f"test name not found in {files[0]}"
    return None


def cmd_verify(a):
    prd = load_prd(a.prd)
    root = Path(a.root).resolve()
    if not root.is_dir():
        sys.exit(f"Not a folder: {root}")
    results = []

    def add(status, cid, detail):
        results.append({"status": status, "id": cid, "detail": detail})

    in_scope = lambda row: a.phase is None or any(
        (feature_phase(prd, f) or 0) <= a.phase for f in features_of(row)) or not features_of(row)

    # --- endpoints
    routes, resources = collect_routes(root)
    for aid, row in prd["endpoints"].items():
        if not in_scope(row):
            continue
        m = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(\S+)", row.get("endpoint", ""))
        if not m:
            add("?", aid, "endpoint format is not readable")
            continue
        method, path = m.group(1), norm_path(norm_dynamic(m.group(2).strip("`")))
        short = _strip_api_prefix(path) or "/"
        hit = None
        for mt, p, f in routes:
            if mt != method:
                continue
            pv, qv = _api_version(p), _api_version(path)
            if pv and qv and pv != qv:
                continue
            if path == p or short == (_strip_api_prefix(p) or "/"):
                hit = f
                break
        label = f"{method} {m.group(2).strip('`')}"
        if hit:
            add("OK", aid, f"{label} -> {hit}")
            continue
        seg = short.strip("/").split("/")[0]
        res = next((f for name, f in resources if seg == name.strip("/").split("/")[-1]), None)
        if res:
            add("?", aid, f"{label}: probably registered as a resource in {res}; check the framework's route list")
        else:
            add("MISS", aid, f"{label}: route not found in the route definition files")

    # --- screens: design file + front-end page/view
    pages = collect_pages(root)
    design = root / "docs" / "design"
    for sid, row in prd["screens"].items():
        if not in_scope(row):
            continue
        slug, route = row.get("slug", ""), row.get("route", "").strip("`")
        screen_file = design / "screens" / f"{slug}.md"
        add("OK" if screen_file.exists() else "MISS", f"{sid}.design", f"docs/design/screens/{slug}.md")
        if route.startswith("/"):
            page = pages.get(norm_path(route))
            add("OK" if page else "MISS", f"{sid}.page", f"{route} -> {page}" if page else f"{route}: front-end page/view not found (the framework's pages, views, or templates directory)")

    # --- PRD reference index (docs/prd-reference/<slug>.md): the only place PRD IDs meet code
    slug = Path(a.prd).stem
    ref = load_reference(root, slug)
    ref_hint = f"docs/prd-reference/{slug}.md does not exist yet (create it from references/prd-reference-template.md)"
    add("OK" if ref is not None else "MISS", "ref.file", f"docs/prd-reference/{slug}.md" if ref is not None else ref_hint)
    ref = ref or {kind: {} for kind in REF_TABLE_KEYS.values()}

    for tid, row in prd["tests"].items():
        if not in_scope(row):
            continue
        rows = ref["tests"].get(tid, [])
        if not rows:
            add("MISS", tid, f"not in the reference index yet: {row.get('skenario', '')[:70]}")
            continue
        problems = [x for x in (broken_test_ref(root, r) for r in rows) if x]
        add("MISS" if problems else "OK", tid, "; ".join(problems) if problems else f"test found: {row.get('skenario', '')[:70]}")

    ac_rows = []
    for fid, story in prd["stories"].items():
        if a.phase is not None and (feature_phase(prd, fid) or 0) > a.phase:
            continue
        for ac in story["acs"]:
            rows = ref["acs"].get(ac["id"], [])
            if not rows:
                ac_rows.append((ac["id"], fid, []))
                add("?", ac["id"], "not in the reference index yet (may be covered by another test; verify manually)")
                continue
            problems = [x for r in rows for x in [broken_test_ref(root, r)] if x]
            problems += [x for r in rows for x in broken_code_refs(root, r.get("code", ""))]
            ac_rows.append((ac["id"], fid, [] if problems else [code_refs(r.get("test file", ""))[0] for r in rows if code_refs(r.get("test file", ""))]))
            add("MISS" if problems else "OK", ac["id"], "; ".join(problems) if problems else "test and code found")

    for kind, label in (("features", "F"), ("endpoints", "API"), ("screens", "SCR")):
        for rid, rows in ref[kind].items():
            problems = [x for r in rows for x in broken_code_refs(root, r.get("code", ""))]
            add("MISS" if problems else "OK", f"{rid}.ref", "; ".join(problems) if problems else "code found")

    # --- PRD IDs must not appear in code (comments, test names, strings)
    prd_ids = set(re.findall(PRD_ID_RE, Path(a.prd).read_text(encoding="utf-8")))
    leaks = []
    for f in iter_files(root):
        rel = f.relative_to(root).as_posix()
        if f.suffix not in CODE_EXTS or rel.startswith("docs/"):
            continue
        for n, line in enumerate(read(f).splitlines(), 1):
            hit = next((i for i in re.findall(PRD_ID_RE, line) if i in prd_ids), None)
            if hit:
                leaks.append(f"{rel}:{n} ({hit})")
    if leaks:
        add("MISS", "code.prd-ref", f"{len(leaks)} PRD ID references in code (forbidden): " + ", ".join(leaks[:8]) + (" ..." if len(leaks) > 8 else ""))
    else:
        add("OK", "code.prd-ref", "no PRD IDs in code")

    # --- whole-PRD checks (not tied to a phase)
    if a.phase is None:
        s10 = prd["bodies"]["technical"]
        m = re.search(r"\*\*(?:Model data|Data)[^\n]*", s10)
        if m:
            migrations = "\n".join(read(f) for f in iter_files(root) if MIGRATION_DIR_RE.search(f.relative_to(root).as_posix()))
            for table, col in dict.fromkeys(re.findall(r"`([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)`", m.group(0))):
                add("OK" if col in migrations else "MISS", f"column.{table}.{col}", "mentioned in a migration")
        s9 = prd["bodies"]["design"]
        kp = re.search(r"translation key[^\n]*", s9, re.I)
        if kp:
            locale_text, has_dir = collect_locale_text(root)
            for key in re.findall(r"`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)`", kp.group(0)):
                last = key.split(".")[-1]
                if not has_dir:
                    add("?", f"i18n.{key}", "translation folder (lang/, locales/, messages/) not found")
                else:
                    add("OK" if re.search(rf"[\"']{re.escape(last)}[\"']", locale_text) else "MISS", f"i18n.{key}", "last key segment present in the translation files")

    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("OK", "MISS", "?")}
    scope = f"through Phase {a.phase}" if a.phase else "the whole PRD"
    print(f"PRD conformance: {prd['title']} ({scope})")
    for r in results:
        print(f"  [{r['status']:4}] {r['id']}: {r['detail']}")
    print(f"\nSummary: {counts['OK']} OK, {counts['MISS']} MISS, {counts['?']} need manual verification")
    print("Note: heuristics. Open the code to confirm; [OK] is not proof that the AC is satisfied (that is the test's job).")
    if a.phase is not None:
        print("The migration column and translation key checks are skipped (not tied to a phase); run without --phase for those.")
    if a.ac_table:
        print("\n| AC | Feature | Test | Status |\n|---|---|---|---|")
        for acid, fid, files in ac_rows:
            print(f"| {acid} | {fid} | {', '.join(f'`{x}`' for x in files[:3]) or '-'} | {'connected' if files else 'not connected'} |")
    if a.json:
        Path(a.json).write_text(json.dumps({"counts": counts, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.exit(1 if counts["MISS"] else 0)


def git(root, *args):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


MANIFEST_NAMES = ("composer.json", "package.json", "pyproject.toml", "requirements.txt", "Pipfile", "go.mod", "pom.xml", "build.gradle", "Cargo.toml", "Gemfile", "*.csproj", "*.sln")

def detect_manifests(root):
    found = {}
    for n in MANIFEST_NAMES:
        for p in [root / n, *root.glob(f"*/{n}"), *root.glob(f"*/*/{n}"), *root.glob(f"*/*/*/{n}")]:
            if p.is_file():
                found.setdefault(n, []).append(p)
    return found

def stack_summary(root, manifests):
    """One-line description of the detected stack, or '' when nothing is recognized."""
    parts = []
    for p in manifests.get("package.json", []):
        deps = set()
        try:
            deps = set(json.loads(read(p)).get("dependencies", {})) | set(json.loads(read(p)).get("devDependencies", {}))
        except (ValueError, TypeError):
            deps = set()
        js = sorted(d for d in deps if d in {"next", "nuxt", "react", "vue", "svelte", "@angular/core", "express", "fastify", "koa", "nestjs", "@nestjs/core"})
        parts.append("node/" + (", ".join(js) if js else "node"))
    if manifests.get("composer.json"):
        parts.append("php/composer")
    if manifests.get("pyproject.toml") or manifests.get("requirements.txt") or manifests.get("Pipfile"):
        py_text = "\n".join(read(p) for n in ("pyproject.toml", "requirements.txt", "Pipfile") for p in manifests.get(n, []))
        py = [n for n in ("django", "fastapi", "flask") if re.search(rf"(?im)(?:^|[\s\"',\[]){n}(?![\w-])", py_text)]
        parts.append("python/" + ", ".join(py) if py else "python")
    if manifests.get("go.mod"):
        parts.append("go")
    if manifests.get("Cargo.toml"):
        parts.append("rust")
    if manifests.get("Gemfile"):
        parts.append("ruby/rails" if any(re.search(r"(?m)^\s*gem\s+['\"]rails['\"]", read(p)) for p in manifests["Gemfile"]) else "ruby")
    if manifests.get("pom.xml") or manifests.get("build.gradle"):
        jvm_text = "\n".join(read(p) for n in ("pom.xml", "build.gradle") for p in manifests.get(n, []))
        parts.append("jvm/spring-boot" if "org.springframework.boot" in jvm_text else "jvm")
    return ", ".join(dict.fromkeys(p for p in parts if p))


def run_preflight(a):
    prd = load_prd(a.prd)
    root = Path(a.root).resolve()
    if not root.is_dir():
        sys.exit(f"Not a folder: {root}")
    results = []

    def add(status, cid, detail):
        results.append({"status": status, "id": cid, "detail": detail})

    agents = root / "AGENTS.md"
    if agents.exists():
        add("OK", "agents.md", "AGENTS.md exists")
        ph = read(agents).count("_fill_")
        add("OK" if ph == 0 else "?", "agents.placeholders", "no _fill_ placeholders" if ph == 0 else f"{ph} _fill_ placeholders are not filled in (fill them from the detected facts, confirm with the user)")
    else:
        add("MISS", "agents.md", "AGENTS.md not found; create it before the build")

    code, _ = git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        add("MISS", "git.repo", "not a Git repository")
    else:
        dirty = [l for l in git(root, "status", "--porcelain")[1].splitlines() if l]
        add("OK" if not dirty else "MISS", "git.clean", "clean working tree" if not dirty else f"{len(dirty)} files are not committed; ask the user to commit or stash")
        branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")[1]
        on_main = branch in {"main", "master", ""}
        add("?" if on_main else "OK", "git.branch", f"branch '{branch}'" + (": create a working branch from main in Step 1 before writing any code (do not build on main)" if on_main else ""))


    manifests = detect_manifests(root)
    if manifests:
        summary = stack_summary(root, manifests)
        add("OK", "project.scaffold", "project manifests found" + (f" ({summary})" if summary else ""))
    else:
        add("?", "project.scaffold", "no dependency manifest found: new project, do the Phase 0 bootstrap (references/bootstrap.md) before Phase 1")

    status = prd["meta"].get("status", "").strip()
    add("?" if status.lower() == "draft" else "OK", "prd.status", f"PRD status '{status}'" + (": confirm user approval and record it in the progress file" if status.lower() == "draft" else ""))

    checker = Path(a.check_prd) if a.check_prd else Path(__file__).resolve().parents[2] / "project-prd" / "scripts" / "check_prd.py"
    if checker.exists():
        r = subprocess.run([sys.executable, str(checker), a.prd, "--root", str(root), "--require-design-files",
                            *(["--phase", str(a.phase)] if getattr(a, "phase", None) else [])], capture_output=True, text=True, encoding="utf-8", errors="replace")
        errs = [l.strip() for l in r.stdout.splitlines() if "[ERROR]" in l]
        add("OK" if r.returncode == 0 else "MISS", "prd.check", "check_prd.py is clean" if r.returncode == 0 else f"{len(errs)} errors: " + "; ".join(errs[:3]))
    else:
        add("?", "prd.check", "check_prd.py not found; run it manually from the project-prd skill (or pass --check-prd)")

    open_q = [i for i in prd["notes"] if i.startswith("Q-")]
    add("?" if open_q else "OK", "prd.open-questions", f"{len(open_q)} open questions ({', '.join(open_q)}): answer the ones that affect the phase" if open_q else "no open questions")

    slug = prd["meta"].get("slug", "")
    progress = root / "docs" / "build" / f"{slug}.md"
    if progress.exists():
        m = re.search(r"version\s+([\d.]+)", read(progress), re.I)
        recorded, current = (m.group(1) if m else None), prd["meta"].get("version", "")
        if recorded and recorded != current:
            add("?", "build.prd-drift", f"the progress file records PRD v{recorded}, the PRD is now v{current}: review the changed or new IDs and update the plan")
        else:
            add("OK", "build.progress", f"resumed session: read {progress.relative_to(root).as_posix()} and continue from the last status")
    else:
        add("OK", "build.progress", "no progress file yet (new session): create it from references/progress-template.md")

    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("OK", "MISS", "?")}
    print(f"Preflight build: {prd['title']}")
    for r in results:
        print(f"  [{r['status']:4}] {r['id']}: {r['detail']}")
    print(f"\nSummary: {counts['OK']} OK, {counts['MISS']} MISS (blocking), {counts['?']} need action or confirmation")
    if a.json:
        Path(a.json).write_text(json.dumps({"counts": counts, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if counts["MISS"] else 0


def cmd_preflight(a):
    sys.exit(run_preflight(a))


def cmd_start(a):
    """preflight + plan in one call; the plan is shown only when nothing blocks."""
    a.check_prd, a.json, a.progress = getattr(a, "check_prd", None), None, None
    code = run_preflight(a)
    if code:
        print("\nPreflight blocked: fix the [MISS] items first; the plan is not shown yet.")
        sys.exit(code)
    print()
    cmd_plan(a)


def cmd_scaffold(a):
    """Create docs/prd-reference/<slug>.md with every PRD ID pre-listed (never overwrites)."""
    prd = load_prd(a.prd)
    root = Path(a.root).resolve()
    slug = Path(a.prd).stem
    target = root / "docs" / "prd-reference" / f"{slug}.md"
    if target.exists():
        print(f"{target.relative_to(root).as_posix()} already exists; not overwritten. Run verify to see the IDs that are not filled in yet.")
        return
    in_phase = lambda fid: a.phase is None or (feature_phase(prd, fid) or 0) <= a.phase
    feats = [f for f in prd["features"] if in_phase(f)]
    keep = lambda row: not features_of(row) or any(in_phase(f) for f in features_of(row))
    version = prd["meta"].get("version", "?")
    lines = [f"# PRD Reference: {prd['title'].removeprefix('PRD:').strip()}", "",
             "| Field | Value |", "|---|---|", f"| PRD | docs/prd/{slug}.md (version {version}) |", "| Last updated | |", "",
             "## Features", "| Feature | Code |", "|---|---|"]
    lines += [f"| {f} | |" for f in feats]
    lines += ["", "## Acceptance criteria", "| AC | Test file | Test name | Code |", "|---|---|---|---|"]
    lines += [f"| {ac['id']} | | | |" for f in feats for ac in prd["stories"].get(f, {}).get("acs", [])]
    lines += ["", "## Test scenarios", "| Scenario | Test file | Test name |", "|---|---|---|"]
    lines += [f"| {t} | | |" for t, r in prd["tests"].items() if keep(r)]
    lines += ["", "## Endpoints", "| Endpoint | Code |", "|---|---|"]
    lines += [f"| {i} | |" for i, r in prd["endpoints"].items() if keep(r)]
    lines += ["", "## Screens", "| Screen | Code |", "|---|---|"]
    lines += [f"| {i} | |" for i, r in prd["screens"].items() if keep(r)]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Created {target.relative_to(root).as_posix()}: fill in the Test file / Test name / Code columns (path from the root plus symbol, no line numbers).")


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("plan")
    p1.add_argument("prd")
    p1.add_argument("--phase", type=int)
    p1.add_argument("--progress", help="progress file (default: docs/build/<slug>.md if it exists)")
    p1.add_argument("--json")
    p2 = sub.add_parser("verify")
    p2.add_argument("prd")
    p2.add_argument("--root", required=True)
    p2.add_argument("--phase", type=int)
    p2.add_argument("--ac-table", action="store_true", help="print a markdown AC coverage table for the progress file")
    p2.add_argument("--json")
    p3 = sub.add_parser("preflight")
    p3.add_argument("prd")
    p3.add_argument("--root", required=True)
    p3.add_argument("--phase", type=int, help="require design files only for screens of phases <= N")
    p3.add_argument("--check-prd")
    p3.add_argument("--json")
    p4 = sub.add_parser("start", help="preflight + plan in one call")
    p4.add_argument("prd")
    p4.add_argument("--root", required=True)
    p4.add_argument("--phase", type=int)
    p4.add_argument("--check-prd")
    p5 = sub.add_parser("scaffold", help="create docs/prd-reference/<slug>.md pre-filled with PRD IDs")
    p5.add_argument("prd")
    p5.add_argument("--root", required=True)
    p5.add_argument("--phase", type=int)
    a = ap.parse_args()
    {"plan": cmd_plan, "verify": cmd_verify, "preflight": cmd_preflight, "start": cmd_start, "scaffold": cmd_scaffold}[a.cmd](a)


if __name__ == "__main__":
    main()
