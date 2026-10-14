# In-Code Documentation

> Part of the agent guide. The summary and core rules are in [`AGENTS.md`](../AGENTS.md).
> Conversation with the user follows the user's own language (`AGENTS.md` § 4); only what is written into files is in English.
> All comments and doc comments are written in **English** (docs/CODE-STANDARDS.md).

## Comments are only about code

**A comment explains the code. Nothing else belongs in it.** Comments inside code may **contain three things only**. Anything else is prohibited.

| Allowed | Description |
|---|---|
| 1. Code explanation | What a unit does and what it is for (doc comment), as well as **why** the code is written that way (inline comment) |
| 2. Author | The author's name from `git config`, not made up by the agent (`@author` tag) |
| 3. AI used | The model and tool that wrote the code (`@ai` tag) |

Points 2-3 are **file metadata** (the "File metadata" section below). Point 1 is everyday comment content.

**Prohibited in comments, doc comments, test names, and any string in code:**
- References to a **PRD**: IDs (`F-###`, `US-###`, `AC-F###-n`, `SCR-###`, `API-###`, `T-###`, `A-###`, `Q-###`, `R-###`), PRD name or path, phrases such as "according to the PRD" or "requirement from the client", as well as build phase or task numbers.
- References to other process documents: audit reports and their finding IDs, deviation IDs, progress files, links to `docs/`, issue or PR numbers (`#123`).
- `TODO`, `FIXME`, `HACK`, `XXX`. Unfinished work is recorded in the issue tracker or a progress file, not in code.
- Change history ("changed X on 2026-10-01", "previously used Y"). Git already stores it.
- Conversations with the user or another agent ("as requested", "per the discussion"), names of people other than in the `@author` tag, and commented-out code.

The reason: comments explain **what code does and what it is used for**. Planning documents change and can be deleted; comments pointing to them become stale or wrong. Traceability from requirements to code is recorded in a **separate index**, called the **PRD-code index** (see the "PRD references to code" section below).

## Two kinds of comments

| Kind | Purpose | Mandatory? |
|---|---|---|
| **Doc comment** (PHPDoc / TSDoc / JSDoc) | Explains the **contract**: what a unit does, its parameters, its result, and possible errors | **Mandatory** for public APIs (listed below) |
| **Inline comment** (`//`) | Explains **why**: decisions, workarounds, limitations, tricky logic | As needed |

## Must have a doc comment

**Backend**
- Every type the language lets you document (class, interface, trait, enum, struct, protocol, and the like), at least a one-sentence summary.
- Every method or function that is part of the public or protected surface.
- Use-case / service classes, jobs, event handlers, authorization policies, response serializers, and input validation objects.
- Handler methods: a docblock explaining the endpoint (read by the OpenAPI generator if the one in use supports it).
- Private methods only if their logic is not clear from the name.

**Frontend**
- Exported components (along with props that are not self-explanatory), custom hooks, and exported utility functions.
- Complex types or interfaces, as well as context or store providers.
- Exported server endpoints (route handlers, server-side functions, server actions): the input/output contract, errors, and side effects, because all of them are public endpoints.

**Others:** configuration and constants whose purpose is not clear.

**Not mandatory:** trivial getters/setters, override methods that do not change the contract (just `{@inheritDoc}`), small local components inside a file, and tests (the test name already explains it).

## Content of a good doc comment

- **First line**: a one-sentence summary, starting with a third-person verb ("Cancels ...", "Returns ...", "Renders ..."), ending with a period.
- **Additional description** (optional, only when needed): business rules, prerequisites, side effects, and limitations. At most 1-3 short lines, written as facts about the code, never as the origin of the rule.
- **`@param`**: explain the meaning and value constraints, not just repeating the type. Use the doc-comment format of the language (for example `@param name - Description` in TypeScript, `:param name:` in a Python docstring, `@param name Description` in Javadoc/KDoc/PHPDoc); where the language already types the parameter, do not repeat the type in the text.
- **`@return` / `@returns`**: explain what is returned when it is not clear from the name and signature.
- **`@throws`**: every error deliberately raised to the caller, along with its condition.
- **`@example`**: for utilities, hooks, or reusable components whose usage is not obvious.
- **`@deprecated`** (name the alternative and its version) and `@see` where relevant (`@see` only to another code symbol, not to a document).
- **Richer types** than the language's native types may be written in the doc comment so static analysis can check them (`array<int, Order>`, `list<string>`, `positive-int`). Do not rewrite native types that are already clear.

## Short and dense

- **One sentence** is enough for a summary. Stop as soon as there is nothing left to add beyond the name and the signature.
- **Write only what the code cannot say by itself.** A comment that repeats the line below it is deleted, not rewritten.
- **No padding.** No "This function is responsible for ...", no "as can be seen", no restating the type inside `@param`.
- A doc comment that only repeats the name is a signal: the unit is trivial (leave it out, see the exceptions above) or its name needs fixing.
- Inline comments: **1-2 lines at most**, and only for a reason that is not obvious (workaround, race condition, formula, technical limitation).
- An empty doc comment carries no information and counts as a finding, the same as a missing one.

## File metadata

Every code file that is **created** by the agent has one header comment block at the top of the file, containing a one-sentence file summary and two metadata tags. Use the file-level documentation slot of the language:

| Language | Where the header goes |
|---|---|
| PHP | The docblock of the main class/interface/trait/enum (or the first docblock after the strict-types declaration if there is no class) |
| TypeScript / JavaScript / Vue / Svelte | The first block comment in the file, before the imports |
| Python | The module docstring |
| Go | The comment block directly above the `package` clause |
| Java / Kotlin / C# | The doc comment of the main type |
| Ruby | The leading comment block at the top of the file |
| Rust | The `//!` module documentation at the top of the file |

The scanner only looks for the two tags in the first 60 lines of the file.

```
@author  Budi Santoso
@ai      Claude Sonnet 5.5 (Claude Code)
```

| Tag | Content | How to fill it in |
|---|---|---|
| `@author` | The author's name (no email) | `git config user.name`. If empty, **stop and ask the user to set it**; do not make it up, and do not use the agent's name |
| `@ai` | The model and tool used to write the code | The actual model and tool used in this session. If unsure, ask the user; do not guess model names or version numbers |

There is deliberately no `@version` tag and no email. The agent does not bump versions (docs/GIT.md), so a version in the header would go stale, and Git tags and history already record when a file changed and by whom. Code is often published, so an email address does not belong in it.

Rules:
- Fill in the header when the file is written (not as a separate step). Take `git config user.name` **once per session**, then reuse it.
- Tags go only in the file header. Doc comments for methods, functions, and components do not carry metadata.
- When changing an existing file, leave its header alone. Only if the changing author or AI differs from the one recorded, **add** a new `@author` / `@ai` line; do not delete the old one.
- A file without a header gets one only when it is rewritten wholesale (the rebuild procedure in docs/REBUILD.md); small edits never add or change headers.
- Not mandatory for tool-generated files (generated), configuration files, lockfiles, and files in `vendor/` or `node_modules/`.
- The `@ai` tag is not a standard tag for every tool. If a doc linter flags unknown tags (for example `eslint-plugin-tsdoc`, Checkstyle's Javadoc checks, or a docstring linter), register `@ai` as a custom tag so it does not show up as a warning.

## PRD references to code

This section is the **single source of truth** for the index; other documents call it the **PRD-code index**.

Code does not reference a PRD. Instead, the **PRD references the code**, through a separate index:

- Location: `docs/prd-reference/<slug>.md` (English filename, `<slug>` identical to the PRD slug). Format and example: `references/prd-reference-template.md` in the `project-build` skill.
- Content: a table mapping PRD IDs (features, acceptance criteria, test scenarios, endpoints, screens) to **file paths, test names, and symbol names** (`path/to/file::symbol`, for example `src/orders/cancel_order.py::cancel_order`). No line numbers, because they go stale quickly.
- Created by the `project-build` skill **once at phase close** (scaffold from `prd_tasks.py scaffold`), then updated in the same commit if a referenced file, test, or symbol is renamed. Check with `prd_tasks.py verify`.
- Test names explain behavior (`it('rejects cancelling a paid order')`), without PRD IDs.

## Example

PHP:
```php
<?php

declare(strict_types=1);

namespace App\Actions\Order;

/**
 * Cancels a pending order and releases its reserved stock.
 *
 * Only orders in the "pending" status can be cancelled. The operation runs
 * inside a database transaction so the order status and stock stay consistent.
 *
 * @author  Budi Santoso
 * @ai      Claude Sonnet 5.5 (Claude Code)
 */
final class CancelOrderAction
{
    public function __construct(
        private readonly StockReservationService $stockReservations,
    ) {}

    /**
     * @param  Order  $order  The order to cancel.
     * @param  string|null  $reason  Optional free-text reason stored on the order.
     *
     * @throws OrderNotCancellableException If the order is not in the "pending" status.
     */
    public function execute(Order $order, ?string $reason = null): Order
    {
        // The status is checked inside the transaction to avoid a race with the payment webhook.
        // ...
    }
}
```

TypeScript (file header, then function doc comment):
```ts
/**
 * Hook that loads the paginated order list for the order screens.
 *
 * @author  Budi Santoso
 * @ai      Claude Sonnet 5.5 (Claude Code)
 */
import { useQuery } from '@tanstack/react-query';

/**
 * Fetches a paginated list of orders and keeps it in sync with the server.
 *
 * @param filters - Query filters sent to the API (`status`, `page`, `per_page`).
 * @returns The query state: `orders`, loading and error flags, and pagination meta.
 *
 * @example
 * const { orders, isLoading } = useOrders({ status: 'pending' });
 */
export function useOrders(filters: OrderFilters) {
  // ...
}
```

Python (module docstring, then function docstring):
```python
"""Cancels pending orders and releases their reserved stock.

@author  Budi Santoso
@ai      Claude Sonnet 5.5 (Claude Code)
"""


def cancel_order(order: Order, reason: str | None = None) -> Order:
    """Cancels a pending order and releases its reserved stock.

    :param order: The order to cancel.
    :param reason: Optional free-text reason stored on the order.
    :raises OrderNotCancellableError: If the order is not in the "pending" status.
    """
    # The status is checked inside the transaction to avoid a race with the payment webhook.
    ...
```

Go (package comment, then exported function comment):
```go
// Package orders handles the order lifecycle.
//
// @author  Budi Santoso
// @ai      Claude Sonnet 5.5 (Claude Code)
package orders

// CancelOrder cancels a pending order and releases its reserved stock.
// It returns ErrNotCancellable if the order is not in the "pending" status.
func CancelOrder(ctx context.Context, id OrderID, reason string) error {
	// The status is checked inside the transaction to avoid a race with the payment webhook.
	// ...
}
```

The same rules apply to the other languages in the table above: file summary plus the two tags in the file-level slot, and a one-sentence contract on every public unit.

## Inline comments
- Explain **why**, not what, and only when the reason is not obvious (workaround, race condition, formula, technical limitation). One or two lines.
- Clear code does not need a comment that translates it.
- Explain with code terms and its behavior (conditions, technical limitations, race condition, formula, workaround), not by pointing at a document or a request. Behavioral rules may be written as facts about the code ("Only pending orders can be cancelled."), without naming where the rule comes from.
- Tool-instruction comments (for example `@phpstan-ignore`, `eslint-disable-next-line`, `@ts-expect-error`, `# noqa`, `# type: ignore`, `//nolint`, `@SuppressWarnings`) may be used with a short technical reason on the same line. The ignored rule name must be specific.
- No `TODO`/`FIXME`/`HACK`/`XXX` (see the "Comments are only about code" section).
- Do not leave commented-out code behind. Git already stores its history.
- A comment that does not match the code is a bug. Update or delete it when the code changes.

## Old code and changes
- When adding or changing a unit, add or update the doc comment for **that unit** in the same change. A behavior change without updating the doc comment means the work is not finished.
- In old files containing PRD references, TODOs, or comments outside the three allowed things, clean up **the files you touch** and move still-useful PRD references to the PRD-code index.
- In old files without doc comments, complete only the units you touch. Do not add doc comments in bulk to areas outside the scope (exception: the rebuild procedure in docs/REBUILD.md).

## Enforcement
- Review (human) checks the completeness **and quality** of doc comments: no PRD references, no references to other documents, no TODOs, no comments outside the three allowed things, and **no comment that repeats what the name and signature already say**.
- `project-audit` scans PRD ID references, `TODO`/`FIXME`, and headers without metadata (`comment.*`). `prd_tasks.py verify` blocks PRD ID references in code.
- Static analysis reads the types written in docblocks. On the frontend, a doc-comment lint plugin can be used **if the project already uses it**. Do not add new tooling without approval (YAGNI).
- If the OpenAPI generator in use reads docblocks (for example an annotation-driven OpenAPI tool), the controller doc comment becomes public API documentation, so write it carefully.
