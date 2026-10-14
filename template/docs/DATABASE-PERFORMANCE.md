# Database and Performance

> Part of the agent guide. The summary and core rules are in [`AGENTS.md`](../AGENTS.md).

## Database
- Naming: `snake_case` plural tables (`order_items`), `snake_case` columns, `<singular>_id` foreign keys, pivot tables singular and alphabetically ordered (`order_product`).
- Use **foreign key constraints** with explicit `onDelete`, an **index** on FK columns as well as columns that are frequently filtered/sorted, and **unique constraints at the database level** (validation alone is not enough).
- Choose the correct data type. Money uses `decimal` or integer, not float.
- **Migrations safe for production**:
  - Prefer *additive* changes (add a nullable/defaulted column first, backfill, then tighten).
  - Do not change a migration that has already been run; create a new migration.
  - Avoid operations that lock large tables for too long. Backfill large data via a separate job/command.
  - Do not use ORM models inside a migration (fragile against model changes); use the query builder.
- Use transactions for multi-step operations and row-level locking (for example `SELECT ... FOR UPDATE` or your ORM's equivalent) to prevent *race conditions*.
- Enable the ORM's lazy-loading guard outside production so N+1 is caught early.
- Select only the columns you need (`select`), use batched, cursor, or streaming iteration for large data, and avoid unbounded selects on tables that can grow.

## Backend performance
- **Cache** only for data proven to be expensive and frequently read; define a clear invalidation strategy and key naming.
- Slow work (email, reports, webhooks, file processing) belongs in a **Queue**. Jobs must be *idempotent* and have retry and backoff settings.
- On deploy, enable the framework's production optimizations. Persistent-process servers, caching layers, and the like only when there is a measured need (YAGNI).

## Frontend performance
- **Measure first, then optimize.** Do not perform premature optimization.
- Per-route code splitting is usually automatic in modern frameworks. Code-split heavy components that are not immediately visible (e.g. lazy loading with a loading fallback).
- Make server-rendered components the default and mark a component as client-side only where the framework requires it, keeping that at leaf components so less JavaScript is shipped to the browser.
- Use the image component of the framework (images, sizing, and lazy loading) and the font loader of the framework (fonts).
- Set server fetch caching and revalidation explicitly, and do not cache per-user data in a shared cache.
- If a compiler-based memoization mode is active in the project (enabled via framework config), do not add manual memoization (for example `memo` / `useMemo` / `useCallback` in React, `computed` / `shallowRef` caching in Vue) without profiling evidence. If it is not active yet, use them only when profiling shows a problem.
- Virtualization for long lists, *debounce* for search input, and take advantage of the server state library's cache.
- Watch bundle size; do not add a large library for a small need.
