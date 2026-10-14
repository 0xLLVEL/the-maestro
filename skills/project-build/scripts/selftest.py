#!/usr/bin/env python3
"""Self-test for prd_tasks.py using evals/files/example-prd.md and throwaway fixtures.

Run:  python selftest.py        (exit code 0 = all passed)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prd_tasks.py"
PRD = ROOT / "evals" / "files" / "example-prd.md"
FAILS = []


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail[:300]}"))
    if not cond:
        FAILS.append(name)


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


# plan
code, out = run("plan", str(PRD), "--phase", "1")
check("plan exits 0", code == 0, out)
check("plan lists tasks of phase 1", "## Phase 1" in out and "### Task 1" in out, out)
check("plan includes ACs, endpoint, screen and tests", all(x in out for x in ("AC-F001-1", "API-001", "SCR-001", "T-001")), out)
check("plan warns about Draft status", "PRD status is still Draft" in out, out)
check("plan lists open questions", "Q-001" in out, out)
j = Path(tempfile.mkdtemp(), "plan.json")
run("plan", str(PRD), "--json", str(j))
data = json.loads(j.read_text())
check("plan --json has phases and tasks", data["phases"] and data["phases"][0]["tasks"], str(data)[:200])
code, out = run("plan", str(PRD), "--phase", "99")
check("plan unknown phase exits non-zero", code != 0)

# verify: empty project -> MISS
empty = tempfile.mkdtemp()
code, out = run("verify", str(PRD), "--root", empty, "--phase", "1")
check("verify on empty project exits 1", code == 1, out)
check("verify reports missing route/design/tests/reference", "[MISS] API-001" in out and "[MISS] SCR-001.design" in out and "[MISS] T-001" in out and "[MISS] ref.file" in out, out)

# verify: populated project -> OK (a stack-neutral fixture: one route file, one view, one test)
p = Path(tempfile.mkdtemp())
(p / "routes").mkdir()
(p / "routes" / "api.js").write_text("const r = require('express').Router();\nr.post('/orders/:order/cancel', cancel);\nmodule.exports = r;\n")
(p / "pages" / "orders").mkdir(parents=True)
(p / "pages" / "orders" / "[order].jsx").write_text("export default function Page(){return null}")
(p / "docs" / "design" / "screens").mkdir(parents=True)
(p / "docs" / "design" / "screens" / "order-detail.md").write_text("x")
(p / "tests").mkdir()
(p / "tests" / "cancel-order.test.js").write_text("it('cancels a pending order');\n")
(p / "src" / "services").mkdir(parents=True)
(p / "src" / "services" / "CancelOrderService.js").write_text("export function cancelOrder() {}\n")
(p / "docs" / "prd-reference").mkdir()
REF_TEXT = (
    "## Acceptance criteria\n| AC | Test file | Test name | Code |\n|---|---|---|---|\n"
    "| AC-F001-1 | `tests/cancel-order.test.js` | `cancels a pending order` | `src/services/CancelOrderService.js::cancelOrder` |\n\n"
    "## Test scenarios\n| Scenario | Test file | Test name |\n|---|---|---|\n"
    "| T-001 | `tests/cancel-order.test.js` | `cancels a pending order` |\n"
)
ref_file = p / "docs" / "prd-reference" / "example-prd.md"
ref_file.write_text(REF_TEXT)
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1", "--ac-table")
check("verify finds route", "[OK  ] API-001" in out, out)
check("verify finds the front-end page ([order] segment)", "[OK  ] SCR-001.page" in out, out)
check("verify finds T-001 and AC-F001-1 via the reference index", "[OK  ] T-001" in out and "[OK  ] AC-F001-1" in out and "[OK  ] ref.file" in out, out)
check("verify reports no PRD IDs in code", "[OK  ] code.prd-ref" in out, out)
check("verify flags AC missing from the index as manual check", "[?   ] AC-F001-2" in out, out)
check("verify prints AC table", "| AC-F001-1 | F-001 |" in out and "connected" in out, out)
# reference points to a missing test name / symbol -> MISS
ref_file.write_text(REF_TEXT.replace("::cancelOrder", "::missingMethod"))
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1")
check("verify blocks when the index points to a missing symbol", "[MISS] AC-F001-1" in out and "missingMethod" in out and code == 1, out)
ref_file.write_text(REF_TEXT.replace("`cancels a pending order` |", "`renamed test` |"))
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1")
check("verify blocks when the index points to a missing test name", "[MISS] T-001" in out and "test name not found" in out, out)
ref_file.write_text(REF_TEXT)
# PRD ID leaked into code -> MISS
(p / "src" / "leak.js").write_text("// Implements AC-F001-1 from the PRD\n")
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1")
check("verify blocks PRD IDs in code", "[MISS] code.prd-ref" in out and "src/leak.js:1" in out and code == 1, out)
(p / "src" / "leak.js").unlink()
(p / "routes" / "api.js").write_text("const r = require('express').Router();\nr.resource('orders', controller);\nmodule.exports = r;\n")
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1")
check("resource route needs manual check", "[?   ] API-001" in out and "route list" in out, out)

# plan: compact output + progress status
code, out = run("plan", str(PRD), "--phase", "1")
check("plan prints each AC text once (compact)", out.count("Given my order is `pending`") == 1, out)
check("plan lists AC IDs per task", "- AC: AC-F001-1, AC-F001-2, AC-F001-3, AC-F001-4" in out, out)
pg = Path(tempfile.mkdtemp(), "progress.md")
pg.write_text("| Task | Feature | Status |\n|---|---|---|\n| Migration for the cancellation columns | F-001 | done |\n")
code, out = run("plan", str(PRD), "--phase", "1", "--progress", str(pg))
check("plan shows task status from progress file", "Migration for the cancellation columns [S] (migration) -> done" in out and "Progress summary" in out, out)

# preflight
g = tempfile.mkdtemp()
sh(g, "git", "init", "-q", "-b", "main")
sh(g, "git", "config", "user.email", "t@t.t")
sh(g, "git", "config", "user.name", "t")
Path(g, "AGENTS.md").write_text("# Agent\n")
sh(g, "git", "add", "-A")
sh(g, "git", "commit", "-qm", "init")
code, out = run("preflight", str(PRD), "--root", g, "--check-prd", "/nonexistent/check_prd.py")
check("preflight treats main as an action item (the branch is created in Step 1), not a blocker", code == 0 and "[?   ] git.branch" in out, out)
check("preflight flags greenfield repo (no dependency manifest)", "[?   ] project.scaffold" in out and "Phase 0" in out, out)
sh(g, "git", "checkout", "-qb", "feature/order-cancellation")
code, out = run("preflight", str(PRD), "--root", g, "--check-prd", "/nonexistent/check_prd.py")
check("preflight passes on clean work branch (manual items remain)", code == 0 and "[OK  ] git.branch" in out and "[?   ] prd.status" in out, out)
Path(g, "x.txt").write_text("dirty")
code, out = run("preflight", str(PRD), "--root", g, "--check-prd", "/nonexistent/check_prd.py")
check("preflight blocks on dirty tree", code == 1 and "[MISS] git.clean" in out, out)
Path(g, "x.txt").unlink()
(Path(g) / "docs" / "build").mkdir(parents=True)
(Path(g) / "docs" / "build" / "order-cancellation.md").write_text("| PRD | docs/prd/order-cancellation.md (version 0.0) |\n")
sh(g, "git", "add", "-A")
sh(g, "git", "commit", "-qm", "progress")
code, out = run("preflight", str(PRD), "--root", g, "--check-prd", "/nonexistent/check_prd.py")
(Path(g) / "pyproject.toml").write_text("[project]\nname = \"demo\"\n")
sh(g, "git", "add", "-A")
sh(g, "git", "commit", "-qm", "scaffold")
code, out = run("preflight", str(PRD), "--root", g, "--check-prd", "/nonexistent/check_prd.py")
check("preflight recognizes a project scaffold of any stack", "[OK  ] project.scaffold" in out, out)
check("preflight detects PRD version drift", "build.prd-drift" in out and "v0.0" in out, out)


# --- fast file index: dependency folders are never scanned (PRD IDs inside them are not "leaks")
(p / "node_modules" / "dep").mkdir(parents=True)
(p / "node_modules" / "dep" / "index.js").write_text("// F-001 AC-F001-1 inside a dependency\n")
(p / "vendor" / "pkg").mkdir(parents=True)
(p / "vendor" / "pkg" / "a.js").write_text("// F-001\n")
code, out = run("verify", str(PRD), "--root", str(p), "--phase", "1")
check("verify ignores node_modules and vendor", "[OK  ] code.prd-ref" in out, out)

# --- scaffold: pre-fills every ID, never overwrites, and unfilled rows are MISS in verify
sc = Path(tempfile.mkdtemp())
code, out = run("scaffold", str(PRD), "--root", str(sc), "--phase", "1")
ref_text = (sc / "docs" / "prd-reference" / "example-prd.md").read_text()
check("scaffold creates the index with AC, scenario, endpoint and screen rows",
      code == 0 and all(x in ref_text for x in ("| AC-F001-1 |", "| AC-F002-1 |", "| T-001 |", "| API-001 |", "| SCR-001 |")), ref_text)
check("scaffold phase 1 leaves out phase 2 ids", "AC-F004-1" not in ref_text and "SCR-002" not in ref_text, ref_text)
(sc / "docs" / "prd-reference" / "example-prd.md").write_text(ref_text + "\nKEEP\n")
code, out = run("scaffold", str(PRD), "--root", str(sc))
check("scaffold does not overwrite an existing index", "already exists" in out and "KEEP" in (sc / "docs" / "prd-reference" / "example-prd.md").read_text(), out)
code, out = run("verify", str(PRD), "--root", str(sc), "--phase", "1")
check("verify marks unfilled scaffold rows as MISS", "[MISS] AC-F001-1" in out and "columns are empty" in out, out)

# --- preflight design check is scoped to the phase being built; start = preflight + plan
CHECKER = ROOT.parent / "project-prd" / "scripts" / "check_prd.py"
if CHECKER.exists():
    Path(g, "docs", "design", "screens").mkdir(parents=True, exist_ok=True)
    Path(g, "docs", "design", "screens", "order-detail.md").write_text("x")
    sh(g, "git", "add", "-A")
    sh(g, "git", "commit", "-qm", "design")
    code, out = run("preflight", str(PRD), "--root", g, "--phase", "1", "--check-prd", str(CHECKER))
    check("preflight --phase 1 does not require phase 2 design files", "[OK  ] prd.check" in out, out)
    code, out = run("preflight", str(PRD), "--root", g, "--check-prd", str(CHECKER))
    check("preflight without --phase requires every design file", "[MISS] prd.check" in out and code == 1, out)
    code, out = run("start", str(PRD), "--root", g, "--phase", "1", "--check-prd", str(CHECKER))
    check("start prints preflight and plan in one call", "Preflight build" in out and "# Build plan" in out and "## Phase 1" in out, out)
    code, out = run("start", str(PRD), "--root", g, "--check-prd", str(CHECKER))
    check("start withholds the plan when preflight blocks", code == 1 and "# Build plan" not in out, out)
else:
    print("SKIP preflight design-scope tests (project-prd not installed next to project-build)")

# --- the route, test, and migration conventions of other stacks are understood too
sys.path.insert(0, str(ROOT / "scripts"))
import prd_tasks  # noqa: E402


def stack_fixture(files):
    d = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        f = d / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return d


def routes_of(files):
    prd_tasks._FILE_INDEX.clear()
    routes, resources = prd_tasks.collect_routes(stack_fixture(files))
    return {(m, pth) for m, pth, _ in routes}, [r for r, _ in resources]


r, _ = routes_of({"routes.go": "package main\nfunc main() {\n  r.GET(\"/orders/:id/cancel\", cancel)\n  http.HandleFunc(\"/health\", h)\n}\n"})
check("routes: Go (gin-style verbs and HandleFunc)", ("GET", "/orders/{}/cancel") in r and ("ANY", "/health") in r, str(r))
r, _ = routes_of({"src/main/java/app/OrderController.java": "class OrderController {\n  @PostMapping(\"/orders/{id}/cancel\")\n  void cancel() {}\n}\n"})
check("routes: Spring annotations in a *Controller file", ("POST", "/orders/{}/cancel") in r, str(r))
r, res = routes_of({"config/routes.rb": "Rails.application.routes.draw do\n  post '/orders/:id/cancel', to: 'orders#cancel'\n  resources :invoices\nend\n"})
check("routes: Rails routes.rb (verb routes and resources)", ("POST", "/orders/{}/cancel") in r and "invoices" in res, f"{r} {res}")
r, _ = routes_of({"Controllers/OrdersController.cs": "class OrdersController {\n  [HttpPost(\"orders/{id}/cancel\")]\n  public void Cancel() {}\n}\n"})
check("routes: ASP.NET attributes", ("POST", "/orders/{}/cancel") in r, str(r))
r, _ = routes_of({"app/urls.py": "urlpatterns = [\n    path('orders/<int:id>/cancel/', views.cancel),\n]\n",
                  "app/routers/payments.py": "@app.post('/payments/{pid}/refund')\ndef refund(pid): ...\n"})
check("routes: Django path() and FastAPI decorators", ("ANY", "/orders/{}/cancel") in r and ("POST", "/payments/{}/refund") in r, str(r))

tests = prd_tasks.collect_test_files(stack_fixture({
    "tests/test_orders.py": "def test_cancel(): pass\n", "pkg/order_test.go": "package pkg\n",
    "src/test/java/OrderTest.java": "class OrderTest {}\n", "spec/order_spec.rb": "describe 'x' do end\n",
    "tests/OrderTest.php": "<?php\n", "App.Tests/OrderTests.cs": "class OrderTests {}\n", "src/order.py": "x = 1\n"}))
check("tests: Python, Go, Java, Ruby, PHP, and C# test files are found, source files are not",
      len(tests) == 6 and "src/order.py" not in tests, str(sorted(tests)))

mg = stack_fixture({"db/migrate/20240101_add_status.rb": "add_column :orders, :cancel_reason, :string\n",
                    "docs/prd.md": "unused"})
check("migrations: db/migrate (Rails) is recognised", bool(prd_tasks.MIGRATION_DIR_RE.search("db/migrate/20240101_add_status.rb")
      and prd_tasks.MIGRATION_DIR_RE.search("app/migrations/0001_initial.py") and prd_tasks.MIGRATION_DIR_RE.search("alembic/versions/ab12.py")
      and not prd_tasks.MIGRATION_DIR_RE.search("src/orders.py")), "")
code, out = run("verify", str(PRD), "--root", str(mg))
check("verify without --phase no longer crashes (whole-PRD checks)", code in (0, 1) and "Traceback" not in out, out)

print(f"\n{'ALL PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
