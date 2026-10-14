# Testing

> Part of the agent guide. The summary and core rules are in [`AGENTS.md`](../AGENTS.md).

- **Backend**: the test runner of the stack.
  - *Unit test* for Services/Actions/pure logic.
  - *Feature/integration test* for HTTP endpoints (status, response structure, authorization, validation).
  - Start each test from a clean database and use factories/seeders and *fakes* for the queue, mailer, and HTTP client.
- **Frontend**: component-level test tooling for components, hooks, and utils.
  - Test the behavior the user sees, not internal implementation details.
  - Test custom hooks and utils separately.
  - Mock API calls at the API client boundary, and mock framework modules (e.g. routing/navigation) when needed.
  - Server-rendered components are often not supported by the component test runner (check the installed framework documentation): extract their logic into an ordinary testable function or component, and test the full flow via E2E.
  - Server-side handlers (server actions, route handlers) are tested as ordinary functions with the API client mocked. The real contract is tested in backend feature tests.
- Test writing pattern: **Arrange - Act - Assert**. A test name explains the scenario and the expected result, with no PRD ID or other document references. AC-to-test traceability lives in the PRD-code index, filled once at phase close (rules: `docs/CODE-DOCUMENTATION.md`).
- A failing test must **not** be deleted or skipped to make the pipeline green. Fix the cause.
