# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com), and versions follow [Semantic Versioning](https://semver.org).

## [0.1.0] - 2026-10-14

First public release.

### Added
- Five skills that form one workflow: `project-prd`, `project-build`, `project-audit`, `project-refactor`, `project-release`.
- `template/`: an `AGENTS.md` and twelve standards documents (`docs/`) to copy into a project. The "Project Context"
  section is left blank on purpose; the agent fills it from the project's own manifests on the first run.
- A stack-neutral audit scanner (`skills/project-audit/scripts`): PHP, Node/TypeScript (React, Vue, Svelte, Angular,
  Next, Nuxt, ...), Python, Go, Ruby, Java/Kotlin, Rust, and .NET, including several in one repository.
- Language packs (`--lang-pack`) for the "code must be in English" checks: `id`, `es`, `pt`, `fr`, `de`, or your own JSON file.
- Self-tests for the audit, build, and release scripts, and `tools/check_kit.py` to keep the kit consistent.
- GitHub Actions workflow running the checks on Linux, Windows, and macOS.

### Decisions worth knowing
- File headers carry `@author` (name only) and `@ai`. There is no `@version` (it goes stale) and no email (code is
  often public).
- Style heuristics (`design.slop-*`) are off by default; enable them with `--style-checks`.
- The scanner reports heuristics, not verdicts: every finding must be confirmed by reading the code.

### Fixed (relative to the pre-release archive)
- `prd_tasks.py verify` crashed without `--phase` (`KeyError: 'teknis'`).
- Ruby doc-comment rules crashed on the first Ruby file; doc-comment coverage always read 0%.
- `json.dump(` / `yaml.dump(` were reported as leftover debug calls; PHP and Rust attributes were treated as comments.
- SQL-injection detection flagged ordinary English strings such as `f"Could not update {name}"`.
- Django `<int:id>` route parameters were normalised incorrectly.
- Skills searched for `_isi_` while the scripts counted `_fill_`; leftover Indonesian labels (`Esensial`, `Opsional`) made
  `check_prd.py` reject valid PRDs.
- `compare_scans.py` read a metric the scanner never wrote.
