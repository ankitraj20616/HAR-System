# 🛡️ Simple RBAC Implementation Plan (PostgreSQL)

Ye document ek simple aur secure **Role-Based Access Control (RBAC)** system banane ka plan hai, jisme hum PostgreSQL tables ka use karenge.

## 1. 🎯 Goal (Maksad)
Ek aasan RBAC system banana jisme user ke signup karte hi usko ek default role mile, aur baad me `admin` us user ka role change kar sake. 

## 2. 👥 System ke Roles (Permissions)
Project me 4 main roles honge:

1. **`pending` (Default):** Naya user jab signup karega toh usko ye role milega. Ise koi data nahi dikhega.
2. **`caregiver`:** Patient ka live data dekh sakta hai aur emergency alerts ko handle (acknowledge) kar sakta hai.
3. **`doctor`:** Timeline aur history dekh sakta hai, par alerts dismiss nahi kar sakta.
4. **`admin`:** Poore system ka boss. Ye baaki users (pending) ko unka sahi role (doctor/caregiver) assign karega.

---

## 3. 🗄️ PostgreSQL Database Design

Hum database me ek nayi table banayenge jo user ki ID ko uske role ke sath jodegi.

### Table 1: `user_roles`
Ye table batayegi ki kis user ka kya role hai.

| Column Name | Data Type | Details |
| :--- | :--- | :--- |
| `user_id` | UUID (Primary Key) | Ye auth table ke user id se link hoga (Foreign Key). |
| `role` | Enum (String) | Isme sirf (`pending`, `caregiver`, `doctor`, `admin`) hi allowed honge. Default `pending` rahega. |
| `assigned_by` | UUID | Kis admin ne ye role diya, uski ID. |
| `updated_at` | Timestamp | Role aakhri baar kab change hua. |

**SQL Query (Example):**
```sql
CREATE TYPE user_role_type AS ENUM ('pending', 'caregiver', 'doctor', 'admin');

CREATE TABLE user_roles (
    user_id UUID PRIMARY KEY,
    role user_role_type NOT NULL DEFAULT 'pending',
    assigned_by UUID,
    updated_at TIMESTAMP DEFAULT now()
);
```

---

## 4. ⚙️ System Kaam Kaise Karega? (Logic Flow)

### Step A: Naya User Signup (Trigger)
Jaise hi koi naya user app me sign up karega, PostgreSQL ka ek **Trigger (ya function)** automatically chalega aur `user_roles` table me ek nayi entry bana dega jiska role `pending` hoga.

### Step B: Token me Role dalna
Jab user login karega, toh backend (Auth Service) `user_roles` table se uska role padhega aur usko Access Token (JWT) ke andar daal dega.

### Step C: API Restrictions (Kaun kya kar sakta hai)
Backend me har API ke upar ek chota sa check (middleware) laga hoga:
* **`GET /api/live-data`** -> Sirf `caregiver`, `doctor`, `admin` ko allowed hai.
* **`POST /api/assign-role`** -> Sirf `admin` ko allowed hai.

---

## 5. 🛠️ API Endpoints (Admin ke liye)

Admin ko ek dashboard panel milega jahan se wo roles manage karega. Iske liye 2 APIs banengi:

1. **`GET /api/users`** 
   * **Kaam:** Saare `pending` aur baaki users ki list lana.
   * **Access:** Sirf `admin`.

2. **`POST /api/users/{user_id}/role`**
   * **Kaam:** Kisi user ka role update karna (jaise pending se doctor banana).
   * **Input:** `{ "new_role": "doctor" }`
   * **Access:** Sirf `admin`.

### Table 2: `role_audit_log` (Security Tracking)
Jaisa ki aapne kaha, security ke liye hum ek audit log table banayenge. Ye record rakhegi ki kisne kiska role kab change kiya.

| Column Name | Data Type | Details |
| :--- | :--- | :--- |
| `id` | BigInt | Auto-incrementing ID. |
| `user_id` | UUID | Jiska role change hua. |
| `old_role` | Enum | Pehle kya role tha. |
| `new_role` | Enum | Naya role kya diya gaya. |
| `changed_by` | UUID | Kis admin ne change kiya. |
| `changed_at` | Timestamp | Kis waqt change hua. |

**SQL Query (Example):**
```sql
CREATE TABLE role_audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL,
    old_role user_role_type,
    new_role user_role_type NOT NULL,
    changed_by UUID,
    changed_at TIMESTAMP DEFAULT now()
);
```

> **Final Design Decision:** Jaisa ki aapne confirm kiya hai, ek user ka strictly ek hi role hoga (single-role per user). Ye design complexity ko kam rakhega aur authorization rules ko simple banayega.

---

> **Note:** Plan ab final ho gaya hai. Aur sabse mazedar baat ye hai ki kyunki aapne ekdam perfect software engineering design chuna hai, is project ke actual code (`001_auth_rbac.sql`) me bhi same yahi logic aur yahi 2 tables use ki gayi hain! Aapne system design complete kar liya hai!
