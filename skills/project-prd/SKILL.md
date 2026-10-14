---
name: project-prd
description: Writes a concise and executable PRD (Product Requirements Document) for a project, aligned with the AGENTS.md and docs/ standards, including the design files it derives. The agent asks the user for context first (one batch), then determines the essential features from the request. Use this skill each time the user asks for write a PRD, create a PRD, product requirements, feature specification, requirements document, full plan of a feature or application, design a feature before it is built, or explains a new feature/product idea and wants it planned first, even if the user does not mention the word PRD. English triggers include write a PRD, product requirements, feature spec, and plan this feature end to end.
---

# Project PRD

Writing a PRD that is **concise and executable**: a user request becomes a feature catalog, acceptance criteria (AC), design, technical specification, additional tests, and a phase plan, aligned with `AGENTS.md` and `docs/`. This skill only writes planning documents and design files; **it does not write application code**.

**The standards belong to the project.** If `references/` in this skill differs from the project docs, the project docs win. The PRD **does not copy** the content of the standards; just reference it.

## Principles
1. **Ask first, write later**, in one batch (Step 2).
2. **Essentials first (YAGNI).** Features come from the request. Things not requested but needed for the feature to work (login, validation, error state, access rights) are marked **Implicit essential** so they can be rejected. No "nice to have" feature counts as essential.
3. **Dense.** One sentence per item; no personas, glossary, metrics, user stories, traceability tables, or DoD unless requested (full rules in `references/prd-template.md`). A long PRD slows the build and increases the chance of conflicts between sections.
4. **ACs are tests.** Each AC is one measurable Given/when/then line; every Essential feature has an AC.
5. **Reuse before creating something new (DRY):** check the code and the existing components before defining a new model, endpoint, or component.
6. **Honest.** What is not yet known becomes an **Assumption (A-###)** or an **Open Question (Q-###)**. Brand, target numbers, and business rules must not be invented without being marked.

## Flow

### Step 1: Quick reconnaissance (read-only, one reading pass)
- Read `AGENTS.md`, `docs/QUICK-RULES.md`, and the list of `docs/prd/` (avoid duplication, keep IDs consistent). Open the standards files only for the areas this PRD touches (the pace rules are in `AGENTS.md` § 3).
- Explore the code enough for the related feature, model, route, and component. `project-audit/scripts/scan.py` provides stack facts quickly if it is installed.
- If `AGENTS.md` does not exist, say so and offer to create it first.

### Step 2: Ask for context (required, one batch)
Follow `references/questions.md`: **4-6 questions** with default recommendations, only those that change the content of the PRD. Include one combined design question if there is UI. After sending, **stop and wait**. The user says "proceed with assumptions": use the defaults and record them as A-###.

### Step 3: Write the PRD
Use `references/prd-template.md` (structure, density rules, ID scheme) and see `references/example-prd.md`. Save it in `docs/prd/<feature-slug>.md`. Build the feature catalog first (F-001..., priority, origin, phase, out of scope); test each Essential: if it were dropped, would the user's goal still be met? If yes, downgrade it.

Align with the standards without copying them: API per `docs/API.md` (`/api/v1`, plural, kebab-case); data per `docs/DATABASE-PERFORMANCE.md`; layers per `docs/BACKEND.md` and `docs/FRONTEND.md`; security per `docs/SECURITY.md`; identifiers and translation keys in English. Split phase tasks to the size of one build cycle and merge similar small tasks (e.g. migration + model + factory as one).

### Step 4: Check (once)
```bash
python scripts/check_prd.py docs/prd/<feature-slug>.md --trace
```
Fix all `[ERROR]`, consider `[WARN]`. The checker evaluates structure, ID consistency, scope, and size, not the quality of the idea. Review quickly: Essential ACs are measurable; edge cases and access rights are covered; there are no invented values without A-###.

### Step 5: Submit and ask for approval
In chat (in the user's language), **a 5-8 line summary**: goal, feature count per priority, key decisions, main assumptions, open questions, file location. Do not paste the PRD. End with **one** question: is it correct, or is there anything to change before the screen files are created?

### Step 6: Screen files (after the PRD is approved)
Screen files are the only design artifact. Write them in one batch:
1. `docs/design/screens/<slug>.md` for each `SCR-###`, **only the relevant parts**: the layout, the components to reuse or create, and the states.
2. Verify:
   ```bash
   python scripts/check_prd.py docs/prd/<feature-slug>.md --root . --require-design-files
   ```
   Fix all `[ERROR]`, consider `[WARN]`.
Screen documents only; do not write UI code.

### Step 7: Implementation
Do not start automatically. After the PRD is approved, suggest the `project-build` skill per phase (Section 8 of the PRD).

## Updating an existing PRD
Update `docs/prd/<slug>.md`, do not create a duplicate. Raise the Versi and Status, keep the IDs already in use (do not renumber them), add new IDs at the end.

## Response format
The conversation with the user follows the user's own language; the PRD file is in **English**; identifiers, slugs, endpoints, columns, JSON keys, file names, and translation keys in **English**.

## Common mistakes
- Writing a PRD before the questions are answered, or asking about things that are in `AGENTS.md`, `docs/`, or the code.
- A bloated PRD: repeating the standards, personas, glossary, user stories, manual traceability (a source of conflicts between sections).
- Unmeasurable ACs; an Essential feature without ACs; a feature without the Phase column.
- Reading all of `docs/` at the start; two layout alternatives for every screen.
- Inventing brand, numbers, or business rules without A-###; writing code or starting a build without approval.
- Creating a new PRD instead of updating the existing one.
