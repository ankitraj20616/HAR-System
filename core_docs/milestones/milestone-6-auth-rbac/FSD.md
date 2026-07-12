# Milestone 6 FSD: Authentication Middleware and Role-Based Access Control

## 1. Goal

Dashboard ko public/open screen se secure application banana. Har user Supabase se signup/login karega. HAR APIs sirf valid access token aur allowed role ke saath open hongi.

Simple rule: **pehle identity verify, phir permission verify, uske baad data.**

## 2. Users and roles

| Role | Easy meaning | Allowed work |
|---|---|---|
| `pending` | Account bana hai, approval baaki hai | Login/logout only; monitoring data nahi |
| `caregiver` | Patient ko daily monitor karta hai | Live/history/feedback read, alert acknowledge |
| `doctor` | Clinical reviewer | Live/history/feedback read, feedback/summary request |
| `admin` | System administrator | All caregiver/doctor work plus role assignment |

New signup hamesha `pending` hoga. User apna role khud nahi badal sakta.

## 3. Functional requirements

| ID | Priority | Behaviour | Acceptance |
|---|---|---|---|
| FR-A1 | Must | Email/password signup and login Supabase Auth se ho. | Valid user session paata hai; invalid credentials generic error dete hain. |
| FR-A2 | Must | Email confirmation supported ho. | Confirmation enabled hone par unverified signup ko dashboard session nahi milta. |
| FR-A3 | Must | React har protected REST request mein access JWT bheje. | Request mein `Authorization: Bearer ...` ho; refresh token na ho. |
| FR-A4 | Must | Auth Service JWT signature and claims verify kare. | Invalid signature, expiry, issuer, audience, session/user claim reject hon. |
| FR-A5 | Must | Endpoint permissions role matrix se decide hon. | Missing/invalid identity = 401; insufficient role = 403. |
| FR-A6 | Must | New users default `pending` hon. | Signup ke baad admin approval se pehle HAR data unavailable ho. |
| FR-A7 | Must | Admin safely role assign kar sake. | Non-admin update rejected; change audit table mein record ho. |
| FR-A8 | Must | Supabase client access token automatically refresh kare. | Expired access token ke baad active session bina password re-entry continue kare. |
| FR-A9 | Must | WebSocket handshake authenticated ho. | Short-lived one-time ticket ke bina connection reject ho. |
| FR-A10 | Must | Logout session clear kare. | Refresh token invalidated/removed; UI login screen par aaye. |
| FR-A11 | Must | Fusion/Feedback browser se directly reachable na hon. | Compose mein public dashboard API path Auth Service se guzre. |
| FR-A12 | Must | Secrets and tokens logs/bundles mein na hon. | Secret scan and tests frontend/service-role leakage nahi dikhate. |

## 4. User journeys

### Signup

User email/password submit karta hai. Supabase record banata hai. Database trigger `pending` role banata hai. Email confirmation on hai to user email link click karta hai, phir login karta hai. Pending page usko batata hai ki admin approval chahiye.

### Login and normal request

Supabase React ko access JWT and refresh token deta hai. React access JWT HAR request header mein lagata hai. Auth Service token signature and role verify karke request Fusion/Feedback ko forward karti hai.

### Role assignment

Admin user UUID aur role submit karta hai. Auth Service admin JWT verify karke server-only service-role credential se Supabase `user_roles` update karti hai. User session refresh/login ke baad naya JWT claim paata hai.

## 5. Safety and privacy rules

- Password HAR backend ko kabhi nahi milega.
- Refresh token Fusion/Feedback/Auth proxy payload mein nahi jayega.
- `SUPABASE_SERVICE_ROLE_KEY` sirf backend environment mein hoga.
- User-supplied `X-HAR-User-*` headers remove karke gateway trusted values add karega.
- Error response token, key, password, internal URL ya Supabase raw error expose nahi karega.
- Default deny: koi endpoint explicit rule mein nahi hai to request reject hogi.

## 6. Scope limit

Current HAR demo single monitored context use karta hai. Milestone 6 endpoint/action RBAC deta hai; multi-patient tenancy (`doctor A` sirf assigned patient dekhe) abhi included nahi hai. Future milestone mein every activity/event ko `patient_id` ke saath migrate karna hoga.

## 7. Exit checklist

- [ ] Signup, confirmation, login, refresh and logout work.
- [ ] New user `pending` and data-blocked hai.
- [ ] Role matrix ke positive/negative tests pass hain.
- [ ] Fake/expired/wrong-project JWT rejected hai.
- [ ] REST and WebSocket gateway tests pass hain.
- [ ] Direct public Fusion/Feedback access Compose mein removed hai.
- [ ] Service-role key frontend files/build output mein absent hai.
- [ ] Supabase SQL, setup steps and recovery runbook tested hain.
