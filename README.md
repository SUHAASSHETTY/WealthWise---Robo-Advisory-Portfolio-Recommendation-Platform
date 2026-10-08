# WealthWise — Robo-Advisory & Portfolio Recommendation Platform

WealthWise is a rule-based robo-advisory and investment portfolio management platform providing deterministic risk profiling, goal tracking, asset allocation recommendations, portfolio valuation, drift calculation, and rebalancing execution for retail investors.

---

## Quick Start Guide

### Prerequisites
- **Python 3.12+** with [Poetry](https://python-poetry.org/)
- **Node.js 18+** with `npm`
- **SQLite 3**

### Single-Command Start
Run migrations, seed synthetic data, and start both the backend FastAPI server (`:8000`) and the frontend React + Vite application (`:5173`) concurrently:

```bash
make dev
```
*(or `npm start` / `npm run dev` from the project root)*

Once started:
- **Frontend Application:** [http://localhost:5173](http://localhost:5173)
- **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Test Suites

Run the full end-to-end and domain test suites:

```bash
# Run all backend and frontend tests
make test

# Run backend domain, service, api, and architecture pytest suite
make test-backend

# Run frontend Playwright end-to-end tests (desktop + mobile with snapshots)
make test-frontend
```

---

## Available Personas & Role Switcher

WealthWise includes built-in role switching powered by development stub authentication tokens (`WEALTHWISE_STUB_AUTH_ENABLED=true`):

| Persona | Role | Token | Description |
| :--- | :--- | :--- | :--- |
| **Alice Fernandes** | `CUSTOMER` | `stub-token-alice` | Assessed profile, active portfolio with drift breach, verified KYC |
| **Bob Mathew** | `CUSTOMER` | `stub-token-bob` | Verified KYC, unassessed initial state |
| **Carol Dsouza** | `CUSTOMER` | `stub-token-carol` | Assessed Moderate profile, unverified KYC |
| **Frank Okoro** | `CUSTOMER` | `stub-token-frank` | Multi-goal portfolio with 48-month horizon |
| **Grace Lim** | `CUSTOMER` | `stub-token-grace` | Multi-goal portfolio with 29-month horizon |
| **Dan Advisor** | `ADVISOR` | `stub-token-dan` | Senior Wealth Advisor (fiduciary overrides & portfolio deep-dive) |
| **Erin Admin** | `ADMIN` | `stub-token-erin` | Platform Administrator (template versioning, risk policies, NAV ops) |

---

## Feature Modules & AC Mapping

- **🎯 Risk Profile & Questionnaire (`/risk-profile`) [AC-01]:** Interactive 7-question tolerance assessment, scoring logic with hard stop overrides, and risk band classification (`CONSERVATIVE`, `MODERATE`, `AGGRESSIVE`).
- **🏆 Goals Tracker (`/goals`) [AC-03, AC-08]:** Multi-goal creation with priority 1–5, target dates, funding share allocation, and automatic NAV valuation snapshots.
- **📊 Portfolio Recommendation (`/recommendation`) [AC-02, AC-04]:** Deterministic asset allocation strictly summing to 100.00% across Equity, Debt, Gold, and Cash with time-horizon shift rules.
- **💼 Holdings & Drift (`/holdings`) [AC-05]:** Real-time asset valuation from latest NAV feeds and absolute drift calculation (`abs(current% − target%)`) with breach threshold alerts.
- **⚖️ Rebalancing Engine (`/rebalancing`) [AC-06, AC-07]:** Drift-triggered trade proposal generator with buy/sell quantities, post-trade cash validation, and accept/dismiss audit trail.
- **👥 Advisor Workbench (`/advisor`) [AC-09]:** Managed customer overview, portfolio inspection, fiduciary risk band overrides with rationale notes, and custom manual allocations.
- **📑 Platform Administration (`/admin`) [AC-10]:** Immutably versioned template policies, risk scoring matrix configuration, asset class catalog, and daily NAV feed ops.

---

## Architecture Guarantees & Precision Rules
- **NFR-01 (Fixed-Point Decimal):** All monetary amounts and percentage calculations are represented with strict 2-decimal/4-decimal string fixed precision. No floating-point arithmetic is performed in UI code.
- **NFR-04 (Role Isolation):** Backend endpoints enforce strict role-based access control. All customer endpoints resolve identity from bearer tokens.
- **NFR-08 (Fiduciary Auditability):** Risk band reassignment and override records are immutable with mandatory actor, reason code, and timestamp metadata.
