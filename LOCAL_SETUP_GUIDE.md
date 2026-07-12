# HAR System: Local Setup Guide

Ye guide ek new developer ko clean checkout se complete authenticated HAR prototype tak le jaati
hai. Commands repository root se run karein:

```bash
cd /home/insightstap/Collage_Project/HAR-System
```

## 1. Ab system kaise work karta hai?

```text
React dashboard
   ├── signup/login/refresh ──> Supabase Auth
   └── Bearer access JWT ─────> FastAPI Auth Service :8005
                                      ├── role check
                                      ├── Fusion Service :8001 (Docker internal)
                                      └── Feedback Service :8002 (Docker internal)
```

- Supabase user account, login session, access JWT aur refresh token manage karta hai.
- React HAR backend ko sirf short-lived access JWT bhejta hai.
- Refresh token Supabase client ke session flow mein rehta hai.
- Auth Service har protected REST request ka JWT aur role verify karti hai.
- Browser Fusion/Feedback services ko directly call nahi karta.
- Local PostgreSQL HAR timeline/events/feedback store karta hai.
- Supabase PostgreSQL authentication users/roles/audit store karta hai.

Ye dono databases alag responsibility rakhte hain; Supabase database local HAR PostgreSQL ko replace
nahi karta.

## 2. Quick-start checklist

First setup ka correct order:

1. Docker, Git aur required tools install karein.
2. `./dev.sh setup` run karke `.env` create karein.
3. Supabase project create/open karein.
4. Supabase SQL Editor mein `supabase/migrations/001_auth_rbac.sql` run karein.
5. Supabase Custom Access Token Hook enable karein.
6. Supabase Site URL/email settings configure karein.
7. `.env` mein real Supabase values aur random ticket secret dalein.
8. `./dev.sh up` run karein.
9. First user signup/email verify karein aur manually first admin banayein.
10. Logout/login karke dashboard access verify karein.

Detailed Supabase-only instructions bhi yahan available hain:
[`SUPABASE_SETUP.md`](core_docs/milestones/milestone-6-auth-rbac/SUPABASE_SETUP.md).

## 3. Prerequisites

Required:

- Git;
- Docker Engine/Desktop;
- Docker Compose v2 (`docker compose version`);
- a Supabase project;
- internet access for signup, login and session refresh;
- `curl` for health/smoke checks;
- approximately 8 GB RAM.

Optional:

- Linux webcam for live video recognition;
- Python 3.11/3.12 and `uv` for backend development/tests;
- Node/npm for standalone frontend development;
- Ollama for locally generated feedback.

Docker verify karein:

```bash
docker version
docker compose version
docker info
```

Linux par Docker permission error aaye to Docker service/group configuration fix karein; commands ko
blindly `sudo` ke saath mix na karein, kyunki isse root-owned project files ban sakti hain.

## 4. Repository aur `.env` prepare karein

```bash
./dev.sh setup
```

Ye command:

- Docker/Compose availability check karti hai;
- missing `.env` ko `.env.example` se create karti hai;
- Compose syntax validate karti hai;
- next auth configuration steps print karti hai.

Important: `.env.example` ke Supabase values placeholders hain. `./dev.sh up` tab tak intentionally
stop karega jab tak placeholders replace nahi hote.

Kabhi commit na karein:

- `.env`;
- Supabase service-role key;
- access/refresh tokens;
- real passwords;
- cloud API keys.

## 5. Supabase configure karein

### 5.1 Project URL aur keys

Supabase Dashboard mein project open karein. Project URL aur publishable key copy karein.

`.env` mein:

```dotenv
SUPABASE_URL=https://your-real-project-id.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_your_real_value
SUPABASE_SERVICE_ROLE_KEY=your_server_only_service_role_key
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ALGORITHMS=RS256,ES256
```

Rules:

- Publishable key browser ko dena allowed hai.
- Service-role key sirf Auth Service environment ke liye hai.
- Service-role key ko `VITE_` prefix kabhi na dein.
- Admin panel se roles update karne ke liye service-role key required hai.
- Agar service-role key blank hai, login/read flow chal sakta hai but admin role-update API `503` degi.

### 5.2 Asymmetric signing key

Supabase Authentication signing-key settings mein RSA/EC asymmetric key active rakhein. Auth Service
Supabase ke JWKS public keys se JWT verify karti hai. Private JWT signing key application ko nahi
chahiye.

### 5.3 Auth/RBAC SQL migration

Supabase SQL Editor open karke ye file complete run karein:

```text
supabase/migrations/001_auth_rbac.sql
```

Migration create karti hai:

- `pending`, `caregiver`, `doctor`, `admin` roles;
- `user_roles` table;
- role audit log;
- every new signup ke liye default `pending` role;
- JWT mein `user_role` add karne wala custom access-token hook function;
- required RLS/grants/revokes.

Migration local HAR PostgreSQL container mein run na karein. Ye Supabase project ke SQL Editor mein
run honi chahiye.

### 5.4 Custom Access Token Hook enable karein

Supabase Dashboard mein:

```text
Authentication → Hooks → Custom Access Token
```

`public.custom_access_token_hook` select karke enable karein.

Hook enable na ho to user login kar sakta hai, lekin JWT mein recognized `user_role` nahi hoga aur
Auth Service request ko `401` se reject karegi.

### 5.5 URL aur email settings

Authentication URL Configuration mein local development ke liye:

```text
Site URL: http://localhost:5173
Allowed redirect URL: http://localhost:5173
```

Email confirmation enabled ho to signup ke immediately baad session `null` hona normal hai. User
email confirmation link click karne ke baad login karega.

## 6. WebSocket ticket secret generate karein

At least 32-character random secret use karein. OpenSSL example:

```bash
openssl rand -hex 32
```

Output ko `.env` mein set karein:

```dotenv
AUTH_TICKET_SECRET=replace_with_generated_random_value
AUTH_TICKET_TTL_SECONDS=30
AUTH_UPSTREAM_TIMEOUT_SECONDS=10
```

Ye Supabase key nahi hai. Auth Service isse short-lived one-time browser WebSocket tickets sign karti
hai. Secret change karne ke baad Auth Service restart karein; old tickets automatically invalid ho
jayenge.

## 7. Remaining environment configuration

Common values:

| Variables | Meaning |
|---|---|
| `POSTGRES_*` | Local HAR database name/user/password/host port |
| `AUTH_SERVICE_PORT` | Public protected API gateway, default `8005` |
| `SENSOR_SERVICE_PORT` | Sensor service health/dev port, default `8003` |
| `VIDEO_SERVICE_PORT` | Video service health/dev port, default `8004` |
| `DASHBOARD_PORT` | React/Nginx dashboard, default `5173` |
| `MQTT_PORT` | Mosquitto host port, default `1883` |
| `WINDOW_*` | Sensor window settings |
| `MODALITY_WEIGHTS` | Sensor/video fusion weights |
| `LLM_PROVIDER`, `LLM_MODEL` | Feedback provider/model |
| `VIDEO_DEVICE`, `VIDEO_GID` | Optional Linux webcam device/group |

Compose internal URLs automatically use Docker service names. Root `.env` ka host-side
`DATABASE_URL=...localhost...` sirf directly host par service run karne ke kaam aata hai.

Config render validate karein:

```bash
./dev.sh config
```

Rendered output share karte waqt secrets redact karein.

## 8. Stack start karein

```bash
./dev.sh up
```

Command:

1. `.env` auth placeholders reject karti hai;
2. PostgreSQL and Mosquitto start karti hai;
3. empty HAR database seed karti hai;
4. service images build karti hai;
5. simulator, Sensor, Video, Fusion, Feedback, Auth and Dashboard start karti hai;
6. container health ka wait karti hai.

Status aur logs:

```bash
./dev.sh status
./dev.sh logs
./dev.sh logs auth-service
./dev.sh logs fusion-service
./dev.sh logs feedback-service
```

Dashboard:

```text
http://localhost:5173
```

Auth API documentation:

```text
http://localhost:8005/docs
```

## 9. Services and network access

| Service | Host access | Purpose |
|---|---|---|
| Dashboard | `http://localhost:5173` | Login and monitoring UI |
| Auth Service | `http://localhost:8005` | Public JWT/RBAC REST/WebSocket gateway |
| Fusion Service | Docker-only `fusion-service:8001` | Activity, events, history and trends |
| Feedback Service | Docker-only `feedback-service:8002` | Feedback and summaries |
| Sensor Service | `http://localhost:8003` | Sensor pipeline/health |
| Video Service | `http://localhost:8004` | Pose pipeline/health |
| Mosquitto | `localhost:1883` | Internal event/prediction broker |
| Local PostgreSQL | `localhost:5432` | HAR timeline/events/feedback |

Fusion/Feedback ports host par publish nahi kiye gaye, taaki browser Auth Service bypass na kar sake.

Public health checks:

```bash
curl http://localhost:8005/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:5173/health
```

## 10. First signup aur admin bootstrap

### 10.1 First account create karein

1. `http://localhost:5173` open karein.
2. `Sign up` select karein.
3. Email/password submit karein.
4. Email confirmation enabled hai to email verify karein.
5. Sign in karein.

First account `pending` screen dekhega. Ye expected secure behavior hai.

### 10.2 First admin manually banayein

Supabase Table Editor mein `public.user_roles` open karein. First user UUID ka role `pending` se
`admin` update karein.

Uske baad browser mein:

1. sign out;
2. sign in again;
3. `/api/auth/me` new JWT se `admin` role verify karega;
4. dashboard ke top par minimal admin role-assignment panel available hoga.

First admin ko automatic “first signup wins” logic se create na karein. Public signup attacker ko
admin bana sakta hai.

### 10.3 Other users approve karein

Other users signup ke baad default `pending` honge. Admin panel mein user UUID aur role select karein.
Role update ke baad affected user logout/login ya session refresh kare, kyunki existing JWT mein old
role claim rehta hai.

## 11. Role permissions

| Action | pending | caregiver | doctor | admin |
|---|---:|---:|---:|---:|
| Login/logout | Yes | Yes | Yes | Yes |
| Monitoring data read | No | Yes | Yes | Yes |
| Live WebSocket | No | Yes | Yes | Yes |
| Feedback/summary generate | No | Yes | Yes | Yes |
| Alert acknowledge | No | Yes | No | Yes |
| User role update | No | No | No | Yes |

Expected errors:

- `401 Unauthorized`: token missing, expired, malformed, wrong project, wrong audience, or missing role claim;
- `403 Forbidden`: identity valid hai but assigned role requested action allow nahi karta;
- `503 Role administration is not configured`: backend service-role key missing hai.

## 12. Login/session request flow

Normal REST request:

```text
React → Authorization: Bearer <access JWT> → Auth Service → RBAC → Fusion/Feedback
```

Rules:

- HAR APIs ko refresh token na bhejein.
- Tokens URL/query params mein na dalein.
- Tokens logs, screenshots, issue descriptions ya chat messages mein share na karein.
- Access token expire hone par Supabase client session refresh karta hai.

Browser WebSocket custom Authorization header reliably set nahi karta. Isliye React pehle:

```text
POST /api/auth/ws-ticket
```

call karta hai, phir returned 30-second one-time ticket se `/ws` ya `/feedback-ws` open karta hai.
Access JWT WebSocket URL mein nahi jaata.

## 13. Protected API manually verify karna

Normally browser dashboard use karein. Debugging ke liye current Supabase **access token** ko temporary
shell variable mein rakha ja sakta hai. Refresh token/service-role key use na karein:

```bash
ACCESS_TOKEN='<temporary-current-access-jwt>'
curl -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8005/api/auth/me
curl -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8005/api/status
curl -H "Authorization: Bearer $ACCESS_TOKEN" "http://localhost:8005/api/trends?period=24h"
```

Verification ke baad shell unset karein:

```bash
unset ACCESS_TOKEN
```

Missing-token check intentionally `401` hona chahiye:

```bash
curl -i http://localhost:8005/api/status
```

## 14. Seeded prototype walkthrough

1. First admin/caregiver login ensure karein.
2. Fresh demo content ke liye `./dev.sh seed` run karein.
3. Dashboard par system/modality state show karein.
4. Timeline and Trends open karein.
5. Seeded fall banner and Alerts history show karein.
6. Caregiver/admin role se alert acknowledge karein.
7. Feedback panel mein seeded summary show karein.
8. Optional fresh feedback generate karein.
9. `./dev.sh status` aur service logs show karein.

`./dev.sh seed` local application tables clear/repopulate karta hai. Supabase users/roles delete nahi
karta.

## 15. Optional Ollama feedback

System Ollama ke bina safe deterministic fallback feedback de sakta hai. Local model ke liye:

```bash
ollama pull llama3.2:3b
ollama serve
ollama list
```

`.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_HOST=http://host.docker.internal:11434
FEEDBACK_FALLBACK_ENABLED=true
```

## 16. Optional sensor model

Default deterministic fallback ko artifact download nahi chahiye. Approved model use karne ke liye:

1. publisher se exact artifact/licence obtain karein;
2. file `data/models/model.tflite` mein rakhein;
3. exact output label order configure karein.

```dotenv
SENSOR_MODEL_PATH=/models/model.tflite
SENSOR_MODEL_LABELS=STANDING,WALKING,SITTING,LYING,EXERCISING,UNKNOWN
USE_FALLBACK=false
```

Label order guess na karein; wrong order silently wrong activities produce kar sakta hai.

## 17. Optional Linux webcam

```bash
ls -l /dev/video*
getent group video
HAR_WEBCAM=true VIDEO_DEVICE=/dev/video0 ./dev.sh up
```

Persistent settings `.env` mein dalein. macOS/Windows Docker Desktop Linux device passthrough jaisa
camera access nahi deta; video service ko host par run karna pad sakta hai. Camera absent ho to Video
Service safely degraded rehni chahiye.

## 18. Stop, restart, reset

```bash
./dev.sh restart auth-service
./dev.sh restart feedback-service
./dev.sh down
```

`down` local PostgreSQL/MQTT volumes preserve karta hai.

Fresh local HAR demo data:

```bash
./dev.sh seed
```

Intentional complete local data deletion:

```bash
docker compose down --volumes
```

Warning: `--volumes` local HAR database/MQTT data delete karta hai. Supabase hosted users/roles par
iska effect nahi hota.

## 19. Automated checks

Secured stack smoke check:

```bash
./dev.sh smoke
```

Smoke test protected API ko token ke bina call karke expected `401` bhi verify karta hai. Ye real
user login/role UI acceptance test replace nahi karta.

Python development/tests:

```bash
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

Frontend checks:

```bash
cd dashboard
npm ci
npm run lint
npm test
npm run build
```

### Standalone Vite development caveat

Authenticated end-to-end UI ke liye Compose dashboard (`http://localhost:5173`) recommended hai.
Current Vite development proxy direct Fusion/Feedback development targets use karta hai; standalone
`npm run dev` tab tak complete Auth Service flow represent nahi karega jab tak its `/api`, `/ws`, and
`/feedback-ws` proxy targets Auth Service port `8005` par configure na hon. Component tests/lint/build
standalone run kiye ja sakte hain.

## 20. Troubleshooting

### `Configure SUPABASE_URL...` error

`.env` abhi example placeholders use kar raha hai. Real project URL, publishable key and generated
ticket secret set karein.

### Signup works but session nahi milta

Email confirmation enabled ho sakta hai. Confirmation email/link check karein. Supabase Site URL and
redirect URL `http://localhost:5173` se match hone chahiye.

### Login ke baad `401`

Check:

- Custom Access Token Hook enabled hai;
- JWT mein recognized `user_role` claim hai;
- `SUPABASE_URL` same project ka hai;
- asymmetric signing key/JWKS active hai;
- audience `authenticated` hai;
- machine clock correct hai;
- user ne role change ke baad session refresh/logout-login kiya hai.

Token ko logs mein print na karein.

### Login valid but `403`

User role valid hai but requested permission allowed nahi. `pending` user ko admin approve kare.
Doctor alert acknowledge nahi kar sakta; caregiver/admin kar sakte hain.

### Admin role update `503`

`SUPABASE_SERVICE_ROLE_KEY` Auth Service `.env` mein missing hai. Key add karke:

```bash
./dev.sh restart auth-service
```

### Dashboard login screen load nahi hoti

```bash
curl http://localhost:5173/health
curl http://localhost:5173/api/auth/config
./dev.sh logs dashboard
./dev.sh logs auth-service
```

Public auth config response mein only Supabase URL and publishable key honi chahiye—service-role key
nahi.

### Live updates disconnected

Check authenticated `/api/auth/ws-ticket`, Auth Service logs, Fusion/Feedback internal health and
system clock. Ticket short-lived and one-time hota hai; reuse rejection expected hai.

### Fusion/Feedback localhost ports nahi khul rahe

Secured Compose mein expected hai. Dono Docker-internal hain. Browser/API calls port `8005` Auth
Service ke through karein.

### Docker/port/camera/feedback issues

- Docker unreachable: Docker Engine/Desktop start karein.
- Port allocated: matching host port `.env` mein change karein.
- Camera degraded: webcam ke bina expected; Linux overlay instructions follow karein.
- Ollama unavailable: `ollama list`, `OLLAMA_HOST` and logs check karein; fallback enabled rakhein.
- Service unhealthy: `./dev.sh status` and `./dev.sh logs <service>` use karein.

## 21. Security reminders and deeper docs

- Raw video frames store/transmit nahi hone chahiye.
- `.env` and secrets commit na karein.
- Service-role key frontend source/build mein nahi honi chahiye.
- Refresh token HAR backend ko nahi bhejna hai.
- New signup default `pending` rehna chahiye.
- Unknown routes/actions default deny hone chahiye.
- System academic assistive prototype hai, certified medical/emergency device nahi.

Related documents:

- [Milestone 6 FSD](core_docs/milestones/milestone-6-auth-rbac/FSD.md)
- [Milestone 6 TDD](core_docs/milestones/milestone-6-auth-rbac/TDD.md)
- [Supabase setup](core_docs/milestones/milestone-6-auth-rbac/SUPABASE_SETUP.md)
- [Auth/RBAC runbook](core_docs/milestones/milestone-6-auth-rbac/RUNBOOK.md)
- [Security checklist](core_docs/milestones/milestone-6-auth-rbac/SECURITY_CHECKLIST.md)
- [Release runbook](core_docs/milestones/milestone-5-verification-release/RUNBOOK.md)
