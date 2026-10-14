# the-maestro

A small, opinionated kit that keeps AI coding agents disciplined: one **guide** (`AGENTS.md` plus twelve short standards
documents) and five **skills** that turn it into a workflow: write a PRD, build from it, audit the result, refactor what the
audit found, and prepare a release.

It does not generate code by itself. It tells an agent *how* to work in your repository, and ships scripts that check the
agent's work (and your repository) against the same rules.

## What is inside

```
template/            copy into your project
  AGENTS.md          entry point for any agent: principles, workflow, pace rules, definition of done
  docs/              standards: code, documentation, backend, frontend, API, database, security, testing, Git, CI/CD, rebuild
skills/              the five skills (each is a folder with a SKILL.md)
  project-prd/       write a short, executable PRD (no code)
  project-build/     build from an approved PRD, phase by phase, on its own branch
  project-audit/     read-only audit of a project against the standards, then a fix plan
  project-refactor/  apply an approved audit plan in small, tested commits
  project-release/   prepare version, changelog, and release PR (never tags or deploys on its own)
tools/check_kit.py   keeps this repository consistent (see Development)
```

The standards belong to **your project**, not to the skills: every skill reads `AGENTS.md` and `docs/` first.

## Quick start

1. **Copy the guide into your project.** Copy `template/AGENTS.md` and `template/docs/` to the root of your repository.
2. **Install the skills.** Copy the folders in `skills/` to your agent's skills directory (for example `.claude/skills/` in your
   project, or `~/.claude/skills/` for Claude Code).
3. **Start the agent.** The "Project Context" section of `AGENTS.md` is blank on purpose (`_fill_`). On the first run the agent
   detects your stack from the manifests in your repository, fills it in, and asks you one question only if something cannot
   be detected.

Typical flow: *"write a PRD for ..."* then *"build it"* then *"audit the project"* then *"apply the audit plan"* then *"prepare a release"*.

## The audit scanner

`skills/project-audit/scripts/scan.py` is a read-only, standard-library-only scanner. It reports **heuristics**, not verdicts:
every finding must be confirmed by reading the code.

```bash
python skills/project-audit/scripts/scan.py <project-root> --json audit-scan.json
```

| Option | Meaning |
|---|---|
| `--max-file-lines N`, `--max-func-lines N` | size thresholds (defaults 300 and 50) |
| `--max-per-rule N` | how many examples to list per rule |
| `--style-checks` | also report opinionated `design.slop-*` style heuristics (off by default) |
| `--lang-pack id,es,...` | which non-English language(s) to flag in code and comments: `id`, `es`, `pt`, `fr`, `de`, a JSON file, or `none` (default `id`) |

It recognises **PHP, Node/TypeScript** (React, Vue, Svelte, Angular, Next, Nuxt, ...), **Python, Go, Ruby, Java/Kotlin, Rust,
and .NET**, including several in one repository. Per stack it checks the tooling that belongs there (formatter, linter, static
analysis, lockfile, runtime pin, `.gitignore`, tests, CI) and applies the detector rules that make sense for that language.
Language packs are small JSON files in `skills/project-audit/scripts/langpacks/`; adding a language needs no code.

## Development

```bash
python tools/check_kit.py            # consistency checks
python tools/check_kit.py --tests    # ... plus every self-test of the skills
```

`check_kit.py` verifies, among other things, that the template contains no stack-specific API names, that every rule id cited in
the documentation really exists in the scanner, that duplicated files are identical, and that `VERSION`, `CHANGELOG.md`, the
template's version marker, and the skills' front matter agree. CI runs it on Linux, Windows, and macOS (Python 3.9 and 3.12).
Everything uses the Python standard library only.

## Status and limitations

- The scripts were developed and tested on Linux with Python 3.12; CI covers the other platforms and versions.
- The scanner has been exercised on generated projects for each stack and on a corpus of real source files, not yet on large
  real-world repositories, so expect false positives from the newer rules and report them.
- The skills are instructions for an agent. Their scripts are tested; the agent's behaviour when following them is not
  covered by automated tests (the `evals/` folders describe behavioural checks that need an agent to run them).
- The Spanish, Portuguese, French, and German language packs are starting points; add or remove words for your team.

## Versioning

[Semantic Versioning](https://semver.org); see [CHANGELOG.md](CHANGELOG.md). The first line of `template/AGENTS.md` carries the
kit version, so a project can tell which version of the guide it copied.

## License

Not specified yet. Until a `LICENSE` file is added, all rights are reserved by the author.
