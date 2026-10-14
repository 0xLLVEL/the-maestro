# Context Question Bank

## Rules
1. **Read first, ask later.** Do not ask about anything already in `AGENTS.md`, `docs/`, or the code (stack, versions, architecture, API conventions, code language).
2. **One batch, 4-6 questions** (a maximum of 8 for an A-Z product). Only questions whose answers change scope, flows, data, security, or UI; the rest are decided by default and recorded as Assumptions.
3. **Every question has 2-4 options and one marked recommendation**, so answering "follow the recommendation" or an option number is enough.
4. **Tools:** options through the available interactive question tool (`ask_user_input_v0`, `AskUserQuestion`); open questions as a numbered list in the text. Without a tool: everything as a numbered list with lettered options.
5. **A two-sentence introduction** that shows understanding of the request, followed by the questions. After that, **stop and wait**.
6. **Gate:** do not write the PRD until it has been answered, unless the user says "proceed with assumptions" or "your call" (use the defaults, record every decision as A-###).
7. **One round is enough.** A second round (2-4 questions) only if the answers open a large gap (e.g. "there is payment"). The rest become A-### or Q-###.

## Core questions (pick the relevant ones)
1. **Goal** (open): what problem does it solve, and what is the sign of success?
2. **Roles:** one role, several roles with different rights, or the public without login? (recommendation: state every role and its rights)
3. **MVP scope:** what must be in the first release, what may follow? (recommendation: only what is needed to reach the goal)
4. **Data and integrations:** where does the data come from (input / existing system / third party / import)? Are exports or integrations needed?
5. **Business rules** (open): constraints, statuses, or special calculations that must be obeyed?
6. **Scale and sensitive data:** estimated number of users/data; is there personal data? (recommendation: small-to-medium scale, personal data per `docs/SECURITY.md`)
7. **UI language:** Indonesian / English / both? (recommendation: one language first, text through translation files)

## Conditional (only if the request touches them)
| Topic | Question |
|---|---|
| Payment | Provider, refund, invoice, tax, compliance? |
| Authentication | Self-signup or invitation; social login, email verification, MFA? |
| Multi-tenant | One organization or many with separated data? |
| Notification | Email, push, or in-app; who receives it and when? |
| Files | Type and maximum size; who may access them? |
| Search and reporting | Search, filter, export, dashboard; how realtime? |
| Public pages | Need SEO or a preview when shared (determines what is rendered on the server)? |
| Realtime | Need live updates (chat, status, collaboration)? |
| Legacy data | Is there data that must be migrated? |
| Audit | Need a trail of who changed what and when? |

## Using the answers
Important decisions go into Section 1 of the PRD; those decided by default become A-### in Section 9 (complete with the impact if wrong); those that limit scope go into "Out of scope" in Section 2; answers about screens (which pages exist, on which devices) go into the screen table in Section 5.
