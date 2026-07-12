# Auth and RBAC Runbook

## Normal checks

- `/health` returns `auth_service` healthy.
- Login ke baad `/api/auth/me` correct UUID/email/role deta hai.
- Pending user `/api/status` par 403 paata hai.
- Caregiver status read and alert acknowledge kar sakta hai.
- Doctor read/generate kar sakta hai but acknowledge par 403 paata hai.
- WebSocket URL mein short ticket hota hai, JWT nahi.

## 401 Unauthorized

Browser session refresh try karega. Repeated 401 mein issuer/audience, Supabase URL, active signing key, system clock and hook-issued claims check karo. Token content logs mein mat print karo.

## 403 Forbidden

`/api/auth/me` role check karo. Supabase `user_roles` update ke baad old JWT still old role rakhega; logout/login ya refresh required hai.

## Role update 503/502

503 means backend service-role key configured nahi hai. 502 means Supabase update reject hua; key, migration/table and Supabase logs check karo. Raw upstream error user ko expose nahi hota.

## Live updates disconnected

REST `/api/auth/ws-ticket` permission, ticket TTL, auth-service logs and Fusion/Feedback internal health check karo. Ticket reuse expected rejection hai.

## Emergency key event

Compromised publishable key alone admin access nahi deta. Compromised service-role key ko Supabase mein rotate/revoke karo, backend env update/redeploy karo, audit log inspect karo. Ticket secret compromise par `AUTH_TICKET_SECRET` rotate and auth-service restart karo.
