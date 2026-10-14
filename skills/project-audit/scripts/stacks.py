#!/usr/bin/env python3
"""Stack profiles for project-audit/scripts/scan.py.

What each ecosystem looks like on disk (manifests, lockfiles, runtime pins,
ignore entries, expected tooling, test file shapes) is DATA in STACKS below.
The code that turns that data into facts and project checks has no per-stack
branches except the small fact extractors at the bottom of the "facts" section.
Adding an ecosystem = adding one STACKS entry (plus detector rows in detectors.py).

Standard library only. Nothing here modifies the project.
"""
import fnmatch
import json
import os
import re
from pathlib import Path

EXCLUDE_DIRS = {
    ".git", "vendor", "node_modules", "storage", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "backup", "coverage", ".idea", ".vscode", "__pycache__", ".turbo", ".cache",
    ".venv", "venv", "env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", ".gradle", "bin", "obj", ".bundle",
}
MAX_BYTES = 1_500_000
EXCLUDE_PREFIXES = ("public/build", "bootstrap/cache", "public/hot")


# --------------------------------------------------------------------------- file helpers
def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


_FILES_CACHE = {}


def iter_files(root):
    """Every scannable file under root. The walk happens once per run; later callers reuse the list."""
    key = str(root)
    if key not in _FILES_CACHE:
        _FILES_CACHE[key] = list(_walk_files(root))
    return iter(_FILES_CACHE[key])


def _walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS
            and not any((rel_dir + "/" + d).lstrip("./").startswith(p) for p in EXCLUDE_PREFIXES)
        ]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield p


_LOCATE_CACHE = {}


def clear_cache():
    _LOCATE_CACHE.clear()
    _FILES_CACHE.clear()


def locate(root, filename, depth=2):
    """Files called `filename` (a glob is allowed) in root and up to `depth` levels below it."""
    key = (str(root), filename, depth)
    if key in _LOCATE_CACHE:
        return list(_LOCATE_CACHE[key])
    is_glob = any(c in filename for c in "*?[")
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        d = 0 if rel == "." else rel.count(os.sep) + 1
        dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIRS] if d < depth else []
        names = fnmatch.filter(filenames, filename) if is_glob else ([filename] if filename in filenames else [])
        found.extend(Path(dirpath) / n for n in names)
    _LOCATE_CACHE[key] = found
    return list(found)


# --------------------------------------------------------------------------- the profiles
def _pydep(names):
    """Regex for a Python dependency name in pyproject.toml / requirements / Pipfile (inline arrays included)."""
    return rf"(?im)(?:^|[\s\"',\[])(?:{names})(?=[\s\"'<>=~!^\],;\[]|$)"


def _tool(files=(), patterns=(), deps=(), hint=""):
    return {"files": list(files), "patterns": list(patterns), "deps": list(deps), "hint": hint}


STACKS = {
    "php": {
        "label": "PHP", "manifests": ["composer.json"],
        "locks": ["composer.lock"], "ignore": ["vendor"],
        "pins": {"files": [".php-version", ".tool-versions"], "patterns": [("composer.json", r'"php"\s*:')]},
        "tools": {
            "formatter": _tool(["pint.json", ".php-cs-fixer.php", ".php-cs-fixer.dist.php"],
                               deps=[r'"(?:laravel/pint|friendsofphp/php-cs-fixer)"'], hint="Pint or PHP CS Fixer"),
            "linter": None,
            "static": _tool(["phpstan.neon", "phpstan.neon.dist", "psalm.xml", "psalm.xml.dist"],
                            deps=[r'"(?:phpstan/phpstan|larastan/larastan|nunomaduro/larastan|vimeo/psalm)"'],
                            hint="PHPStan/Larastan or Psalm"),
        },
        "tests": r"(^|/)tests?/.+\.php$|Test\.php$",
    },
    "node": {
        "label": "Node/JavaScript", "manifests": ["package.json"],
        "locks": ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"],
        "managers": {"npm": "package-lock.json", "pnpm": "pnpm-lock.yaml", "yarn": "yarn.lock", "bun": "bun.lockb"},
        "ignore": ["node_modules"],
        "pins": {"files": [".nvmrc", ".node-version", ".tool-versions"],
                 "patterns": [("package.json", r'"engines"\s*:\s*\{[^}]*"node"'), ("package.json", r'"volta"\s*:')]},
        "tools": {
            "formatter": _tool(
                [".prettierrc", ".prettierrc.json", ".prettierrc.yml", ".prettierrc.yaml", ".prettierrc.js", ".prettierrc.cjs",
                 ".prettierrc.mjs", "prettier.config.js", "prettier.config.mjs", "prettier.config.cjs", "biome.json",
                 "biome.jsonc", "dprint.json", ".dprint.json"],
                [("package.json", r'"prettier"\s*:')], [r'"(?:prettier|@biomejs/biome|dprint)"'], "Prettier, Biome, or dprint"),
            "linter": _tool(
                ["eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts", ".eslintrc", ".eslintrc.js",
                 ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml", "biome.json", "biome.jsonc", ".oxlintrc.json"],
                [("package.json", r'"eslintConfig"')], [r'"(?:eslint|@biomejs/biome|oxlint)"'], "ESLint, Biome, or oxlint"),
            "static": _tool(["tsconfig.json"], hint="tsconfig.json"),  # only when TypeScript is used
        },
        "tests": r"\.(?:test|spec)\.[cm]?[jt]sx?$|(^|/)__tests__/",
    },
    "python": {
        "label": "Python", "manifests": ["pyproject.toml", "requirements*.txt", "Pipfile", "setup.py", "setup.cfg"],
        "locks": ["poetry.lock", "uv.lock", "Pipfile.lock", "pdm.lock"],
        "lock_patterns": [("requirements*.txt", r"(?m)^[\w.\-\[\]]+==")],
        "managers": {"poetry": "poetry.lock", "uv": "uv.lock", "pipenv": "Pipfile.lock", "pdm": "pdm.lock"},
        "ignore": [".venv", "venv", "__pycache__"],
        "pins": {"files": [".python-version", "runtime.txt", ".tool-versions"],
                 "patterns": [("pyproject.toml", r"requires-python|python_requires|\[tool\.poetry\.dependencies\][^\[]*python\s*="),
                              ("Pipfile", r"python_version"), ("setup.py", r"python_requires"), ("setup.cfg", r"python_requires")]},
        "tools": {
            "formatter": _tool(["ruff.toml", ".ruff.toml", ".style.yapf"],
                               [("pyproject.toml", r"\[tool\.(?:ruff|black|yapf|autopep8)")],
                               [_pydep("ruff|black|yapf|autopep8")], "Ruff or Black"),
            "linter": _tool(["ruff.toml", ".ruff.toml", ".flake8", ".pylintrc", "pylintrc"],
                            [("pyproject.toml", r"\[tool\.(?:ruff|pylint|flake8)"), ("setup.cfg", r"\[(?:flake8|pylint)"),
                             ("tox.ini", r"\[flake8")],
                            [_pydep("ruff|flake8|pylint")], "Ruff, Flake8, or Pylint"),
            "static": _tool(["mypy.ini", ".mypy.ini", "pyrightconfig.json", ".pytype.cfg"],
                            [("pyproject.toml", r"\[tool\.(?:mypy|pyright|pytype)"), ("setup.cfg", r"\[mypy")],
                            [_pydep("mypy|pyright|pytype")], "mypy or Pyright"),
        },
        "tests": r"(^|/)tests?/.+\.py$|(^|/)test_[^/]*\.py$|_test\.py$",
    },
    "go": {
        "label": "Go", "manifests": ["go.mod"], "locks": ["go.sum"], "ignore": [],
        "pins": {"files": [".tool-versions"], "patterns": [("go.mod", r"(?m)^go\s+\d")]},
        "tools": {"formatter": "gofmt", "linter": "go vet", "static": None},
        "tests": r"_test\.go$",
    },
    "ruby": {
        "label": "Ruby", "manifests": ["Gemfile"], "locks": ["Gemfile.lock"], "ignore": [".bundle", "vendor/bundle"],
        "pins": {"files": [".ruby-version", ".tool-versions"], "patterns": [("Gemfile", r"(?m)^\s*ruby\s")]},
        "tools": {
            "formatter": _tool([".rubocop.yml"], deps=[r"(?m)^\s*gem\s+['\"]rubocop"], hint="RuboCop or StandardRB"),
            "linter": _tool([".rubocop.yml", ".standard.yml"], deps=[r"(?m)^\s*gem\s+['\"](?:rubocop|standard)"], hint="RuboCop or StandardRB"),
            "static": None,
        },
        "tests": r"_(?:spec|test)\.rb$|(^|/)(?:spec|test)/.+\.rb$",
    },
    "jvm": {
        "label": "Java/Kotlin", "manifests": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "locks": None, "ignore": ["target", "build", ".gradle"],
        "pins": {"files": [".java-version", ".sdkmanrc", ".tool-versions"],
                 "patterns": [("pom.xml", r"maven\.compiler|java\.version|<release>"),
                              ("build.gradle", r"sourceCompatibility|JavaVersion|toolchain|jvmTarget"),
                              ("build.gradle.kts", r"sourceCompatibility|JavaVersion|toolchain|jvmTarget")]},
        "tools": {
            "formatter": _tool(["checkstyle.xml"], [("pom.xml", r"spotless|fmt-maven|ktlint"),
                                                    ("build.gradle", r"spotless|ktlint"), ("build.gradle.kts", r"spotless|ktlint")],
                               hint="Spotless or ktlint"),
            "linter": _tool(["checkstyle.xml", "config/checkstyle/checkstyle.xml", "detekt.yml", "config/detekt/detekt.yml"],
                            [("pom.xml", r"checkstyle|spotbugs|pmd"), ("build.gradle", r"checkstyle|spotbugs|pmd|detekt|ktlint"),
                             ("build.gradle.kts", r"checkstyle|spotbugs|pmd|detekt|ktlint")], hint="Checkstyle, SpotBugs, PMD, or detekt"),
            "static": None,
        },
        "tests": r"(^|/)src/test/|Tests?\.(?:java|kt)$",
    },
    "rust": {
        "label": "Rust", "manifests": ["Cargo.toml"], "locks": ["Cargo.lock"], "ignore": ["target"],
        "pins": {"files": ["rust-toolchain", "rust-toolchain.toml"], "patterns": [("Cargo.toml", r"rust-version")]},
        "tools": {"formatter": "cargo fmt", "linter": "cargo clippy", "static": None},
        "tests": r"(^|/)tests/.+\.rs$", "test_content": (".rs", r"#\[cfg\(test\)\]"),
    },
    "dotnet": {
        "label": ".NET", "manifests": ["*.csproj", "*.sln"], "locks": None, "ignore": ["bin", "obj"],
        "pins": {"files": ["global.json"], "patterns": [("*.csproj", r"TargetFramework")]},
        "tools": {"formatter": "dotnet format", "linter": "Roslyn analyzers", "static": None},
        "tests": r"(?:Tests?|Specs?)\.cs$|(^|/)[^/]*\.Tests?/",
    },
}

FRONTEND_DEPS = {"react": "react", "next": "next", "vue": "vue", "nuxt": "nuxt", "svelte": "svelte", "@sveltejs/kit": "sveltekit",
                 "@angular/core": "angular", "solid-js": "solid", "preact": "preact", "astro": "astro",
                 "@remix-run/react": "remix", "@builder.io/qwik": "qwik"}
FULLSTACK_JS = {"next", "nuxt", "sveltekit", "remix", "astro"}
NODE_BACKEND_DEPS = {"express": "express", "fastify": "fastify", "koa": "koa", "@nestjs/core": "nestjs",
                     "@hapi/hapi": "hapi", "hono": "hono", "@adonisjs/core": "adonis"}
NODE_TEST_DEPS = {"vitest": "vitest", "jest": "jest", "mocha": "mocha", "@playwright/test": "playwright",
                  "cypress": "cypress", "ava": "ava"}
BUNDLER_DEPS = ("vite", "webpack", "parcel", "esbuild", "rollup", "laravel-mix")
CI_FILES = [".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile", "bitbucket-pipelines.yml", ".drone.yml",
            ".woodpecker.yml", ".travis.yml", "bitrise.yml", "cloudbuild.yaml"]
ENV_EXAMPLES = [".env.example", ".env.sample", ".env.template", ".env.dist"]
DB_IMAGES = ("postgres", "mysql", "mariadb", "mongo", "sqlserver", "mssql", "oracle", "cockroach", "clickhouse")


# --------------------------------------------------------------------------- facts
def _dep_version(text, name):
    m = re.search(rf"(?im)(?:^|[\s\"',\[]){re.escape(name)}(?![\w-])\s*(?:[=<>~!^]=?\s*|=\s*[\"'])\s*([^\s\"',\]]+)", text)
    return m.group(1) if m else "present"


def _has_dep(text, name):
    return re.search(_pydep(re.escape(name)), text) is not None


def _joined(paths):
    return "\n".join(read(p) for p in paths)


def _node_facts(root, paths):
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}}
    for p in paths:
        try:
            data = json.loads(read(p))
        except ValueError:
            continue
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for dep, name in FRONTEND_DEPS.items():
            if dep in deps:
                out["frameworks"][name] = deps[dep]
                if name not in out["frontend"]:
                    out["frontend"].append(name)
        for dep, name in NODE_BACKEND_DEPS.items():
            if dep in deps:
                out["frameworks"][name] = deps[dep]
                out["backend"].append(name)
        out["tests"] += [n for d, n in NODE_TEST_DEPS.items() if d in deps and n not in out["tests"]]
        if "typescript" in deps:
            out["typescript"] = True
        out["bundler"] = out.get("bundler") or next((b for b in BUNDLER_DEPS if b in deps), None)
        out["scripts"] += [s for s in sorted(data.get("scripts", {})) if s not in out["scripts"]]
        node = data.get("engines", {}).get("node")
        if node:
            out["runtime"]["node"] = node
    return out


def _php_facts(root, paths):
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}, "orm": []}
    names = {"laravel/framework": "laravel", "symfony/framework-bundle": "symfony", "symfony/symfony": "symfony",
             "slim/slim": "slim", "cakephp/cakephp": "cakephp", "codeigniter4/framework": "codeigniter", "yiisoft/yii2": "yii"}
    for p in paths:
        try:
            data = json.loads(read(p))
        except ValueError:
            continue
        req = {**data.get("require", {}), **data.get("require-dev", {})}
        for pkg, name in names.items():
            if pkg in req:
                out["frameworks"][name] = req[pkg]
                out["backend"].append(name)
        if "laravel/framework" in req:
            out["orm"].append("eloquent")
        if "inertiajs/inertia-laravel" in req:
            out["frameworks"]["inertia"] = req["inertiajs/inertia-laravel"]
        out["tests"] += [n for pkg, n in (("pestphp/pest", "pest"), ("phpunit/phpunit", "phpunit")) if pkg in req]
        out["scripts"] += sorted(data.get("scripts", {}))
        if data.get("require", {}).get("php"):
            out["runtime"]["php"] = data["require"]["php"]
    return out


def _python_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}, "orm": []}
    for dep in ("django", "fastapi", "flask", "starlette", "sanic", "aiohttp", "tornado", "pyramid", "litestar"):
        if _has_dep(text, dep):
            out["frameworks"][dep] = _dep_version(text, dep)
            out["backend"].append(dep)
    if "django" in out["frameworks"]:
        out["orm"].append("django-orm")
    if _has_dep(text, "sqlalchemy"):
        out["orm"].append("sqlalchemy")
    out["tests"] += [n for n in ("pytest", "nose2") if _has_dep(text, n)]
    m = re.search(r"requires-python\s*=\s*[\"']([^\"']+)", text)
    if m:
        out["runtime"]["python"] = m.group(1)
    return out


def _go_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": ["testing"], "scripts": [], "runtime": {}}
    for mod, name in (("gin-gonic/gin", "gin"), ("labstack/echo", "echo"), ("gofiber/fiber", "fiber"),
                      ("go-chi/chi", "chi"), ("gorilla/mux", "gorilla-mux")):
        if mod in text:
            out["frameworks"][name] = "present"
            out["backend"].append(name)
    m = re.search(r"(?m)^go\s+(\S+)", text)
    if m:
        out["runtime"]["go"] = m.group(1)
    return out


def _ruby_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}, "orm": []}
    for gem in ("rails", "sinatra", "hanami", "grape"):
        m = re.search(rf"(?m)^\s*gem\s+['\"]{gem}['\"](?:\s*,\s*['\"]([^'\"]+))?", text)
        if m:
            out["frameworks"][gem] = m.group(1) or "present"
            out["backend"].append(gem)
    if "rails" in out["frameworks"]:
        out["orm"].append("activerecord")
    out["tests"] += [n for n in ("rspec", "minitest") if re.search(rf"(?m)^\s*gem\s+['\"]{n}", text)]
    m = re.search(r"(?m)^\s*ruby\s+['\"]([^'\"]+)", text)
    if m:
        out["runtime"]["ruby"] = m.group(1)
    return out


def _jvm_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}}
    for needle, name in (("org.springframework.boot", "spring-boot"), ("io.quarkus", "quarkus"),
                         ("io.micronaut", "micronaut"), ("io.ktor", "ktor")):
        if needle in text:
            out["frameworks"][name] = "present"
            out["backend"].append(name)
    out["tests"] += [n for n, k in (("junit", "junit"), ("testng", "testng"), ("kotest", "kotest")) if k in text.lower()]
    out["kotlin"] = "kotlin" in text.lower()
    return out


def _rust_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": ["cargo test"], "scripts": [], "runtime": {}}
    for crate in ("axum", "actix-web", "rocket", "warp", "poem"):
        if re.search(rf"(?m)^\s*{re.escape(crate)}\s*=", text):
            out["frameworks"][crate] = "present"
            out["backend"].append(crate)
    return out


def _dotnet_facts(root, paths):
    text = _joined(paths)
    out = {"frameworks": {}, "frontend": [], "backend": [], "tests": [], "scripts": [], "runtime": {}}
    if "Microsoft.NET.Sdk.Web" in text:
        out["frameworks"]["aspnet"] = "present"
        out["backend"].append("aspnet")
    out["tests"] += [n for n in ("xunit", "nunit", "mstest") if n in text.lower()]
    return out


_EXTRACTORS = {"node": _node_facts, "php": _php_facts, "python": _python_facts, "go": _go_facts,
               "ruby": _ruby_facts, "jvm": _jvm_facts, "rust": _rust_facts, "dotnet": _dotnet_facts}


def _guess_database(root):
    for name in ENV_EXAMPLES:
        for p in locate(root, name):
            text = read(p)
            m = re.search(r"(?m)^DB_CONNECTION=(\S+)", text)
            if m:
                return m.group(1)
            m = re.search(r"(?mi)^(?:DATABASE_URL|DB_URL|SPRING_DATASOURCE_URL)\s*=\s*[\"']?(?:jdbc:)?([a-z0-9+]+)[:]", text)
            if m:
                return m.group(1).split("+")[0]
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        for p in locate(root, name):
            m = re.search(r"(?m)^\s*image:\s*[\"']?(?:[\w./-]*/)?(" + "|".join(DB_IMAGES) + r")\b", read(p))
            if m:
                return m.group(1)
    return None


def detect_facts(root):
    """Neutral description of the project: stacks, frameworks, package managers, runtimes, database, architecture."""
    clear_cache()
    facts = {"stacks": [], "frameworks": {}, "frontend_frameworks": [], "backend_frameworks": [],
             "package_managers": [], "test_frameworks": [], "runtime": {}, "orm": [], "manifests": {}}
    dirs = {}
    for sid, prof in STACKS.items():
        paths = [p for m in prof["manifests"] for p in locate(root, m)]
        if not paths:
            continue
        facts["stacks"].append(sid)
        facts["manifests"][sid] = sorted({p.relative_to(root).as_posix() for p in paths})
        dirs[sid] = {p.parent for p in paths}
        ex = _EXTRACTORS[sid](root, paths)
        facts["frameworks"].update(ex["frameworks"])
        for key, target in (("frontend", "frontend_frameworks"), ("backend", "backend_frameworks"),
                            ("tests", "test_frameworks"), ("orm", "orm")):
            facts[target] += [x for x in ex.get(key, []) if x not in facts[target]]
        facts["runtime"].update(ex["runtime"])
        if ex.get("typescript"):
            facts["typescript"] = True
        if ex.get("bundler"):
            facts["bundler"] = ex["bundler"]
        if ex.get("kotlin"):
            facts["kotlin"] = True
        if ex["scripts"]:
            facts.setdefault("scripts", {})[sid] = ex["scripts"]
        managers = [name for name, lock in prof.get("managers", {}).items() if locate(root, lock)]
        facts["package_managers"] += [f"{sid}:{n}" for n in managers]

    facts["database"] = _guess_database(root)
    backend_dirs = set().union(*(dirs[s] for s in dirs if s != "node")) if any(s != "node" for s in dirs) else set()
    node_front_dirs = dirs.get("node", set()) if facts["frontend_frameworks"] else set()
    fullstack = [f for f in facts["frontend_frameworks"] if f in FULLSTACK_JS]
    if backend_dirs and node_front_dirs:
        if backend_dirs & node_front_dirs:
            facts["architecture_guess"] = (
                "a UI framework and a backend in one folder (check the split"
                + ("; the front end runs as a separate app)" if fullstack else "; SPA + API or server-rendered?)"))
        else:
            facts["architecture_guess"] = "monorepo/separate: backend and front end in different folders"
    elif node_front_dirs and fullstack:
        facts["architecture_guess"] = "full-stack JavaScript framework (server and UI in one app)"
    elif node_front_dirs:
        facts["architecture_guess"] = "front end only (no backend project detected)"
    elif backend_dirs:
        facts["architecture_guess"] = "backend only (no front-end framework detected)"
    return {k: v for k, v in facts.items() if v not in (None, [], {}, False) or k in ("stacks",)}


# --------------------------------------------------------------------------- project checks
def _tool_found(root, spec):
    """(found, how) for one tool spec: a config file, a config section in a manifest, or a declared dependency."""
    for name in spec["files"]:
        hit = locate(root, name)
        if hit:
            return True, name
    for manifest, pattern in spec["patterns"]:
        for p in locate(root, manifest):
            if re.search(pattern, read(p)):
                return True, f"configured in {manifest}"
    for pattern in spec["deps"]:
        for sid_manifest in {m for prof in STACKS.values() for m in prof["manifests"]}:
            for p in locate(root, sid_manifest):
                if re.search(pattern, read(p)):
                    return True, "declared in dependencies (default configuration)"
    return False, ""


def _pinned(root, prof):
    for name in prof["pins"]["files"]:
        if locate(root, name):
            return True
    for manifest, pattern in prof["pins"]["patterns"]:
        if any(re.search(pattern, read(p)) for p in locate(root, manifest)):
            return True
    return False


def _has_lock(root, prof):
    if prof["locks"] is None:
        return None  # lockfiles are not a convention in this ecosystem
    if any(locate(root, n) for n in prof["locks"]):
        return True
    for glob, pattern in prof.get("lock_patterns", []):
        if any(re.search(pattern, read(p)) for p in locate(root, glob)):
            return True
    return False


def _test_counts(root, stacks):
    counts = {sid: 0 for sid in stacks}
    patterns = {sid: re.compile(STACKS[sid]["tests"]) for sid in stacks}
    contents = {sid: STACKS[sid]["test_content"] for sid in stacks if "test_content" in STACKS[sid]}
    for p in iter_files(root):
        rel = p.relative_to(root).as_posix()
        for sid, pat in patterns.items():
            if pat.search(rel):
                counts[sid] += 1
            elif sid in contents and p.suffix == contents[sid][0] and re.search(contents[sid][1], read(p)):
                counts[sid] += 1
    return counts


_N_PLUS_ONE = [  # (fact that makes the check applicable, regex that proves a guard exists)
    ("eloquent", r"preventLazyLoading"),
    ("activerecord", r"strict_loading|\bbullet\b"),
    ("django-orm", r"nplusone|zen[_-]queries|django-seal"),
    ("sqlalchemy", r"raiseload|lazy\s*=\s*[\"']raise"),
]
_GUARD_EXTS = {".php", ".rb", ".py", ".toml", ".txt"}
_GUARD_NAMES = {"Gemfile", "Pipfile", "composer.json"}


def project_checks(root, facts):
    checks = []

    def add(cid, status, detail):
        checks.append({"id": cid, "status": status, "detail": detail})

    def exists_any(names):
        return [n for n in names if locate(root, n)]

    def check(cid, applicable, found, when_pass, when_fail, when_na="not applicable to this stack"):
        if not applicable:
            add(cid, "na", when_na)
        else:
            add(cid, "pass" if found else "fail", when_pass if found else when_fail)

    stacks = facts.get("stacks", [])

    # --- the agent guide itself
    agents = root / "AGENTS.md"
    add("agents.md", "pass" if agents.exists() else "fail", "AGENTS.md exists" if agents.exists() else "AGENTS.md not found at root")
    if agents.exists():
        ph = read(agents).count("_fill_")
        add("agents.placeholders", "pass" if ph == 0 else "fail", f"{ph} unfilled _fill_ placeholder(s)" if ph else "no placeholders")
        docs_dir = root / "docs"
        expected = ["BACKEND", "FRONTEND", "API", "DATABASE-PERFORMANCE", "SECURITY", "TESTING", "GIT", "CI-CD",
                    "REBUILD", "CODE-STANDARDS", "CODE-DOCUMENTATION"]
        missing = [e for e in expected if not (docs_dir / f"{e}.md").exists()]
        add("agents.docs", "pass" if not missing else "fail", "all docs/ present" if not missing else "docs/ missing: " + ", ".join(missing))

    # --- tooling, per detected stack
    check("tooling.editorconfig", True, exists_any([".editorconfig"]), "present", ".editorconfig not found")
    for kind, cid in (("formatter", "tooling.formatter"), ("linter", "tooling.linter"), ("static", "tooling.static-analysis")):
        parts, failed = [], []
        for sid in stacks:
            spec = STACKS[sid]["tools"].get(kind)
            if spec is None or (sid == "node" and kind == "static" and not facts.get("typescript")):
                continue
            label = STACKS[sid]["label"]
            if isinstance(spec, str):
                parts.append(f"{label}: built in ({spec})")
                continue
            found, how = _tool_found(root, spec)
            if found:
                parts.append(f"{label}: {how}")
            else:
                failed.append(f"{label}: no {kind.replace('static', 'static analysis')} configured (expected {spec['hint']})")
        if not parts and not failed:
            add(cid, "na", "not applicable to the detected stack(s)")
        else:
            add(cid, "fail" if failed else "pass", "; ".join(failed + parts))

    # --- repository hygiene
    check("repo.env-example", True, exists_any(ENV_EXAMPLES), "environment template present",
          ".env.example not found")
    check("repo.changelog", True, exists_any(["CHANGELOG.md"]), "CHANGELOG.md present", "CHANGELOG.md not found")
    locks = {sid: _has_lock(root, STACKS[sid]) for sid in stacks}
    lock_stacks = [sid for sid, v in locks.items() if v is not None]
    missing_locks = [STACKS[sid]["label"] for sid in lock_stacks if not locks[sid]]
    check("repo.lockfile", bool(lock_stacks), not missing_locks,
          "lockfile committed for " + ", ".join(STACKS[s]["label"] for s in lock_stacks),
          "no dependency lockfile committed for " + ", ".join(missing_locks))
    competing = []
    for sid in stacks:
        found = [name for name, lock in STACKS[sid].get("managers", {}).items() if locate(root, lock)]
        if len(found) > 1:
            competing.append(f"{STACKS[sid]['label']}: {', '.join(found)}")
    applicable = any("managers" in STACKS[s] and any(locate(root, l) for l in STACKS[s]["managers"].values()) for s in stacks)
    check("repo.single-lockfile", applicable, not competing, "one lockfile per ecosystem",
          "more than one package manager has a lockfile (" + "; ".join(competing) + ")")
    unpinned = [STACKS[sid]["label"] for sid in stacks if not _pinned(root, STACKS[sid])]
    check("repo.runtime-pinned", bool(stacks), not unpinned, "runtime version pinned for every stack",
          "runtime version not pinned for " + ", ".join(unpinned))

    gi = read(root / ".gitignore")
    wanted = [(".env",)] + [tuple(STACKS[sid]["ignore"]) for sid in stacks if STACKS[sid]["ignore"]]
    miss = [group[0] if len(group) == 1 else "one of " + "/".join(group) for group in wanted
            if not any(re.search(rf"^/?{re.escape(e)}/?\s*$", gi, re.M) for e in group)]
    add("repo.gitignore", "pass" if not miss else "fail",
        "important entries present" if not miss else "not yet in .gitignore: " + ", ".join(miss))

    wf_dir = root / ".github" / "workflows"
    ci = [f".github/workflows ({len(list(wf_dir.glob('*.y*ml')))} file(s))"] if wf_dir.is_dir() and list(wf_dir.glob("*.y*ml")) else []
    ci += exists_any(CI_FILES) + (["CircleCI"] if (root / ".circleci" / "config.yml").exists() else [])
    add("ci.pipeline", "pass" if ci else "fail", ", ".join(ci) if ci else "no CI configuration found")

    # --- language-specific strictness
    if facts.get("typescript"):
        strict = any(re.search(r'"strict"\s*:\s*true', read(p)) for p in locate(root, "tsconfig.json"))
        add("ts.strict", "pass" if strict else "fail", "strict: true" if strict else "strict not yet true in tsconfig.json")
    else:
        add("ts.strict", "na", "project does not use TypeScript")

    # --- tests
    frontend_app = bool(facts.get("frontend_frameworks"))
    node_is_backend = "node" in stacks and (
        not frontend_app
        or bool(set(facts.get("backend_frameworks", [])) & set(NODE_BACKEND_DEPS.values()))
        or bool(set(facts.get("frontend_frameworks", [])) & FULLSTACK_JS))
    backend_stacks = [s for s in stacks if s != "node"] + (["node"] if node_is_backend else [])
    counts = _test_counts(root, stacks) if stacks else {}
    backend_n = sum(counts.get(s, 0) for s in backend_stacks)
    frontend_n = counts.get("node", 0) if frontend_app else 0
    check("tests.backend", bool(backend_stacks), backend_n, f"{backend_n} backend test file(s)", "0 backend test file(s)",
          "no backend stack detected")
    check("tests.frontend", frontend_app, frontend_n, f"{frontend_n} frontend test file(s)", "0 frontend test file(s)",
          "no front-end framework detected")

    # --- database and API
    applicable_guards = [rx for fact, rx in _N_PLUS_ONE if fact in facts.get("orm", [])]
    guarded = False
    if applicable_guards:
        for p in iter_files(root):
            if p.suffix in _GUARD_EXTS or p.name in _GUARD_NAMES:
                text = read(p)
                if any(re.search(rx, text) for rx in applicable_guards):
                    guarded = True
                    break
    check("db.n-plus-one-guard", bool(applicable_guards), guarded,
          "the ORM's lazy-loading / N+1 guard is enabled", "the ORM's lazy-loading / N+1 guard is not used yet",
          "no ORM with a known N+1 guard detected")
    route_re = re.compile(r"(^|/)(routes?|urls?|router|endpoints?|handlers?|controllers?)([/.])", re.I)
    route_files = [p for p in iter_files(root) if route_re.search(p.relative_to(root).as_posix())]
    if route_files:
        versioned = any(re.search(r"\bv1\b", read(p)) for p in route_files) or any(
            "/v1/" in p.relative_to(root).as_posix() for p in iter_files(root))
        add("api.versioned", "pass" if versioned else "fail",
            "API routes use v1" if versioned else "API routes without a version prefix (/api/v1)")
    else:
        add("api.versioned", "na", "no route files found")
    return checks
