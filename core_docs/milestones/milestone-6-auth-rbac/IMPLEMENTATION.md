# Milestone 6 Implementation Notes

## Delivered result

Milestone 6 adds a Supabase-backed login/session UI and a new FastAPI Auth Service on port 8005.
Dashboard REST and live traffic now enters through this service. It verifies the Supabase access JWT,
applies an explicit role matrix, and forwards only allowed work to internal Fusion/Feedback services.

## Important files

- `services/auth_service/`: config, async JWKS verifier, RBAC rules, HTTP proxy, WebSocket tickets.
- `dashboard/src/auth/`: Supabase initialization, signup/login, pending approval, refresh, logout,
  and minimal admin role assignment.
- `supabase/migrations/001_auth_rbac.sql`: roles, audit, signup trigger, and access-token hook.
- `docker-compose.yml` and `dashboard/nginx.conf`: Auth Service public; Fusion/Feedback internal.
- `services/auth_service/Dockerfile`: minimal auth-only image without computer-vision/ML packages.
- `.env.example`: browser-safe and backend-only Supabase/ticket configuration.
- `tests/unit/test_auth_*` and `tests/integration/test_auth_gateway.py`: security behaviour.

## Security decisions

- React sends only access JWTs to HAR APIs. Refresh tokens stay in Supabase session handling.
- JWTs use asymmetric JWKS validation with exact issuer/audience and a strict algorithm allow-list.
- Missing/invalid token returns 401; insufficient permission returns 403; unknown route is denied.
- New user is `pending`; first admin is bootstrapped manually in Supabase.
- Incoming identity headers are removed and replaced with verified internal headers.
- Access JWT is never put in a WebSocket URL. A 30-second, target-specific, one-time ticket is used.
- Role service key and raw Supabase errors never reach the browser.

## Verification completed

- Python formatting and Ruff checks: pass.
- Complete backend suite: `198 passed, 1 skipped`.
- Dashboard TypeScript lint: pass.
- Dashboard Vitest suite: `5 passed`.
- Dashboard production build: pass (bundle-size warning only).
- Docker Compose render with valid-shaped auth environment: pass.
- Shell syntax and Git whitespace checks: pass.

## External setup still required

Repository code cannot create or configure the user's hosted Supabase project. Before live use, run
the supplied SQL migration, enable the Custom Access Token Hook, configure email/site redirects,
place real keys in `.env`, and bootstrap the first admin by following `SUPABASE_SETUP.md`.

## Known limitations

- Current data model is one monitored demo context, not patient-by-patient tenant isolation.
- WebSocket used-ticket memory is process-local; multiple Auth Service replicas need Redis/database.
- Local JWT verification does not instantly detect logout; an issued JWT remains valid until `exp`.
- Admin role changes appear after user token refresh or a new login.
- Supabase connectivity is required for signup/login/refresh even though HAR inference remains local.
