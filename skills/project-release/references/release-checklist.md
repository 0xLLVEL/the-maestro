# Release Checklist and Templates

Table of contents: Readiness checklist · Deploy and rollback plan · Release notes template · Release PR description template

## Readiness checklist
Report each item as **ready**, **needs action**, or **cannot be verified** (with the reason).

**Quality**
- [ ] CI on `main` is green: all quality checks of the stack run, including the dependency audit. User confirmation or readable evidence.
- [ ] No open PRs that should be part of this release.
- [ ] Dependency audit findings are explained (fixed or accepted with a reason).

**Data and configuration**
- [ ] Migrations in the release: safe for a staged deploy (expand/contract), time estimates on large tables, and a written rollback plan.
- [ ] New or changed env variables (`.env.example`) are set in staging and production. Variables embedded in the client bundle (public, browser-visible) are set at **build** time.
- [ ] The impact of `config/` changes per environment is understood.

**Contract and compatibility**
- [ ] API changes: no breaking change without a MAJOR and migration notes. If there is one, the backward-compatible backend is deployed first.
- [ ] OpenAPI and API documentation are in sync with the code.
- [ ] Versions in the project files are in sync with the release (the dependency manifest); a manifest that does not declare a `version` field is left alone.

**Documentation**
- [ ] `CHANGELOG.md` contains the new version with a date; entries match the commits.
- [ ] Release notes are ready; the impact for users and operators is explained.

## Deploy and rollback plan
Keep it short and concrete; this is handover material for the user or the operations team (the skill does not run it).

```markdown
### Deploy vX.Y.Z
1. Staging: deploy the service, run the migrations, then deploy the client. Smoke test the main flow: <list>.
2. Production: the same order. The backward-compatible service first.
3. Health check after deploy: service <endpoint>, client <page>. Watch errors and latency for <duration>.

### Rollback
- Application: redeploy the previous release tag (vA.B.C). Tags are not deleted.
- Database: <per-migration plan: safe to leave because it is additive / reverse steps / restore from backup>.
- Criteria for deciding a rollback: <e.g. error rate > X% for Y minutes>.
```

## Release notes template
For stakeholders, in English, without commit jargon.

```markdown
# Release vX.Y.Z (YYYY-MM-DD)

## Highlights
- <the 1-3 most important changes from the user's perspective>

## Changes that need attention
- Breaking change: <what, who is affected, how to adjust>
- Database migration: <yes/no, its impact>
- New env variable: <name, no value>

## Fixes and security
- <summary of important fixes; vulnerabilities described adequately without exploit details>

## How to upgrade and roll back
See the deploy plan: <link/summary>.

Full list of changes: CHANGELOG.md
```

## Release PR description template
```markdown
## Release vX.Y.Z
**Version rationale:** <MINOR because N feat commits / etc.>
**Changelog summary:** <brief Added/Changed/Fixed>
**Risk:** <migration, env, dependency, breaking, or "none">
**Deploy and rollback plan:** <summary or link>
**How to test:** the quality commands in AGENTS.md; smoke test after the staging deploy
**After merge:** the `vX.Y.Z` tag is created by the release owner (annotated, on this `main` commit)
```
