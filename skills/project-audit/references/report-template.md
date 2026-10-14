# Audit Report Template

Save as `docs/audit/audit-YYYY-MM-DD.md` (English filename). Use this structure exactly so reports stay uniform and can be compared between audits. Do not copy the content of the standards; just reference the file and its section. **Never write secret values.**

```markdown
# Project Audit - YYYY-MM-DD

## 1. Summary
- **Scope:** entire project / certain dimensions: <...>
- **Commit audited:** <short hash> on branch <name>
- **Reference standards:** AGENTS.md and docs/ (same commit version)
- **Overall verdict:** Healthy / Partly healthy / Messy (1-2 sentences of reasoning)

| Severity | Confirmed | Needs verification |
|---|---|---|
| Critical | 0 | 0 |
| High | 0 | 0 |
| Medium | 0 | 0 |
| Low | 0 | 0 |
| Info | 0 | 0 |

## 2. Project context
Detected facts: stack, versions, package manager, database, architecture, tooling.
AGENTS.md placeholders not yet filled in and their proposed values.

## 3. Baseline
| Check | Command | Result |
|---|---|---|
| Backend format | `<command>` | pass / N issues / cannot be run: <reason> |
| Static analysis | ... | ... |
| Backend tests | ... | ... |
| Frontend lint / typecheck / test / build | ... | ... |
| Dependency audit | ... | ... |

Metrics: number of files and lines, doc comment coverage, 10 largest files, 10 longest functions, Conventional Commits ratio.

## 4. Convention verdict per area
| Area | Verdict | Brief evidence | Strategy |
|---|---|---|---|
| Backend | Healthy / Partly healthy / Messy | ... | Keep / partial fix / rebuild |
| Frontend | ... | ... | ... |
| API | ... | ... | ... |
| Database | ... | ... | ... |
| Testing | ... | ... | ... |
| Tooling and process | ... | ... | ... |

## 5. Findings
Order from highest severity. One line per finding, details below it when needed.

| ID | Severity | Status | Dimension | Location | Standard violated | Recommendation | Effort |
|---|---|---|---|---|---|---|---|
| AF-001 | Critical | Confirmed | Security | `path/to/file.ext:42` | docs/SECURITY.md (section ...) | ... | S |

Status values: *Confirmed*, *Needs verification*, or *N/A (culture mismatch)* — the last
one when the target's own convention legitimately differs from the project standard
(name the convention instead of reporting a violation).

### AF-001 <short title>
- **Evidence:** what is visible in the code (quote just enough, without secrets).
- **Impact:** why this matters.
- **Fix:** concrete steps.

## 6. What is already good
List practices that already meet the standards, so they are maintained.

## 7. Cannot be audited / out of scope
Branch protection, production configuration, modules that were not sampled (name them), commands that cannot be run.

## 8. Adjustment plan
### Phase 0 - Critical (immediate)
- [ ] <item> | standard | effort | risk | dependencies
### Phase 1 - Foundation
- [ ] ...
### Phase 2 - Structure
- [ ] ...
### Phase 3 - Refinement
- [ ] ...

## 9. Adjustment results (filled in after fixes)
Before/after comparison per scanner rule, results of quality commands, and remaining findings.
```

Filling notes:
- **Finding status:** *Confirmed* only if the code at that location has been read and the violation is clear. Otherwise *Needs verification*. *N/A (culture mismatch)* when the target follows its own legitimate convention (state which); never use it to hide an unread location.
- **Effort:** S (less than half a day), M (1-3 days), L (more than 3 days).
- One finding = one problem. The same violation in many places is made into a single finding with a list of locations.
