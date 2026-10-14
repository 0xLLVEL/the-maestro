#!/usr/bin/env python3
"""Self-test for the scanner: builds small throwaway projects for several stacks and checks
that facts, project checks, and detectors behave the same way for each of them.

Run: python selftest.py        (standard library only; exit code 1 on any failure)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAILED = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILED.append(name)


def write(root, rel, text=""):
    p = Path(root, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def scan(root):
    out = Path(root, "_scan.json")
    r = subprocess.run([sys.executable, str(HERE / "scan.py"), str(root), "--json", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None, None, None, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    out.unlink()
    return data["facts"], {c["id"]: c["status"] for c in data["project_checks"]}, data["rules"], ""


def long_python_function(n=60):
    return "def big(x):\n" + "".join(f"    x = x + {i}\n" for i in range(n)) + "    return x\n"


def fixture_laravel_next(d):
    write(d, "composer.json", json.dumps({"require": {"php": "^8.2", "laravel/framework": "^11.0", "laravel/pint": "^1.0"},
                                          "require-dev": {"larastan/larastan": "^2.0", "pestphp/pest": "^2.0"}}))
    write(d, "composer.lock", "{}")
    write(d, "pint.json", "{}")
    write(d, "phpstan.neon", "")
    write(d, ".env.example", "DB_CONNECTION=mysql\n")
    write(d, "app/Http/Controllers/OrderController.php",
          "<?php\nclass OrderController {\n  function a() { Order::where('a', 1); }\n  function b() { Order::create([]); }\n  function c() { $o->save(); }\n}\n")
    write(d, "tests/Feature/OrderTest.php", "<?php\n")
    write(d, "web/package.json", json.dumps({"dependencies": {"next": "15.0.0", "react": "19.0.0"},
                                              "devDependencies": {"typescript": "5.0.0", "vitest": "1.0.0", "eslint": "9.0.0", "prettier": "3.0.0"},
                                              "engines": {"node": ">=20"}}))
    write(d, "web/package-lock.json", "{}")
    write(d, "web/tsconfig.json", '{"compilerOptions": {"strict": true}}')
    write(d, "web/eslint.config.mjs", "export default []")
    write(d, "web/src/Card.test.tsx", "export {}\n")


def fixture_django(d):
    write(d, "pyproject.toml", '[project]\nrequires-python = ">=3.11"\ndependencies = ["django>=5.0", "pytest"]\n\n[tool.ruff]\nline-length = 100\n')
    write(d, "uv.lock", "")
    write(d, ".python-version", "3.12\n")
    write(d, "shop/views.py",
          "def a(r):\n    return Order.objects.filter(a=1)\n\ndef b(r):\n    return Order.objects.get(id=1)\n\ndef c(r):\n    return Order.objects.create(a=1)\n")
    write(d, "shop/util.py", "import json\nimport subprocess\n\n" + long_python_function() +
          "\ndef run(cmd):\n    subprocess.run(cmd, shell=True)\n    json.dump({}, open('x', 'w'))\n")
    write(d, "tests/test_views.py", "def test_a():\n    assert True\n")


def fixture_go(d):
    write(d, "go.mod", "module example.com/app\n\ngo 1.22\n\nrequire github.com/gin-gonic/gin v1.9.0\n")
    write(d, "go.sum", "")
    write(d, "main.go", "package main\n\nfunc main() {\n\tq := fmt.Sprintf(\"SELECT * FROM users WHERE id = %s\", id)\n\t_ = q\n}\n")
    write(d, "handlers/user.go",
          "package handlers\n\nfunc A() { db.Query(\"x\") }\nfunc B() { db.Exec(\"y\") }\nfunc C() { db.QueryRow(\"z\") }\n")
    write(d, "handlers/user_test.go", "package handlers\n")


def fixture_rails(d, guard=False):
    write(d, "Gemfile", "source 'https://rubygems.org'\nruby '3.3.0'\ngem 'rails', '~> 7.1'\ngem 'rubocop'\ngem 'rspec-rails'\n")
    write(d, "Gemfile.lock", "")
    write(d, ".rubocop.yml", "")
    write(d, "app/controllers/users_controller.rb",
          "class UsersController\n  def index\n    User.where(a: 1)\n    User.find_by(id: 1)\n    User.create!(a: 1)\n  end\nend\n")
    write(d, "spec/users_spec.rb", "RSpec.describe 'x' do\nend\n")
    if guard:
        write(d, "config/environments/development.rb", "config.active_record.strict_loading_by_default = true\n")


def fixture_spring(d):
    write(d, "pom.xml", "<project><properties><java.version>21</java.version></properties>"
                        "<parent><groupId>org.springframework.boot</groupId></parent>"
                        "<dependency>junit-jupiter</dependency><plugin>maven-checkstyle-plugin</plugin></project>")
    write(d, "src/main/java/app/UserController.java", "package app;\nclass UserController {\n}\n")
    write(d, "src/test/java/app/UserControllerTest.java", "package app;\nclass UserControllerTest {\n}\n")


def fixture_express(d):
    write(d, "package.json", json.dumps({"dependencies": {"express": "4.19.0"}, "devDependencies": {"jest": "29.0.0"}}))
    write(d, "yarn.lock", "")
    write(d, "pnpm-lock.yaml", "")
    write(d, "src/app.test.js", "test('x', () => {})\n")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        d = base / "laravel_next"; d.mkdir(); fixture_laravel_next(d)
        facts, checks, rules, err = scan(d)
        check("laravel+next: scan runs", facts is not None, err)
        if facts:
            check("laravel+next: stacks", set(facts["stacks"]) == {"php", "node"}, facts["stacks"])
            check("laravel+next: frameworks", {"laravel", "next", "react"} <= set(facts.get("frameworks", {})), facts.get("frameworks", {}))
            check("laravel+next: frontend framework list", "next" in facts.get("frontend_frameworks", []), facts.get("frontend_frameworks"))
            check("laravel+next: database from .env.example", facts.get("database") == "mysql", facts.get("database"))
            check("laravel+next: separate folders", "different folders" in facts.get("architecture_guess", ""), facts.get("architecture_guess"))
            check("laravel+next: formatter + static analysis found", checks["tooling.formatter"] == "pass" and checks["tooling.static-analysis"] == "pass", checks)
            check("laravel+next: lazy-loading guard missing", checks["db.n-plus-one-guard"] == "fail", checks.get("db.n-plus-one-guard"))
            check("laravel+next: typescript strict", checks["ts.strict"] == "pass", checks.get("ts.strict"))
            check("laravel+next: both test suites found", checks["tests.backend"] == "pass" and checks["tests.frontend"] == "pass", checks)
            check("laravel+next: controller data access", "layer.handler-data-access" in rules, list(rules))

        d = base / "django"; d.mkdir(); fixture_django(d)
        facts, checks, rules, err = scan(d)
        check("django: scan runs", facts is not None, err)
        if facts:
            check("django: stack and framework", facts["stacks"] == ["python"] and "django" in facts.get("frameworks", {}), facts)
            check("django: runtime version", facts.get("runtime", {}).get("python") == ">=3.11", facts.get("runtime", {}))
            check("django: package manager", "python:uv" in facts.get("package_managers", []), facts.get("package_managers", []))
            check("django: ruff counts as formatter and linter", checks["tooling.formatter"] == "pass" and checks["tooling.linter"] == "pass", checks)
            check("django: no type checker configured", checks["tooling.static-analysis"] == "fail", checks["tooling.static-analysis"])
            check("django: runtime pinned, lockfile present", checks["repo.runtime-pinned"] == "pass" and checks["repo.lockfile"] == "pass", checks)
            check("django: typescript checks not applicable", checks["ts.strict"] == "na" and checks["tests.frontend"] == "na", checks)
            check("django: tests found", checks["tests.backend"] == "pass", checks["tests.backend"])
            check("django: n+1 guard missing", checks["db.n-plus-one-guard"] == "fail", checks["db.n-plus-one-guard"])
            check("django: long python function", "generic.long-function" in rules, list(rules))
            check("django: shell=True flagged", "python.shell-true" in rules, list(rules))
            check("django: json.dump is not a debug call", "debug.leftover" not in rules, rules.get("debug.leftover"))
            check("django: view data access", "layer.handler-data-access" in rules, list(rules))

        d = base / "go"; d.mkdir(); fixture_go(d)
        facts, checks, rules, err = scan(d)
        check("go: scan runs", facts is not None, err)
        if facts:
            check("go: stack, framework, runtime", facts["stacks"] == ["go"] and "gin" in facts.get("frameworks", {}) and facts.get("runtime", {}).get("go") == "1.22", facts)
            check("go: built-in tooling counts", checks["tooling.formatter"] == "pass" and checks["tooling.linter"] == "pass", checks)
            check("go: Sprintf SQL flagged", "sql.string-built" in rules, list(rules))
            check("go: handler data access", "layer.handler-data-access" in rules, list(rules))
            check("go: tests found", checks["tests.backend"] == "pass", checks["tests.backend"])

        d = base / "rails"; d.mkdir(); fixture_rails(d)
        facts, checks, rules, err = scan(d)
        check("rails: scan runs (ruby unit rules do not crash)", facts is not None, err)
        if facts:
            check("rails: facts", facts["stacks"] == ["ruby"] and "rails" in facts.get("frameworks", {}) and "activerecord" in facts.get("orm", []), facts)
            check("rails: rubocop found, runtime pinned", checks["tooling.linter"] == "pass" and checks["repo.runtime-pinned"] == "pass", checks)
            check("rails: strict loading missing", checks["db.n-plus-one-guard"] == "fail", checks["db.n-plus-one-guard"])
            check("rails: controller data access", "layer.handler-data-access" in rules, list(rules))
        fixture_rails(d, guard=True)
        facts, checks, rules, err = scan(d)
        check("rails: strict loading found", facts is not None and checks["db.n-plus-one-guard"] == "pass", checks)

        d = base / "spring"; d.mkdir(); fixture_spring(d)
        facts, checks, rules, err = scan(d)
        check("spring: scan runs", facts is not None, err)
        if facts:
            check("spring: facts", facts["stacks"] == ["jvm"] and "spring-boot" in facts.get("frameworks", {}), facts)
            check("spring: checkstyle + java version", checks["tooling.linter"] == "pass" and checks["repo.runtime-pinned"] == "pass", checks)
            check("spring: lockfile is not a convention here", checks["repo.lockfile"] == "na", checks["repo.lockfile"])
            check("spring: tests found", checks["tests.backend"] == "pass", checks["tests.backend"])

        d = base / "express"; d.mkdir(); fixture_express(d)
        facts, checks, rules, err = scan(d)
        check("express: scan runs", facts is not None, err)
        if facts:
            check("express: backend framework, no frontend", facts.get("backend_frameworks", []) == ["express"] and "frontend_frameworks" not in facts, facts)
            check("express: competing lockfiles flagged", checks["repo.single-lockfile"] == "fail", checks["repo.single-lockfile"])
            check("express: node tests count as backend", checks["tests.backend"] == "pass" and checks["tests.frontend"] == "na", checks)

        d = base / "empty"; d.mkdir()
        facts, checks, rules, err = scan(d)
        check("empty project: scan runs and stays neutral", facts is not None and facts["stacks"] == [], err or facts)
        if facts:
            check("empty project: stack checks are not applicable",
                  all(checks[c] == "na" for c in ("tooling.formatter", "repo.lockfile", "repo.runtime-pinned", "tests.backend", "tests.frontend")), checks)

        d = base / "style"; d.mkdir()
        write(d, "package.json", json.dumps({"dependencies": {"vue": "3.4.0"}}))
        write(d, "src/App.vue", "<template><div v-html=\"raw\"></div></template>\n<script>\nconst k = import.meta.env.VITE_API_SECRET\n</script>\n")
        facts, checks, rules, err = scan(d)
        check("vue: scan runs", facts is not None, err)
        if facts:
            check("vue: raw HTML and public secret flagged", {"frontend.raw-html", "frontend.public-env-secret"} <= set(rules), list(rules))
            check("vue: front end only", "front end only" in facts.get("architecture_guess", ""), facts.get("architecture_guess"))

    # --- language packs: the non-English checks follow the pack, not a hard-coded language
    def lang_fixture(root):
        write(root, "src/orders.py",
              "# elimina el pedido cuando el cliente cancela porque no puede pagar\n"
              "def borrar_pedido(pedido_id):\n    return pedido_id\n\n"
              "# hapus pesanan untuk pengguna dengan harga\n"
              "def hapus_pesanan(id_pesanan):\n    return id_pesanan\n")

    def lang_rules(root, *flags):
        out = Path(root, "_l.json")
        r = subprocess.run([sys.executable, str(HERE / "scan.py"), str(root), "--json", str(out), *flags], capture_output=True, text=True, encoding="utf-8", errors="replace")
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
        out.unlink(missing_ok=True)
        return r, data

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp); lang_fixture(d)
        r, data = lang_rules(d)
        names = {n for n in data.get("rules", {})}
        check("lang pack: default (Indonesian) flags Indonesian identifiers, not Spanish ones",
              "lang.non-english-identifier" in names and "pedido" not in json.dumps(data["rules"]["lang.non-english-identifier"]), str(names))
        r, data = lang_rules(d, "--lang-pack", "es")
        hits = json.dumps(data.get("rules", {}).get("lang.non-english-identifier", {}))
        check("lang pack: --lang-pack es flags Spanish identifiers (pedido) and Spanish comments",
              "pedido" in hits and "lang.non-english-comment" in data.get("rules", {}), hits)
        r, data = lang_rules(d, "--lang-pack", "id,es")
        check("lang pack: several packs combine", {"pedido", "pesanan"} <= {w.strip() for w in json.dumps(data["rules"]["lang.non-english-identifier"]).replace('"', ' ').replace(",", " ").split()}, "")
        r, data = lang_rules(d, "--lang-pack", "none")
        check("lang pack: none switches the language checks off", not any(k.startswith("lang.") for k in data.get("rules", {})) and data.get("lang_packs") == [], str(data.get("lang_packs")))
        custom = Path(tmp, "team.json")
        custom.write_text(json.dumps({"language": "Team", "identifier_words": ["borrar"], "stopwords": []}), encoding="utf-8")
        r, data = lang_rules(d, "--lang-pack", str(custom))
        check("lang pack: a custom JSON file works", "borrar" in json.dumps(data.get("rules", {}).get("lang.non-english-identifier", {})) and data["lang_packs"] == ["Team"], str(data.get("lang_packs")))
        r, data = lang_rules(d, "--lang-pack", "klingon")
        check("lang pack: an unknown pack stops with a helpful message", r.returncode != 0 and "Shipped packs" in (r.stdout + r.stderr), r.stderr[-200:])

    packs_ok = True
    for pack in sorted((HERE / "langpacks").glob("*.json")):
        data = json.loads(pack.read_text(encoding="utf-8"))
        clash = {w for w in data["identifier_words"] + data["stopwords"] if w in {"the", "and", "data", "cargo", "color", "total", "name", "type", "message", "page", "image", "number", "title", "description"}}
        if not data.get("language") or not data["identifier_words"] or not data["stopwords"] or clash:
            packs_ok = False
            print("      bad pack:", pack.name, clash)
    check("lang pack: every shipped pack is well formed and avoids common English words", packs_ok, "")

    # --- the speed optimisations must not change a single result
    sys.path.insert(0, str(HERE))
    import detectors as d
    import re as _re

    def reference_findings(rel, ext, lines, is_test, stop, ids, in_lang, secret_patterns, secret_skip):
        """The straightforward per-line implementation: every rule on every line, no gating, no prefilter."""
        orig_strip = _re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
        for i, raw in enumerate(lines, 1):
            s = raw.strip()
            if not s:
                continue
            commented = d.is_comment(s, ext)
            code_line = orig_strip.sub('""', raw)
            for rid, exts, pat, cond, flags, detail in d.LINE_RULES:
                if (exts is not None and ext not in exts) or pat is None or not d._flags_ok(flags, rel, is_test):
                    continue
                if (cond == "code" and commented) or (cond == "comment" and not commented):
                    continue
                if pat.search(raw if "raw" in flags else code_line):
                    yield rid, rel, i, detail
            for rid, exts, first, second, cond, flags in d._PAIR_LINE:
                if (exts is not None and ext not in exts) or not d._flags_ok(flags, rel, is_test):
                    continue
                if cond == "code" and commented:
                    continue
                hay = raw if "raw" in flags else code_line
                if first.search(hay) and second.search(hay):
                    yield rid, rel, i, None
            for rid, exts, cond, kind, guard in d._WORD_LINE:
                if (exts is not None and ext not in exts) or ("not_lang_dir" in guard and in_lang) or ("not_style" in guard and ext in d.STYLE_EXTS):
                    continue
                if (cond == "comment" and not commented) or (cond == "code" and commented):
                    continue
                if kind == "stopword":
                    if len(set(d.words(raw)) & stop) >= 2:
                        yield rid, rel, i, None
                else:
                    toks = {tk for ident in _re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code_line.replace("$", " ")) for tk in d.ident_tokens(ident)}
                    hit = toks & ids
                    if hit:
                        yield rid, rel, i, ", ".join(sorted(hit)[:3])
            if not commented:
                for sp in secret_patterns:
                    if sp.search(raw) and not secret_skip.search(raw):
                        yield "secret.possible", rel, i, "value masked"
                        break

    stop = {"yang", "untuk", "dengan", "tidak", "dari", "sudah", "akan", "pada"}
    ids = {"hapus", "tambah", "pengguna", "pesanan", "harga", "keranjang"}
    corpus = sorted(HERE.parent.parent.rglob("*.py")) + sorted(Path(_re.__file__).parent.parent.glob("*.py"))[:150]
    for ext in (".js", ".ts", ".tsx", ".php", ".rb", ".go"):
        corpus += sorted(Path("/usr/lib/node_modules").rglob("*" + ext))[:25] if Path("/usr/lib/node_modules").exists() else []
    snippets = {
        "a.py": "import pickle\nx = eval(s)\npickle.loads(b)\njson.dump(o, f)\nprint(f\"SELECT * FROM t WHERE id = {x}\")\n# hapus pesanan untuk pengguna dengan harga\nkeranjang_baru = 1\n",
        "b.ts": "const k = process.env.NEXT_PUBLIC_API_TOKEN\nel.innerHTML = x\nlocalStorage.setItem(\"token\", t)\nconsole.log(a as any)\n// @ts-ignore\n",
        "c.rb": "User.where(\"a = #{x}\")\nbyebug\nENV[\"KEY\"]\n",
        "d.php": "<?php\ndd($x);\n$y = $request->all();\nDB::raw(\"select * from t where a = $a\");\n",
    }
    mismatches, files, total_findings = [], 0, 0
    for rel, text in [(str(c), c.read_text(encoding="utf-8", errors="ignore")) for c in corpus] + list(snippets.items()):
        ext = Path(rel).suffix
        lines = text.splitlines()
        for is_test in (False, True):
            want = sorted(set(reference_findings(rel, ext, lines, is_test, stop, ids, False, d.SECRET_PATTERNS, d.SECRET_SKIP)))
            got = sorted(set(d.iter_line_findings(rel, ext, lines, is_test, stop, ids, False, d.SECRET_PATTERNS, d.SECRET_SKIP)))
            d.PREFILTER = False
            got_plain = sorted(set(d.iter_line_findings(rel, ext, lines, is_test, stop, ids, False, d.SECRET_PATTERNS, d.SECRET_SKIP)))
            d.PREFILTER = True
            total_findings += len(want)
            if want != got or want != got_plain:
                mismatches.append((rel, is_test, sorted(set(want) ^ set(got))[:3]))
        files += 1
    check(f"line rules: optimised == reference on {files} files (prefilter on and off)", not mismatches, str(mismatches[:3]))
    check("the comparison is not vacuous (many findings compared)", total_findings > 200, str(total_findings))
    check("string stripping is unchanged", all(d.strip_strings(s) == _re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`', '""', s)
          for s in ["a = 'x' + \"y\"", "plain line", "f(`t ${x}`)", "it\'s", ""]), "")

    print("\nFAILED: " + ", ".join(FAILED) if FAILED else "\nALL PASSED")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
