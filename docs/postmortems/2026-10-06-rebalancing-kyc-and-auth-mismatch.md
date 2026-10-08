# Debugging Post-Mortem: Environment-First Resolution of KYC Rebalancing Gate & Persona Token Alignment

**Incident Date:** 2026-10-06  
**Status:** RESOLVED  
**Methodology:** Environment-First Resolution (Env → Config/Seeds → API Contracts → Domain Code)

---

## 1. Summary & Symptoms

During frontend integration testing and Playwright E2E execution of the Rebalancing Engine (AC-06, AC-07) and Advisor Workbench (AC-09):
1. Rebalancing proposal acceptance for test customer Carol Dsouza unexpectedly failed with HTTP 409 Conflict: `{"error": {"code": "KYC_NOT_VERIFIED", "message": "Customer KYC is not verified."}}`.
2. Initial manual API curl requests to `/api/v1/advisor/customers` returned HTTP 401: `{"error": {"code": "UNAUTHENTICATED", "message": "A valid bearer token is required."}}`.

---

## 2. Root Cause Analysis (Environment-First Investigation)

Rather than immediately altering domain policies or commenting out security checks in backend services, the investigation followed the mandatory **Environment-First Resolution** sequence:

### Step 1: Environment & Authentication Configuration Check
- **Investigation:** Examined backend environment variable `WEALTHWISE_STUB_AUTH_ENABLED` and token resolver `backend/app/core/security.py`.
- **Finding:** `_STUB_PRINCIPALS` maps `"stub-token-dan"` → `dan.advisor` (ADVISOR) and `"stub-token-alice"` → `alice.customer` (CUSTOMER). Test curl scripts passing `-H "Authorization: Bearer dan"` failed because the configured prefix is `stub-token-dan`.
- **Resolution:** Updated frontend `auth.ts` personas and test harnesses to supply the exact configured token strings (`stub-token-dan`, `stub-token-alice`, `stub-token-carol`).

### Step 2: Database Seed State & KYC Model Verification
- **Investigation:** Queried the active SQLite database `backend/wealthwise.db` directly to inspect customer KYC statuses:
  ```sql
  SELECT id, display_name, kyc_verified FROM customers;
  ```
- **Database Output:**
  ```
  00000000-0000-4000-8000-00000000c001 | Alice Fernandes | 1 (KYC Verified)
  00000000-0000-4000-8000-00000000c002 | Bob Mathew      | 1 (KYC Verified)
  00000000-0000-4000-8000-00000000c003 | Carol Dsouza    | 0 (KYC Pending)
  ```
- **Finding:** By design in `0002_sprint1_seed.py` and `app_spec.md`, Carol Dsouza is seeded with `kyc_verified=False` to serve as a negative test case for unverified account gates. Alice Fernandes and Bob Mathew are seeded with `kyc_verified=True`.
- **Resolution:** Rebalancing order acceptance flows were aligned to test against KYC-verified persona Alice Fernandes, while Carol Dsouza remains the reference persona for KYC gating and unassessed status.

---

## 3. Key Takeaway & Guardrails

- **Zero Domain Code Hacks:** The backend domain check in `rebalancing_service.py` was operating with 100% correctness according to AC-07.2 ("Only KYC-verified customers may place trade orders").
- **Preserved Invariants:** Avoiding premature code edits prevented introducing security vulnerabilities that would allow unverified retail customers to execute market trades.
- **Automated Verification:** Added Playwright tests proving that KYC-verified customers succeed in placing orders while unverified accounts cleanly receive appropriate UI guidance.
