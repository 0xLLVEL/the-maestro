#!/usr/bin/env python3
"""Compare two scan.py JSON outputs (before / after) and print a Markdown delta.

Usage:
    python compare_scans.py before.json after.json

Both files come from project-audit's scripts/scan.py (--json). Read-only,
standard library only. Rule counts are heuristic; use them as a progress
indicator, not as proof of correctness.
"""
import json
import sys

SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if len(sys.argv) != 3:
        sys.exit("Usage: compare_scans.py before.json after.json")
    before, after = load(sys.argv[1]), load(sys.argv[2])

    rows = []
    for rule in set(before["rules"]) | set(after["rules"]):
        rb, ra = before["rules"].get(rule, {}), after["rules"].get(rule, {})
        meta = ra or rb
        cb, ca = rb.get("count", 0), ra.get("count", 0)
        rows.append((SEV[meta["severity"]], rule, meta["severity"], cb, ca, ca - cb, meta["description"]))
    rows.sort()

    print("## Scanner findings comparison\n")
    print("| Severity | Rule | Before | After | Delta | Description |")
    print("|---|---|---:|---:|---:|---|")
    for _, rule, sev, cb, ca, d, desc in rows:
        print(f"| {sev} | `{rule}` | {cb} | {ca} | {d:+d} | {desc} |")
    if not rows:
        print("| - | (no findings) | 0 | 0 | 0 | |")

    tb = sum(r[3] for r in rows)
    ta = sum(r[4] for r in rows)
    print(f"\n**Total heuristic findings:** {tb} -> {ta} ({ta - tb:+d})")

    regress = [r for r in rows if r[5] > 0]
    if regress:
        print("\n### Regressions (findings added)")
        for _, rule, sev, cb, ca, d, _ in regress:
            print(f"- `{rule}` ({sev}): {cb} -> {ca}. Check whether this was caused by a recent change.")
    else:
        print("\nNo rules increased.")

    cb_ = {c["id"]: c for c in before.get("project_checks", [])}
    ca_ = {c["id"]: c for c in after.get("project_checks", [])}
    changed = [(i, cb_.get(i, {}).get("status", "-"), ca_.get(i, {}).get("status", "-"))
               for i in sorted(set(cb_) | set(ca_)) if cb_.get(i, {}).get("status") != ca_.get(i, {}).get("status")]
    print("\n### Project check changes")
    if changed:
        for i, s1, s2 in changed:
            print(f"- `{i}`: {s1} -> {s2}")
    else:
        print("No changes.")

    mb, ma = before.get("metrics", {}), after.get("metrics", {})
    print("\n### Metrics")
    print(f"- Lines of code: {mb.get('loc')} -> {ma.get('loc')}")
    db, da = mb.get("doc_comment", {}), ma.get("doc_comment", {})
    if db.get("coverage") is not None or da.get("coverage") is not None:
        print(f"- Doc comments: {db.get('coverage')} -> {da.get('coverage')}")
    gb, ga = before.get("git", {}), after.get("git", {})
    if gb.get("conventional_commits_ratio") is not None or ga.get("conventional_commits_ratio") is not None:
        print(f"- Conventional Commits ratio: {gb.get('conventional_commits_ratio')} -> {ga.get('conventional_commits_ratio')}")


if __name__ == "__main__":
    main()
