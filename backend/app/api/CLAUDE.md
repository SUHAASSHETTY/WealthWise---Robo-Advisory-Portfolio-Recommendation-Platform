# backend/app/api/: HTTP boundary (controllers)

FastAPI routers, Pydantic request/response schemas, auth dependencies and error mapping. **This layer is the authentication and authorisation boundary (NFR-04).**

## Allowed imports

`app.services`, `app.domain` (enums and value types only, for schema typing), `app.core` (security, logging, config). **Never `app.repositories`.** Routers don't touch the DB directly.

## Layout

```
api/
  deps.py            get_db, get_clock, current_user, require_role(*roles)
  errors.py          domain/service error → HTTP status + error envelope
  middleware.py      X-Request-ID correlation, request logging (template path, status, ms)
  schemas/           <feature>.py Pydantic v2 models; decimals as str
  routers/           auth.py, risk_profile.py, goals.py, recommendations.py, holdings.py,
                     rebalancing.py, advisor.py, admin.py, health.py
```

## Rules

- **Every route declares its role:** `dependencies=[Depends(require_role(Role.CUSTOMER))]` (or ADVISOR/ADMIN). Only `/health` and `/api/v1/auth/login` are public. `tests/architecture/test_routes_declare_roles.py` enforces this.
- **Customer routes never take a `customer_id` parameter.** The customer is resolved from the token. Advisor routes take `{customer_id}` and the service checks the assignment.
- **Decimals at the boundary:** request fields are `str` matching `^-?\d+(\.\d+)?$` with the spec's scale; JSON numbers return `422 DECIMAL_MUST_BE_STRING`. Responses serialise every Decimal as a string with fixed scale (`"5.00"`, `"400.0000"`).
- **Thin handlers:** parse, call one service method, map the result to a response model. No business rules and no arithmetic.
- **Error envelope:** `{"error": {"code", "message", "details"}}`, with status codes per app_spec §5.7. Unowned resources return 404, not 403.
- **Paths** match the spec exactly (`/api/v1/...`). Request and response field names match the spec tables. Any change is a spec PR first.
- **Logging:** the middleware logs method, the **route template** (not the raw path with IDs), status, duration and correlation ID. Never request or response bodies.
- **`/health`:** `SELECT 1`, returning 200 or 503, with no auth and within 1 s (NFR-07).
- **Tests:** `tests/acceptance/` (HTTP-level, AC-tagged, via `httpx.AsyncClient` against the app) and `tests/architecture/`.
