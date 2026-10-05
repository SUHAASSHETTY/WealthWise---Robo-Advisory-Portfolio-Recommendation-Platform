# frontend/: React + Vite + TypeScript

Read the root `CLAUDE.md` first.

## Shape

```
frontend/
  src/
    api/          typed client per feature (fetch wrapper adds Bearer token, X-Request-ID)
    types/        TS interfaces mirroring the spec API contracts (decimals typed as `string`)
    features/     risk-profile/, goals/, recommendation/, holdings/, rebalancing/, advisor/, admin/
    components/   shared UI primitives (AllocationBar, DriftTable, MoneyText, PercentText, …)
    app/          routing, layouts (CustomerLayout, AdvisorLayout, AdminLayout), auth context
  e2e/            Playwright specs (one per feature) + __snapshots__/
  playwright.config.ts
```

## Rules

- **No money arithmetic in the browser (NFR-01).** Decimal values arrive as strings and are displayed as strings, formatted with `Intl.NumberFormat` on a parsed copy **for display only**. Never sum, subtract or round amounts or percentages in TS. If a total is needed, the API provides it.
- **Strict TypeScript:** `strict: true`, zero `any`. API types mirror the spec field names exactly (snake_case from the API; map in `api/` if camelCase is wanted).
- **Role-aware routing:** customer routes `/risk-profile`, `/goals`, `/recommendation`, `/holdings`, `/rebalancing`; `/advisor/*` and `/admin/*` are guarded by role from the login response. The UI hides what a role can't use, but the **API is the real boundary**.
- **Responsive:** at least one layout must adapt meaningfully at 375 px and 1280 px (brief §7.2). The holdings and drift view is the primary candidate.
- **Accessibility:** semantic elements, labelled inputs, visible focus, AA contrast. The Harness evaluator and Playwright use `getByRole`/`getByLabel`/`getByText`, so every interactive element needs an accessible name.
- **No PII in the console or analytics.** Remove `console.log` from shipped code.
- **Tests:**
  - **Vitest unit tests:** co-located `*.test.tsx`.
  - **Playwright E2E:** in `e2e/`, with titles prefixed `AC-NN:`, semantic locators only, no `waitForTimeout`, and screenshot snapshots in `e2e/__snapshots__/`.
- **Harness design checks:** the ui-designer and design-critic flow (`/design`, Full-mode `/auto`) produces `specs/design/mockups/aesthetic-direction.md`. Production UI follows it.
