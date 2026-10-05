# WealthWise: Business Case

**Case ID:** BC-AINE-008 · **Domain:** Banking & Financial Services, Wealth Management
**Product:** WealthWise, a rule-based robo-advisory and portfolio recommendation platform

---

## 1. Problem

Most retail customers of a mid-sized wealth management firm never get a portfolio review. Human advisors are expensive, so the firm saves them for high-net-worth clients. Everyone else gets generic product brochures, or nothing at all. That causes three problems:

1. **Unsuitable portfolios.** Customers pick funds based on recent returns or word of mouth, not on how much risk they can bear or when they need the money. A customer saving for a house deposit due in two years can end up heavily in equities.
2. **Portfolios drift silently.** Even a well-built allocation goes stale as markets move. Without a periodic check, a 50/50 equity/debt portfolio can become 65/35 after a rally, and nobody tells the customer they're now carrying more risk than they agreed to.
3. **Goals aren't measured.** Customers have goals (retirement, a child's education, a home) but no way to see how close they are. That makes it hard to stay invested through downturns.

The firm wants a **self-service robo-advisor** that handles these cases at scale. Regulators and the firm's compliance team must be able to **explain every recommendation**, so the logic has to be **deterministic and rule-based, not machine-learned**. Given the same answers, policy version and dates, the platform must always produce the same result. An auditor must be able to reproduce any past recommendation from the stored inputs.

## 2. Target users

| User | Who they are | What they need from WealthWise |
|---|---|---|
| **Retail investor** (customer) | An individual with modest investable assets, little financial training, mostly on mobile | A short questionnaire that tells them their risk band in plain language; a recommended mix of equity, debt, gold and cash; goals with visible progress; a clear prompt when the portfolio drifts, with a one-click accept or dismiss |
| **Advisor** | A licensed relationship manager responsible for a book of customers | A single view of a customer's profile, goals, holdings and drift; the ability to **override a risk band** when the questionnaire result doesn't fit the person, always with a recorded reason; the ability to log a manual recommendation |
| **Administrator** (product/compliance) | Owns the investment policy | Maintain the questionnaire scoring, the risk-band thresholds, the asset-class list and the allocation templates as **versioned policies**; publish new versions without disturbing customers already advised under the old ones |

## 3. Value proposition

- **For customers:** advice they can understand and act on in minutes, not weeks. Their portfolio stays aligned with their stated risk appetite and goal dates without them having to watch the market.
- **For advisors:** the platform does the routine work (scoring, allocation, drift monitoring), so they can spend their time on the exceptions where judgement matters. Every override they make is recorded, which protects them in a suitability review.
- **For the firm:** advice reaches the long tail of retail customers at close to zero marginal cost. Every recommendation can be explained and reproduced, because each one stores the exact policy version, inputs and arithmetic that produced it. Policy changes are controlled releases, not silent edits.

## 4. Domain rules (business view)

These are the business rules in plain language. The specs under `specs/` turn each one into exact, testable rules.

1. **Risk profiling is a scored questionnaire.** The customer answers at least six questions about age, investment horizon, income stability, emergency savings, reaction to losses, experience and objective. Each answer carries fixed points. The total maps to one of three bands: **Conservative**, **Moderate** or **Aggressive**. The same answers under the same policy version always give the same band.
2. **A risk band selects an allocation template.** Each band has a target mix across four asset classes: equity, debt, gold and cash. The percentages in every template **always add up to exactly 100**.
3. **Goal timing tempers risk.** Money needed soon must not sit in volatile assets. The closer a goal's target date, the more of the equity allocation moves into debt, or into cash for goals under a year away.
4. **Drift is measured per asset class.** Drift is the absolute gap between the share an asset class currently holds and its target share. When **any** asset class drifts by more than the configured threshold (5 percentage points by default), the platform proposes a rebalance.
5. **Rebalancing proposals are concrete.** A proposal lists BUY and SELL quantities per asset class and carries a unique ID. The customer accepts or dismisses it, and either decision is recorded with who made it and when. Orders are simulated; there is no real brokerage connection.
6. **Goal progress is objective.** Progress equals the goal's current value divided by its target amount, recalculated every time daily prices (NAVs) are refreshed.
7. **Advisors may override, never silently.** A risk-band change by an advisor requires a reason and a supporting note. The original questionnaire result is kept alongside the override.
8. **Policies are versioned and immutable once published.** Publishing a new questionnaire or template version never changes the advice already given. Customers keep the version that was active when they were advised until they are advised again.
9. **Money is exact.** Values, percentages and drift use exact decimal arithmetic. Floating-point rounding errors are not acceptable in financial records.
10. **Privacy by default.** Customer personal data and financial positions never appear in application logs.

## 5. Success metrics

Metrics for the capstone build are measurable in the repository or the running app. Pilot metrics are what the firm would track after launch.

| Metric | Target | How it is measured |
|---|---|---|
| Recommendation determinism | 100% identical output for identical inputs | Repeated-run test over the questionnaire answer space and fixed dates |
| Allocation integrity | 0 templates or recommendations whose percentages don't sum to exactly 100.00 | Architecture or invariant tests plus validation when a version is published |
| Acceptance criteria coverage | Every AC-01…AC-10 has at least one passing test tagged with its ID | Test inventory grep and CI run |
| Audit completeness | 100% of band assignments, overrides, recommendations and rebalancing decisions have an append-only record with actor and timestamp | Integration tests; schema has no update path for these tables |
| Log hygiene | 0 occurrences of PII or position values in logs | Log-capture tests and a PII-redaction hook |
| Time to first recommendation (pilot) | Under 5 minutes from sign-in to seeing a recommended allocation | Product analytics (pilot) |
| Drift response (pilot) | At least 60% of rebalancing proposals acted on (accepted or dismissed) within 7 days | Decision timestamps vs proposal timestamps |
| Advisor override rate (pilot) | Under 10% of customers; a higher rate means the questionnaire needs tuning | Overrides ÷ customers with an assessment |

## 6. Scope

**In scope:** risk questionnaire and banding; versioned allocation templates; recommendations that account for the goal horizon; goals with progress tracking; holdings with drift; rebalancing proposals with BUY/SELL quantities and simulated orders; the advisor workbench (portfolio view, override, manual recommendation); the admin console (rules, scoring, asset classes, templates); a stubbed daily NAV feed; role-separated authentication.

**Out of scope:** real brokerage or exchange connectivity; live market data; multi-currency or FX; tax optimisation; real KYC workflows (a stub `kyc_verified` flag is used); ML-based advice; production deployment, secret management and multi-region.

**Data:** all customers, holdings and prices are **synthetic**. No real or confidential customer data is used anywhere in the project.

## 7. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Unsuitable advice from a badly tuned questionnaire | Advisor override with mandatory reason; override-rate metric; versioned scoring so tuning is controlled |
| Policy change retroactively alters past advice | Immutable published versions; every recommendation stores its version IDs |
| Rounding errors in money or percentages | Decimal-only arithmetic with explicit rounding rules; architecture test forbidding floats in money paths |
| Leakage of personal or financial data | Structured logs with IDs only; PII redaction checks; role-separated API |
