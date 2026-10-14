#!/usr/bin/env python3
"""Builds a throwaway repo for project-build evals (one example stack, no framework assumed).

Usage: python make_fixture.py <target-dir> [options]

Options:
  --empty              no dependency manifest (greenfield, expects Phase 0 bootstrap)
  --no-design          do not create docs/design files (check_prd.py will report errors)
  --approved           set the PRD Status to "Approved"
  --bad-endpoint       PRD endpoint without /api/v1 (violates docs/API.md)
  --with-progress      add docs/build/order-cancellation.md recording an older PRD version (resume + drift)
  --agents-docs PATH   copy AGENTS.md and docs/ from this folder (the real standards) instead of a stub
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = Path(sys.argv[1]).resolve()
    args = sys.argv[2:]
    d.mkdir(parents=True, exist_ok=True)
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "eval@example.com")
    sh(d, "git", "config", "user.name", "eval")

    if "--agents-docs" in args:
        src = Path(args[args.index("--agents-docs") + 1])
        shutil.copy(src / "AGENTS.md", d / "AGENTS.md")
        if (src / "docs").is_dir():
            shutil.copytree(src / "docs", d / "docs", dirs_exist_ok=True)
    else:
        (d / "AGENTS.md").write_text("# Agent Guide (fixture)\n\nFollow the principles: YAGNI, tests first, business logic in the backend, no pushing to main, no creating tags.\n", encoding="utf-8")

    if "--empty" not in args:
        (d / "package.json").write_text('{"name":"shop","version":"1.0.0","scripts":{"dev":"node server.js","build":"echo no build step","test":"node --test tests/"}}', encoding="utf-8")
        (d / "server.js").write_text("require('./routes/api');\n", encoding="utf-8")
        (d / "routes").mkdir(exist_ok=True)
        (d / "routes" / "api.js").write_text("const r = require('express').Router();\nmodule.exports = r;\n", encoding="utf-8")
        (d / "pages").mkdir(parents=True, exist_ok=True)
        (d / "pages" / "index.jsx").write_text("export default function Home() { return null; }\n", encoding="utf-8")

    prd = (HERE / "files" / "example-prd.md").read_text(encoding="utf-8")
    if "--approved" in args:
        prd = prd.replace("| Status | Draft |", "| Status | Approved |")
    if "--bad-endpoint" in args:
        prd = prd.replace("/api/v1/orders/{order}/cancel", "/orders/{order}/cancel")
    (d / "docs" / "prd").mkdir(parents=True, exist_ok=True)
    (d / "docs" / "prd" / "order-cancellation.md").write_text(prd, encoding="utf-8")

    if "--no-design" not in args:
        screens = d / "docs" / "design" / "screens"
        screens.mkdir(parents=True, exist_ok=True)
        for slug in ("order-detail", "admin-cancellation-log"):
            (screens / f"{slug}.md").write_text(f"# Screen: {slug} (fixture)\n", encoding="utf-8")

    if "--with-progress" in args:
        (d / "docs" / "build").mkdir(parents=True, exist_ok=True)
        (d / "docs" / "build" / "order-cancellation.md").write_text(
            "# Build: Order Cancellation\n\n| Field | Value |\n|---|---|\n| PRD | docs/prd/order-cancellation.md (version 0.0) |\n| Active phase | 1 |\n\n## Tasks\n| Task | Feature | Status |\n|---|---|---|\n| Migration for the cancellation columns | F-001 | done |\n", encoding="utf-8")

    sh(d, "git", "add", "-A")
    sh(d, "git", "commit", "-qm", "chore: initial commit")
    print(f"Fixture ready at {d}")


if __name__ == "__main__":
    main()
