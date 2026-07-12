# 🛠️ TECHNICAL DESIGN (TDD) ko samjho — Ekdam Scratch se, Noob-Friendly Hinglish me

> Ye file `core_docs/TECHNICAL_DESIGN.md` ka **poora explanation** hai — maan ke chalo ki
> tumhe technical cheezein bilkul nahi aati. Hum **har ek concept zero se** banayenge:
> API kya hota hai, database kya hota hai, JSON kya hota hai, MQTT kya hota hai — sab kuch.
>
> **FSD (pichli file) ne bataya system KYA karta hai. Ye TDD batata hai system KAISE banega**
> — code, tools, database, messages, sab.
>
> ⚠️ **Padhne ka tarika:** Jaldi mat karo. Pehle neeche wala **"PART 0: Technical Foundation"**
> aaram se padho — ye base hai. Base pakka ho gaya to baaki document paani ki tarah samajh
> aayega. Har concept ke saath ek **real-life example (analogy)** diya hai.

---

# 🧱 PART 0: TECHNICAL FOUNDATION (Base Concepts — Yahi se shuru karo)

TDD me ye words baar-baar aate hain. Pehle inhe ek baar acche se samajh lo. Ghabrao mat,
har cheez ka real-life example hai.

## 0.1 Software, Service, aur "Backend" kya hai?

- **Software / Program** = instructions ka set jo computer chalata hai. Jaise WhatsApp ek
  software hai.
- **Backend** = software ka wo hissa jo **peeche (background me)** kaam karta hai — data
  process karna, save karna, logic chalana. User ise seedha nahi dekhta.
- **Frontend** = software ka wo hissa jo **user dekhta hai** — buttons, screens, colors.
  (Jaise WhatsApp ki chat screen frontend hai; message deliver karne ka system backend hai.)

**Analogy 🍽️:** Restaurant socho. **Frontend** = dining hall jahan tum baithte ho, menu
dekhte ho. **Backend** = kitchen jahan khana banta hai. Tum kitchen nahi dekhte, par asli
kaam wahin hota hai.

## 0.2 Microservice kya hai? (Ye project ki reedh ki haddi hai)

Do tareeke se software bana sakte ho:

1. **Monolith (ek bada block):** Poora system ek hi bade program me. Problem: ek jagah
   bug aaye to poora system band; ek hissa badla to poora dobara test karo.

2. **Microservices (chhote-chhote alag services):** Poore system ko **chhote independent
   programs** me tod do. Har program ek kaam karta hai. Wo aapas me messages se baat karte hain.

Is project me **5 microservices** hain: Sensor, Video, Fusion, Feedback, Dashboard.

**Analogy 🏭:** Ek car factory socho. Ek hi banda poori car nahi banata. Alag-alag stations
hain — ek engine lagata hai, ek tyre, ek paint karta hai. Har station apna kaam karta hai,
aur car ek station se doosre pe jaati hai. Agar paint station ruk jaaye, engine station phir
bhi chalta rehta hai. Yahi microservices ka fayda hai — **fault isolation** (ek fail, baaki
theek).

## 0.3 API kya hai? (Bahut zaroori)

**API = Application Programming Interface.** Iska simple matlab: **do programs aapas me kaise
baat karein, uska tareeka/menu.**

**Analogy 🍕:** API ek **restaurant ka menu** hai. Tum kitchen me ghus ke khana nahi banate.
Tum menu se order dete ho ("2 pizza do"), aur kitchen wo bana ke deti hai. Menu tumhe batata
hai **kya maang sakte ho** aur **kaise maangna hai**. Waise hi API batata hai ek program
doosre se kya-kya maang sakta hai.

Is project me dashboard (frontend) backend se data "API" ke through maangta hai — jaise
"aaj ka timeline do", "latest feedback do".

## 0.4 REST API kya hai?

**REST** ek **style/tareeka** hai API banane ka, jo web pe sabse common hai. Isme tum ek
**URL (address)** pe request bhejte ho aur data wapas milta hai.

REST me kuch common "methods" (kaam ke type) hote hain:
- **GET** = data **maango/padho** ("mujhe timeline do"). Kuch badalta nahi.
- **POST** = kuch **naya bhejo/banao** ("ye alert acknowledge kar do").

**Analogy 📮:** REST ek post-office jaisa hai. Tum ek address (URL) pe chitthi (request)
bhejte ho, aur jawab (data) wapas aata hai. **GET** = "mujhe ye info bhejo". **POST** =
"ye info le lo aur save karo".

Example is project se: `GET /api/timeline?from=...&to=...` → matlab "is time range ka
activity timeline do". Wo `/api/timeline` address hai, aur `from`/`to` extra details hain.

## 0.5 WebSocket kya hai? (REST se farq)

REST me **problem ye hai:** tumhe baar-baar poochna padta hai. Jaise har 2 second me
"kuch naya hua? kuch naya hua?". Ye faltu hai.

**WebSocket** ek **hamesha khula connection** hai. Ek baar connect ho gaya, to server **jab
bhi kuch naya ho, khud push kar deta hai** — tumhe poochna nahi padta.

**Analogy 📞:**
- **REST** = SMS bhejna. Har baar naya SMS bhejo, jawab aaye. (Baar-baar poochna.)
- **WebSocket** = phone call jo **chaalu rehti hai**. Jaise hi kuch hota hai, doosra banda
  turant bol deta hai. Live.

Is project me: **live cheezein** (current activity, fall alert) WebSocket se aati hain
(taaki turant dikhe). **Purani history** REST se aati hai (jab dashboard khulta hai).

## 0.6 JSON kya hai? (Data likhne ka format)

**JSON = JavaScript Object Notation.** Ye ek **data likhne ka simple tareeka** hai jise
insaan aur computer dono padh sakein. Isme data **`key: value`** jodo me hota hai.

Example:
```json
{
  "label": "WALKING",
  "confidence": 0.88
}
```
Iska matlab: activity = "WALKING", confidence = 0.88. Bas itna hi. `{ }` ek object hai,
andar `key: value` pairs hain.

**Analogy 📋:** JSON ek **form bharne** jaisa hai jahan har line pe "Naam: Ankit",
"Umar: 21" likha ho. Har cheez ka ek label (key) aur uski value.

Is project me services aapas me JSON messages bhejte hain. Jaise sensor service bolta hai
`{"label": "WALKING", "confidence": 0.88}`.

## 0.7 MQTT aur "Broker" aur "Pub/Sub" kya hai? (Services kaise baat karte hain)

Ye project ka **sabse important communication concept** hai. Dhyaan se.

**Problem:** 5 services hain. Unhe aapas me messages bhejne hain. Agar har service har
doosri service se seedha jude, to bahut uljhan ho jaayegi (spaghetti).

**Solution: MQTT + Broker + Pub/Sub.**

- **MQTT** = ek halka (lightweight) messaging protocol (baat karne ka tareeka).
- **Broker (Mosquitto)** = ek **beech ka post-office/dalaal** jiske through saare messages
  jaate hain. Koi service doosri ko seedha message nahi bhejti — sab broker ko bhejte hain.
- **Publish (Pub)** = ek service broker ko message **bhejti hai** ek "topic" (channel) pe.
- **Subscribe (Sub)** = ek service broker se bolti hai "mujhe is topic ke saare messages
  do". Jab bhi us topic pe message aata hai, use mil jaata hai.
- **Topic** = ek channel/naam jispe messages jaate hain. Jaise `har/sensor/prediction`.

**Analogy 📺:** YouTube socho. Ek creator **video daalta hai** (publish) apne channel pe.
Tum us channel ko **subscribe** karte ho. Jab bhi wo naya video daalta hai, tumhe **mil
jaata hai** — creator ko har subscriber ko personally bhejna nahi padta. YouTube (broker)
beech me sab sambhaal leta hai.

Isi tarah:
- Sensor Service `har/sensor/prediction` topic pe message **publish** karta hai.
- Fusion Service us topic ko **subscribe** kiya hua hai, to use message **mil jaata hai**.
- Dono ek doosre ko seedha jaante bhi nahi — sirf broker aur topic ke through jude hain.
  Ise **"loosely coupled"** kehte hain (dheele se jude, ek badle to doosra na toote).

## 0.8 Database aur PostgreSQL kya hai?

**Database** = data ko **organized tareeke se permanently save** karne ki jagah. Jaise ek
digital almari jisme sab kuch table (row/column) me rakha ho.

**PostgreSQL (short: "Postgres")** = ek **free, powerful database software**. Ye
**relational database** hai — matlab data **tables** me hota hai (Excel sheet jaisa,
rows aur columns).

**Analogy 📚:** Database ek **library** jaisa hai. Har kitaab (data) ek shelf (table) pe
organized hai. Tum kisi bhi kitaab ko dhoondh sakte ho, nayi rakh sakte ho, purani padh
sakte ho.

Is project me PostgreSQL me 3 tables hain: `activity_timeline` (kya-kya activity hui),
`events` (falls/alerts), `feedback` (AI ke messages). Isse system band hoke chalu ho to bhi
data bacha rehta hai (**persistence**).

**Table, Row, Column samjho:**
- **Table** = ek sheet (jaise "activity_timeline").
- **Column** = ek field (jaise "activity", "confidence", "time").
- **Row** = ek entry (jaise "10:00 baje - WALKING - 0.88 confidence").

## 0.9 FastAPI, Uvicorn, Python kya hai?

- **Python** = ek programming language (code likhne ki bhasha). Easy aur popular. Poore
  backend ki bhasha yahi hai.
- **FastAPI** = Python ka ek **framework (ready-made toolkit)** jisse REST API aur WebSocket
  jaldi banaye ja sakte hain. Har service ek chhota FastAPI app hai.
- **Uvicorn** = wo program jo FastAPI app ko **chalata (run/serve)** karta hai.

**Analogy 🏗️:** Framework ek **ready-made ghar ka dhaancha** hai. Tumhe zero se deewar
nahi banani padti — dhaancha ready hai, tum bas apna kaam add karte ho. FastAPI backend ka
dhaancha deta hai.

## 0.10 React, Vite, Recharts kya hai? (Frontend ke tools)

- **React** = ek popular tool (library) frontend (jo user dekhta hai) banane ke liye. Isse
  interactive screens banti hain.
- **Vite** = ek tool jo React app ko fast develop aur run karne me madad karta hai.
- **Recharts** = React ke liye **charts/graphs** banane ka tool (pie chart, bar chart).
- **SPA (Single Page Application)** = aisa web app jahan page reload nahi hota; sab kuch ek
  hi page pe smoothly update hota hai (jaise Gmail).

**Analogy 🎨:** React frontend banane ke rangoon aur brush deta hai. Recharts se tum data ko
sundar graphs me dikhate ho.

## 0.11 Docker aur docker-compose kya hai? (One-command start ka raaz)

**Problem:** 5 services + database + broker sab alag-alag setup karna, har computer pe alag
issue — bahut mushkil.

**Docker** = har service ko ek **"container" (dabba)** me pack kar deta hai. Container me
service + uske saare zaroori tools ek saath packed hote hain. Ye container **kisi bhi computer
pe same tarah chalta hai**.

**docker-compose** = ek tool jo ek command se **saare containers ek saath** chala deta hai.
Isliye `docker-compose up` se poora system ek command me start hota hai.

**Analogy 📦:** Docker container ek **tiffin box** jaisa hai. Khana + chammach + napkin sab
ek dabbe me packed. Kahin bhi le jaao, kholo, khao — koi jhanjhat nahi. `docker-compose` =
ek bag jisme saare tiffin box ek saath — ek jhatke me sab ready.

## 0.12 Pre-trained Model aur Inference kya hai?

- **Model (AI/ML model)** = ek program jo data se pattern seekh chuka hai aur predictions
  deta hai. Jaise ek model jo image dekh ke bata de "ye billi hai ya kutta".
- **Training** = model ko sikhaana (bahut data dikha ke). Ye mushkil, mehanga, time-lene wala
  hota hai. **Hum ye NAHI karenge.**
- **Pre-trained model** = kisi aur ne pehle se sikha ke ready rakha model. Hum use bas
  download karke **use** karte hain.
- **Inference** = trained model se prediction lena (use karna). **Hum sirf inference karenge.**

**Analogy 🎓:** Training = school jaake padhna (saalon lagta hai). Inference = padhe-likhe
banda se sawaal poochna (turant jawab). Hum kisi ko school nahi bhej rahe; hum ek pehle se
padhe-likhe expert (pre-trained model) se bas sawaal pooch rahe hain.

**Ye project ka golden rule:** Sirf pre-trained models, sirf inference. **No training.**

## 0.13 IMU, Accelerometer, Gyroscope, Pose, Landmark (sensor/video ke basics)

- **IMU (Inertial Measurement Unit)** = ek sensor jo motion naapta hai. Isme do cheezein:
  - **Accelerometer** = seedhi motion / jhatka naapta hai (kis direction me kitna tez hile).
  - **Gyroscope** = ghoomna/rotation naapta hai.
  - (Tumhare phone me bhi ye hote hain — isliye phone ghumaane pe screen ghoomti hai.)
- **Pose estimation** = camera image se body ke joints ki position nikaalna.
- **Landmark** = body ka ek point (jaise left shoulder), jiske paas coordinates hote hain:
  `(x, y, z, visibility)`.
  - **x, y** = screen pe position (left-right, up-down).
  - **z** = depth (kitna aage/peeche).
  - **visibility** = wo point dikh raha hai ya chhupa (0 se 1).
- **MediaPipe Pose** = Google ka free tool jo ek image se **33 body landmarks** nikaal deta hai.

**Analogy 🕺:** Socho ek insaan ke body pe 33 chamakte points lage hain (kandha, kohni,
ghutna, etc.). Camera in points ki position padhti hai. In points ke angle dekh ke pata
chalta hai banda khada hai, baitha hai, ya leta hai.

## 0.14 LLM, GenAI, Ollama kya hai?

- **LLM (Large Language Model)** = ChatGPT jaisa AI jo insaani bhasha samajhta aur likhta
  hai. **GenAI (Generative AI)** = AI jo naya content (text) generate karta hai.
- **Ollama** = ek free tool jo open-source LLMs (jaise Llama, Qwen) ko **tumhare laptop pe
  locally** chalata hai — bina internet, bina paise.
- Alternatively, **Cloud APIs** (Gemini, GPT, Claude) — ye zyada smart par internet + paise
  (API key) chahiye.

**Analogy ✍️:** LLM ek smart writer hai. Tum use raw data do ("patient 3 ghante baitha,
20 min chala"), aur wo ek acchi simple advice likh deta hai caregiver ke liye.

---

> ✅ **Yahan tak agar samajh aa gaya, to aage ka poora document aasan lagega.** Ab document ke
> asli sections shuru. Har jagah upar wale concepts hi ghoom-phir ke aayenge.

---

# SECTION 1: ARCHITECTURE OVERVIEW (System ka poora naksha)

**Architecture** = system ka overall design/naksha — kaun se hisse hain aur wo kaise jude hain.

## 1.1 Design Principles (5 mool soch)

Ye 5 rules poore system ke banane ke pattern hain:

1. **Software-only Model.** Sab kuch software me — camera/webcam se video, aur nakli
   (simulated) sensor. **Koi physical IoT hardware nahi.**

2. **No model training.** Saare AI parts sirf **pre-trained models** use karte hain
   (inference only). Open-source (local, private, offline) ya closed-source cloud API (zyada
   accurate) dono option.

3. **Microservices Architecture.** 5 independent services, **MQTT pub/sub broker** se dheele
   se jude (loosely coupled). Fayda: alag-alag develop/deploy, aur fault isolation.

4. **Privacy by construction.** Video service webcam locally process karta hai aur sirf
   **numeric landmarks** bhejta hai. **Raw video frames turant delete, kabhi save nahi.**

5. **Robust Persistence.** **PostgreSQL** central database — timeline, alerts, events,
   feedback sab store.

> "By construction" ka matlab: privacy design me hi built-in hai, baad me add nahi ki.
> Video kabhi bahar jaa hi nahi sakti kyunki service use bhejti hi nahi.

## 1.2 Component Diagram (kaun kaun se dabbe kaise jude — samjho)

Diagram me ye ho raha hai (upar se neeche):

- **Inputs (data ke source):**
  - `CAM` = Laptop Webcam → Video Service ko frames deta hai.
  - `SIM` = Sensor Simulator → jo UCI-HAR / WISDM / SisFall dataset **replay** karta hai
    (nakli sensor data).

- **Services (4 backend microservices):**
  - `VID` = Video Service (MediaPipe Pose + geometric rules).
  - `SEN` = Sensor Service (features + pre-trained HuggingFace HAR model).
  - `FUS` = Fusion/HAR Service (confidence-weighted voting + fall logic).
  - `FB` = Feedback Service (Ollama local LLM ya cloud API).

- **Beech ka post-office:** `BROKER` = Mosquitto MQTT Broker (saare messages iske through).

- **Storage aur UI:**
  - `DB` = PostgreSQL (timeline + events).
  - `DASH` = Dashboard (React + Vite + Recharts).

**Data kaise behta hai (arrows ka matlab):**
- Webcam → Video Service (frames).
- Simulator → Broker pe `sensor/raw` publish karta hai.
- Video Service → Broker pe `video/prediction` publish.
- Sensor Service → Broker se raw leta hai, phir `sensor/prediction` publish.
- Fusion → Broker se dono predictions leta hai; phir `har/activity` aur `har/event` publish;
  aur seedha DB me likhta hai.
- Feedback → Broker se events leta hai; DB me feedback likhta hai; Dashboard ko REST+WebSocket
  se bhejta hai.
- Dashboard → Fusion aur Feedback se REST+WebSocket se data leta hai; DB se history.

> Sab kuch **broker ke through** ja raha hai — yahi loosely-coupled microservices ka asli
> roop hai. Har service sirf apna kaam jaanta hai; kis ko message mila, ye broker sambhaalta.

## 1.3 Runtime Data Flow (step-by-step kahani) ⭐

Ye 6 steps poore system ki live kahani hai. Ise yaad kar lo:

1. **Simulator** raw IMU windows MQTT pe publish karta hai (topic: `har/sensor/raw`).

2. **Sensor Service** raw windows leta hai → features nikaalta hai → pre-trained HF HAR model
   chalata hai → `{label, confidence}` ko `har/sensor/prediction` pe publish karta hai.

3. **Video Service** webcam/video padhta hai → MediaPipe/YOLO se landmarks → geometric posture
   rules → `{label, confidence, orientation}` ko `har/video/prediction` pe publish karta hai.

4. **Fusion Service** dono prediction streams ko **time-align** karta hai → confidence-weighted
   vote + temporal smoothing → fall logic → `har/activity` (continuous) aur `har/event`
   (fall/abnormal) publish karta hai, aur dono **PostgreSQL** me likhta hai.

5. **Feedback Service** events subscribe karta hai + timeline periodically padhta hai →
   **LLM** (local Ollama ya cloud API) ko prompt bhejta hai → structured feedback/alert/summary
   banata hai → **PostgreSQL** me store + dashboard ko bhejta hai.

6. **Dashboard** sab kuch live **WebSocket** se dikhata hai, aur history **REST** endpoints se
   padhta hai (jo PostgreSQL se aati hai).

---

# SECTION 2: TECHNOLOGY STACK (Kaun se tools, kya kaam, license)

**Tech stack** = un saare tools/technologies ki list jo project me use ho rahe hain.

Yahan table me har "layer" (system ka level) ke tools diye hain. Important samajh:

| Layer (level) | Tool | Kaam (easy me) |
|---|---|---|
| Backend Language | **Python 3.11+** | Saare services + simulator ki bhasha. |
| Web framework | **FastAPI + Uvicorn** | Har service ke REST + WebSocket endpoints. |
| Pose (Open) | **MediaPipe / YOLOv8 / YOLOv11 Pose** | Video se body landmarks (free, local). |
| Pose (Closed) | **Google Cloud Video Intelligence / Azure Vision** | Cloud se pose (paid). |
| Vision I/O | **OpenCV** | Webcam se frame capture karna. |
| Sensor model | **HuggingFace Transformers / Hub** | Pre-trained HAR model load + run. |
| Numerics | **NumPy, SciPy, pandas** | Feature nikaalna, windowing, dataset replay. |
| GenAI (Open) | **Ollama (Llama 3.2, Qwen2.5, Phi-3-mini)** | Local LLM, offline, free. |
| GenAI (Closed) | **Gemini / GPT-4o-mini / Claude 3.5** | Cloud LLM (paid, zyada accurate). |
| Messaging | **Mosquitto (broker) + paho-mqtt (client)** | Services ke beech pub/sub. |
| Database | **PostgreSQL** | Timeline, events, feedback store. |
| Frontend | **React + Vite** | Dashboard ki screens. |
| Charts | **Recharts** | Trend/timeline graphs. |
| Realtime UI | **WebSocket** | Dashboard pe live updates. |
| Orchestration | **Docker + docker-compose** | One-command start. |
| Testing | **pytest** | Tests + metrics harness. |

> **License / Pricing** column ka matlab: batata hai tool **free/open-source** hai (jaise
> MIT, Apache-2.0, BSD — ye free licenses ke naam hain) ya **paid** (cloud APIs). Project ka
> goal free rehna hai, par paid cloud option bhi allowed hai agar team chahe.

**Closed-Source Notice:** Cloud models (Gemini, GPT, Azure) ke liye **internet + valid API
key (paise wali)** chahiye. Open-source (Ollama, MediaPipe) **poori tarah local, offline,
free** chalte hain.

## 2.1 Pre-trained Models — kaunse aur kaise use honge

Har modality ke liye do options (open free / closed paid) aur "kaise use hote hain":

- **Video:**
  - Open: MediaPipe Pose (33 landmarks) ya YOLOv8/v11 Pose.
  - Closed: Google Cloud Video Intelligence ya Azure.
  - **Use:** body joint coordinates nikaalo → deterministic geometric rules se batao
    sitting/standing/walking/lying/falling.

- **Sensor:**
  - Open: HuggingFace se pre-trained HAR classifier (CNN/LSTM/Transformer).
  - Closed: Google Cloud AutoML ya custom cloud endpoint.
  - **Use:** sensor window ke features classify karo → `{label, confidence}`. Model na chale
    to statistical rules ya LLM zero-shot fallback.

- **Feedback:**
  - Open: Llama 3.2 (1B/3B), Qwen2.5, Phi-3-mini via Ollama.
  - Closed: Gemini 1.5 Flash, GPT-4o-mini, Claude 3 Haiku.
  - **Use:** database ke structured timeline se natural-language feedback/alert/summary banao.

> **CNN vs LSTM vs Transformer (halki si samajh):** ye teeno neural network ke types hain.
> - **CNN** = patterns/shapes pehchanne me accha.
> - **LSTM** = **sequence/time-series** (jo cheez time ke saath aati hai) me accha — sensor
>   data time ke saath aata hai, isliye LSTM fit hota hai.
> - **Transformer** = aajkal ka sabse powerful (ChatGPT bhi transformer hai).
> Tumhe inhe banana nahi hai — bas ready-made use karna hai.
>
> **Zero-shot** = model ko bina koi example diye, sidhe kaam karwa lena (jaise LLM se pooch
> lo "ye data konsi activity hai?" bina training ke).

---

# SECTION 3: PER-SERVICE DESIGN (Har service ke andar kya hota hai)

**Common baat:** har service ek chhota FastAPI app hai; paho-mqtt se publish/subscribe karta
hai; config environment variables/config file se padhta hai (FR-X4); structured logs likhta
hai (NFR-10).

> **Environment variable** = ek setting jo code ke bahar rakhi jaati hai (jaise ek chit pe
> "WINDOW_SIZE = 128"). Isse code chhue bina behaviour badla ja sakta hai.
> **Log** = service jo kar rahi hai uska record/diary (debugging ke liye).

## 3.1 Sensor Service (FR-S1…FR-S6)

- **Kaam:** raw IMU windows ko activity predictions me badalna.
- **Input:** MQTT `har/sensor/raw` — accelerometer/gyroscope samples ke windows (simulator se).
- **Output:** MQTT `har/sensor/prediction` — `{label, confidence, motion_intensity, ts}`.
  (`ts` = timestamp = kis time ka data.)
- **Pipeline (steps):**
  1. **Windowing:** sliding windows **1–2 second** ke, **50–100 Hz** pe (jaise 128 samples,
     50% overlap).
  2. **Feature extraction** (har axis + magnitude ke liye): **mean, std, min, max, SMA (Signal
     Magnitude Area), energy, axes ke beech correlation, tilt/orientation angles**. (NumPy/SciPy se.)
  3. **Classification:** pre-trained HF HAR model → label + confidence. Model ke labels ko
     hamare classes pe **map** karo.
  4. **Motion-intensity signal:** window me acceleration-magnitude ka peak (fall logic ko
     feed hota hai, FR-S5).
  5. Prediction publish karo.
- **Failure modes:** model load na ho → statistical/zero-shot fallback (FR-S6); khaali window
  → `UNKNOWN` bhejo.
- **Config:** `WINDOW_SIZE`, `WINDOW_OVERLAP`, `SENSOR_MODEL_ID`, `USE_FALLBACK`.

> **Zaroori terms:**
> - **Hz (Hertz)** = per second kitni baar. 50 Hz = 1 second me 50 readings.
> - **Sliding window + overlap:** data ko chunks me todte hain. "50% overlap" matlab har
>   naya window pichle window ka aadha hissa dobara leta hai (taaki beech ki activity miss
>   na ho). Socho ek chalti hui khidki data ke upar se guzarti hai.
> - **Feature (mean/std/etc.):** raw numbers se nikaali summary. **mean** = average,
>   **std** = kitna bikhra hua, **SMA/energy** = kitni total motion. Model raw ke bajaye ye
>   summary padhta hai (chhota + saaf).

## 3.2 Video Service (FR-V1…FR-V8)

- **Kaam:** webcam frames ko posture predictions me badalna — **bina video store kiye**.
- **Input:** Webcam frames (OpenCV se); **kabhi publish ya save nahi**.
- **Output:** MQTT `har/video/prediction` — `{label, confidence, orientation, ts}`.
- **Pipeline:**
  1. Frames capture **10–15 FPS** pe (OpenCV).
  2. **MediaPipe Pose** → har frame me 33 landmarks `(x, y, z, visibility)`.
  3. **Geometric features:** torso ka vertical-axis angle (seedha vs horizontal), hip/knee ke
     **joint angles**, shoulder-hip alignment, sar-se-farsh proxy, key joints ka vertical motion
     across frames (walking/exercising vs static ke liye).
  4. **Rule-based posture classification** (deterministic, no training):
     - `LYING` agar torso ≈ horizontal.
     - `SITTING` vs `STANDING` — hip/knee flexion + torso height ratio se (dono me torso vertical).
     - `WALKING` agar short window me periodic horizontal displacement / leg alternation.
     - `EXERCISING` agar high repetitive multi-joint motion.
     - warna `UNKNOWN`.
  5. **Orientation flag** (`vertical`/`horizontal`) fall logic ke liye (FR-V7).
  6. **Privacy:** landmark nikaalte hi har frame turant delete; sirf numbers bahar (FR-V5, NFR-3).
- **Failure modes:** koi na dikhe → `UNKNOWN` low confidence (FR-V8); webcam na mile → log +
  service zinda rakho (sensor-only fusion chalta rahe).
- **Config:** `FPS`, `HORIZONTAL_ANGLE_THRESHOLD`, `MIN_VISIBILITY`, `CAMERA_INDEX`.

> **FPS (Frames Per Second)** = 1 second me kitni images. 12 FPS = 1 second me 12 photo.
> **Flexion** = jodo ka mudna (ghutna/hip kitna muda). Baithne me ghutna zyada muda hota hai.
> **Ye service ML nahi, sirf geometry (angle/position ki maths) use karti hai** — isliye koi
> training nahi chahiye. Yahi hamari constraint ke saath fit hai.

## 3.3 Fusion / HAR Service (FR-F1…FR-F7) — System ka Dimaag 🧠

- **Kaam:** ek final "official" activity + events banana.
- **Inputs:** MQTT `har/sensor/prediction`, `har/video/prediction`.
- **Outputs:** MQTT `har/activity` (continuous), `har/event` (fall/abnormal); PostgreSQL me likhna.
- **Algorithm (steps):**
  1. **Time alignment:** har modality ke recent predictions ko buffer me rakho; timestamp se
     align karke intervals (jaise 1 sec) banao.
  2. **Confidence-weighted late fusion:** har candidate label ka score =
     `Σ (confidence_modality × weight_modality)`; jiska score sabse zyada wo jeet. Weights
     configurable (default sensor 0.5 / video 0.5). Ek modality na ho to doosri use karo (FR-F7).
  3. **Temporal smoothing:** pichle *N* fused intervals pe majority/hysteresis — taaki ek noisy
     interval label na palte (FR-F3).
  4. **Fall detection rule (FR-F4):** `FALL` raise karo jab **sensor motion_intensity > spike
     threshold** **AUR** **video orientation == horizontal** — ek hi short window me; agar sirf
     ek condition ho to suppress (false-alarm control, NFR-2). Smoothing duplicate alerts rokta hai.
  5. **Abnormal/inactivity (FR-F6):** time-in-activity track karo; stillness threshold ke baad
     `INACTIVITY`; baseline se bada deviation ho to `ABNORMAL_PATTERN`.
  6. Har fused activity + event PostgreSQL me save; dashboard ko publish.
- **Config:** `MODALITY_WEIGHTS`, `SMOOTHING_WINDOW`, `FALL_ACCEL_THRESHOLD`,
  `INACTIVITY_SECONDS`, `FUSION_INTERVAL`.

> **Confidence-weighted fusion ka maths, example se:**
> Maano ek interval me:
> - Sensor bola "WALKING" confidence 0.6, weight 0.5 → WALKING ko 0.6 × 0.5 = **0.30**.
> - Video bola "STANDING" confidence 0.9, weight 0.5 → STANDING ko 0.9 × 0.5 = **0.45**.
> - STANDING ka score (0.45) > WALKING ka (0.30), to **final = STANDING**.
> Yahi "jo zyada confident, uski zyada chalti hai".
>
> **Late fusion** = pehle har modality **alag** predict kare, phir **baad me** unke predictions
> mila do. (Iska ulta "early fusion" hota hai — raw data pehle mila do — par hum late use karte hain.)
>
> **Hysteresis / smoothing** = ek short blip pe label na badlo. Jaise thermostat: thoda
> temperature upar-neeche ho to AC baar-baar on-off nahi hota.

## 3.4 Feedback Service (GenAI) (FR-G1…FR-G6)

- **Kaam:** GenAI model se simple-language feedback, alert text, aur summaries banana.
- **Inputs:** MQTT `har/event` (turant alert text ke liye); PostgreSQL timeline periodically padhna.
- **Outputs:** Structured feedback objects → PostgreSQL me + dashboard ko WebSocket/REST se push.
- **LLM integration:** ya to local **Ollama** API (open models jaise Llama 3.2 3B) ya cloud API
  (Gemini/GPT/Claude). Prompts **templates + structured (JSON) output** use karte hain taaki
  dashboard fields reliably dikha sake (FR-G5).
- **Prompt design (LLM ko kaise bola jaata hai):**
  - *System role:* "Tum ek careful assistant ho jo caregiver ke liye patient ki recent activity
    summarize karta hai. Concise raho, plain language use karo, **kabhi diagnose mat karo**,
    **hamesha ek short safety disclaimer do**, aur medical concern pe professional se milne bolo."
    (FR-G4, NFR-11)
  - *User content:* recent timeline / triggering event ka compact structured digest.
  - *Required output fields:* `headline`, `detail`, `severity` (`info|warning|critical`),
    `recommendations[]`, `disclaimer`.
- **Modes (3 kaam):**
  - **Alert mode** (`FALL`/abnormal pe): chhota, urgent, structured alert (FR-G2).
  - **Feedback mode** (on demand/periodic): recent pattern se advice (FR-G1).
  - **Summary mode** (scheduled): daily/periodic recap (FR-G3).
- **Failure modes:** LLM na mile → template-based fallback text (dashboard fir bhi kuch dikhaye);
  model pull hone ke baad offline chalta hai (FR-G6, NFR-8).
- **Config:** `LLM_MODEL`, `OLLAMA_HOST`, `GEMINI_API_KEY`/`OPENAI_API_KEY`, `FEEDBACK_INTERVAL`,
  `SUMMARY_SCHEDULE`.

> **Prompt** = LLM ko diya gaya instruction/sawaal. **System role** = LLM ko uski "personality
> aur rules" batana (jaise "diagnose mat karna"). **Template** = ek ready format jisme bas
> details bhar do.
> **Structured (JSON) output kyun:** taaki har cheez apni jagah ho — `headline` alag,
> `disclaimer` alag — aur dashboard use theek se dikha sake.

## 3.5 Dashboard Service (FR-D1…FR-D7)

- **Stack:** React + Vite SPA; Recharts charts; native WebSocket (live); REST (history).
- **Component tree (screen ke hisse):**
  ```
  App
  ├── StatusBar          (system/modality health — FR-D6)
  ├── FallAlertBanner    (live critical alert — FR-D2)
  ├── LiveMonitor        (current activity card — FR-D1)
  ├── ActivityTimeline   (history list/bar — FR-D3)
  ├── TrendsPanel        (Recharts graphs — FR-D4)
  ├── AIFeedbackPanel    (GenAI feedback + summary — FR-D5)
  └── AlertsLog          (event list + acknowledge — FR-D7)
  ```
- **Data sources:** live ke liye WebSocket (`activity`, `event`, `feedback`); load pe history
  ke liye REST (timeline/trends/history).
- **Backend-for-frontend:** Fusion aur Feedback services REST/WebSocket endpoints dete hain; ek
  patla gateway inhe aggregate kar sakta hai (optional).

> **Component** = React me screen ka ek reusable tukda (jaise ek card, ek banner). Poori screen
> chhote components se banti hai (Lego blocks ki tarah).
> **Gateway** = ek beech ka darwaza jo kai services ka data ek jagah jod de (optional yahan).

---

# SECTION 4: DATA CONTRACTS (Messages ka exact format — "sabki language ek")

**Data contract** = ek pakka agreement ki messages **kis format me** honge. Isse har service
ek doosre ko samajhti hai (koi confusion nahi).

## 4.1 MQTT Topics (kaun sa channel, kaun bhejta, kaun sunta)

| Topic | Publisher (bhejne wala) | Subscriber (sunne wale) | Kya |
|---|---|---|---|
| `har/sensor/raw` | Simulator (ya ESP32) | Sensor Service | Raw IMU window |
| `har/sensor/prediction` | Sensor Service | Fusion Service | Sensor prediction |
| `har/video/prediction` | Video Service | Fusion Service | Video prediction |
| `har/activity` | Fusion Service | Feedback, Dashboard | Fused current activity |
| `har/event` | Fusion Service | Feedback, Dashboard | Fall/abnormal/inactivity event |
| `har/feedback` | Feedback Service | Dashboard | GenAI feedback object |

> Topic ka naam ek "raasta" jaisa hai (`har/sensor/raw`). `har` = project ka naam. Isse
> messages organized rehte hain.

## 4.2 JSON Message Formats (asli messages kaise dikhte hain)

Har message JSON me hota hai. Chalo padhte hain (mushkil nahi, bas key:value):

**`har/sensor/raw`** (simulator se raw data):
```json
{
  "ts": "2026-06-20T10:00:00.000Z",
  "device_id": "sim-01",
  "sampling_hz": 50,
  "window": {
    "accel": [[ax, ay, az], "...128 samples..."],
    "gyro":  [[gx, gy, gz], "...128 samples..."]
  }
}
```
Matlab: is time (`ts`) pe, device "sim-01" se, 50 Hz pe, ek window jisme 128 accelerometer aur
128 gyroscope readings hain (har reading me 3 axis: x, y, z).

**`har/sensor/prediction`** (sensor service ka jawab):
```json
{ "ts": "...", "modality": "sensor", "label": "WALKING", "confidence": 0.88, "motion_intensity": 0.31 }
```
Matlab: sensor bolta hai "WALKING, 88% confidence, motion 0.31".

**`har/video/prediction`** (video service ka jawab):
```json
{ "ts": "...", "modality": "video", "label": "LYING", "confidence": 0.82, "orientation": "horizontal" }
```
Matlab: video bolta hai "LYING, 82% confidence, body horizontal".

**`har/activity`** (fusion ka final decision):
```json
{ "ts": "...", "activity": "WALKING", "confidence": 0.90,
  "contributors": { "sensor": "WALKING", "video": "WALKING" } }
```
Matlab: final activity = WALKING (90%), aur ye batata hai dono modalities ne kya kaha.

**`har/event`** (fall/abnormal event):
```json
{ "ts": "...", "type": "FALL", "severity": "critical", "confidence": 0.93,
  "evidence": { "motion_intensity": 0.95, "orientation": "horizontal" } }
```
Matlab: FALL hua, critical, 93% confident, saboot (evidence) = high motion + horizontal.

**`har/feedback`** (AI ka message):
```json
{ "ts": "...", "mode": "alert",
  "headline": "Possible fall detected",
  "detail": "A sudden movement followed by a lying position was detected at 10:00.",
  "severity": "critical",
  "recommendations": ["Check on the patient immediately."],
  "disclaimer": "This is an automated assistive tool and not a medical diagnosis." }
```
Matlab: alert mode ka AI message — headline, detail, severity, recommendation, aur **disclaimer**.

> **Note:** activity labels har jagah wahi FSD wale hain: `WALKING, SITTING, STANDING, LYING,
> EXERCISING, UNKNOWN`. Events: `FALL, INACTIVITY, ABNORMAL_PATTERN`. Sab consistent.

## 4.3 REST + WebSocket API (Dashboard ke liye)

| Method | Path | Service | Kaam |
|---|---|---|---|
| `GET` | `/api/status` | Fusion/gateway | Current activity + health (FR-D1, FR-D6) |
| `GET` | `/api/timeline?from=&to=` | Fusion/gateway | Range ka activity history (FR-D3) |
| `GET` | `/api/trends?period=` | Fusion/gateway | Per-activity time / over-time (FR-D4) |
| `GET` | `/api/events?from=&to=` | Fusion/gateway | Event/alert log (FR-D2, FR-D7) |
| `POST` | `/api/events/{id}/ack` | Fusion/gateway | Alert acknowledge (FR-D7) |
| `GET` | `/api/feedback/latest` | Feedback | Latest AI feedback (FR-D5) |
| `POST` | `/api/feedback/generate` | Feedback | On-demand feedback/summary (FR-G1, FR-G3) |
| `WS` | `/ws` | Fusion + Feedback | Live stream: activity, event, feedback |

**WebSocket event envelope** (live message ka lifafa):
```json
{ "channel": "event", "data": { "...upar wale JSON me se koi..." } }
```
Matlab: har live message me ek `channel` (kis type ka) aur `data` (asli content) hota hai.

> `?from=&to=` = URL me extra details (parameters). Jaise "10 baje se 11 baje tak ka do".
> `{id}` = ek specific event ka number. `POST .../ack` = "ye alert maine dekh liya" mark karna.

## 4.4 PostgreSQL Schema (Database ke tables ka design)

**Schema / DDL** = database ke tables ka design (kaun sa table, kaun se columns).
**DDL (Data Definition Language)** = wo SQL commands jo table banate hain.

3 tables hain:

**Table 1: `activity_timeline`** (har activity ka record)
```sql
CREATE TABLE activity_timeline (
  id           SERIAL PRIMARY KEY,        -- har row ka unique number (auto badhta)
  ts           TIMESTAMPTZ NOT NULL,      -- time (timezone ke saath)
  activity     VARCHAR(20) NOT NULL,      -- WALKING|SITTING|STANDING|LYING|EXERCISING|UNKNOWN
  confidence   DOUBLE PRECISION NOT NULL, -- kitna confident (decimal number)
  sensor_label VARCHAR(20),               -- sensor ne kya kaha
  video_label  VARCHAR(20)                -- video ne kya kaha
);
```

**Table 2: `events`** (falls aur alerts)
```sql
CREATE TABLE events (
  id           SERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  type         VARCHAR(20) NOT NULL,      -- FALL|INACTIVITY|ABNORMAL_PATTERN
  severity     VARCHAR(10) NOT NULL,      -- info|warning|critical
  confidence   DOUBLE PRECISION NOT NULL,
  evidence     JSONB,                     -- extra details (flexible JSON)
  acknowledged BOOLEAN NOT NULL DEFAULT FALSE  -- dekha gaya? default: nahi
);
```

**Table 3: `feedback`** (AI ke messages)
```sql
CREATE TABLE feedback (
  id           SERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  mode         VARCHAR(20) NOT NULL,      -- alert|feedback|summary
  headline     VARCHAR(100),
  detail       TEXT,
  severity     VARCHAR(10),
  payload      JSONB                      -- poora JSON (recommendations[], disclaimer, etc.)
);

CREATE INDEX idx_timeline_ts ON activity_timeline(ts);  -- time se dhoondhna fast
CREATE INDEX idx_events_ts   ON events(ts);
```

> **Column types samjho:**
> - **SERIAL PRIMARY KEY** = auto-badhne wala unique ID (1, 2, 3...). Har row ki pehchaan.
> - **TIMESTAMPTZ** = timezone-aware time (kaunse time zone me kab).
> - **VARCHAR(20)** = text max 20 characters.
> - **DOUBLE PRECISION** = decimal number (jaise 0.88).
> - **BOOLEAN** = sirf true/false.
> - **JSONB** = ek flexible JSON blob (jab structure fixed na ho).
> - **INDEX** = ek "shortcut" jo dhoondhna fast karta hai (kitaab ki index jaisa). Yahan time
>   (`ts`) pe index hai kyunki hum aksar time se search karte hain.

---

# SECTION 5: DATASETS & CLASS MAPPING (Nakli data kahaan se aata hai)

## 5.1 Public Datasets (free, simulator + metrics ke liye)

Kyunki hardware nahi hai, hum **ready-made public datasets** use karte hain jinme real sensor
data pehle se labeled hai:

| Dataset | Kya hai | Yahan use |
|---|---|---|
| **UCI HAR** | Smartphone accel/gyro, 6 daily activities, labeled. | Default activity replay & metrics. |
| **WISDM** | Accelerometer activities (walking, sitting, etc.). | Alternative activity replay. |
| **SisFall** | Falls + normal activities (elderly-relevant). | **Fall** scenarios ke liye. |

Simulator chosen dataset ke samples real-time me `har/sensor/raw` pe replay karta hai, aur
**ground-truth labels** rakhta hai metrics ke liye. Datasets `data/` folder me (gitignored).

> **Labeled dataset** = data jiske saath sahi jawab already likha hai (jaise "ye window
> WALKING hai"). Isse hum accuracy naap sakte hain.
> **Gitignored** = ye files git (version control) me upload nahi hoti (kyunki bhaari hoti hain).

## 5.2 Label Mapping (dataset ke labels ko hamare 6 classes pe milana)

Har dataset ke apne label naam hote hain, jo hamare 6 classes se alag ho sakte hain. Ek
**mapping table** (`shared/` me) har source label ko hamare canonical set pe map karta hai.

Example: UCI ka `WALKING / WALKING_UPSTAIRS / WALKING_DOWNSTAIRS` → sab hamare `WALKING`.
`LAYING → LYING`. Jo map na ho → `UNKNOWN`. SisFall ke fall scenarios → `FALL` event path
(motion spike + horizontal).

> **Canonical set** = hamara official standard set (`WALKING, SITTING, STANDING, LYING,
> EXERCISING, UNKNOWN`). Sab kuch isi pe convert hota hai taaki consistency rahe.

---

# SECTION 6: REPOSITORY / FOLDER STRUCTURE (Code kis folder me kahaan)

**Repository (repo)** = poore project ke code ka folder. Ye batata hai kaun sa code kahaan hai:

```
HAR-System/
├── core_docs/              # documentation (ye docs yahin hain)
├── services/               # 4 backend microservices
│   ├── sensor_service/     # app.py, features.py, classifier.py, config.py
│   ├── video_service/      # app.py, pose.py, rules.py, config.py
│   ├── fusion_service/     # app.py, fusion.py, falldetect.py, config.py
│   └── feedback_service/   # app.py, llm.py, config.py
├── simulator/              # dataset ko MQTT pe replay karta hai
├── shared/                 # sabme common: schemas, topics, labels, db helpers
├── dashboard/              # React + Vite frontend
├── data/                   # downloaded datasets (gitignored)
├── tests/                  # pytest tests + metrics harness
├── docker-compose.yml      # sab ek saath chalane ki file
├── .env.example            # config defaults
└── README.md               # project intro
```

Har service ka **ek folder** (1:1). `shared/` me common contracts (schemas, topics, labels, DB)
taaki saari services ek jaisa samjhein — **single source of truth**.

> **Har service ke files ka kaam:**
> - `app.py` = main file (FastAPI app + MQTT loop).
> - `features.py`/`pose.py`/`fusion.py` = us service ka core logic.
> - `config.py` = settings.
> **Single source of truth** = ek jagah jahan common cheezein rakhi hain, taaki sab same page
> pe rahein (do jagah alag definition ka jhagda na ho).

---

# SECTION 7: CONFIGURATION (Bina code chhue settings badalna)

Saari tunable settings **environment variables** hain (`.env.example` me documented). Isse
FR-X4 / NFR-9 pura hota hai — behaviour config se badlo, code se nahi.

Kuch important variables:

| Variable | Default | Kaun use | Kya |
|---|---|---|---|
| `MQTT_HOST` / `MQTT_PORT` | `localhost` / `1883` | all | Broker ka address/port. |
| `DATABASE_URL` | `postgresql://...` | fusion, feedback | Database ka connection. |
| `WINDOW_SIZE` / `WINDOW_OVERLAP` | `128` / `0.5` | sensor | Sensor window settings. |
| `SENSOR_MODEL_ID` | *(HF model id)* | sensor | Kaun sa pre-trained model. |
| `USE_FALLBACK` | `false` | sensor | Statistical fallback on/off. |
| `FPS` | `12` | video | Webcam frame rate. |
| `HORIZONTAL_ANGLE_THRESHOLD` | `~60°` | video, fusion | Body horizontal maanne ka angle. |
| `MODALITY_WEIGHTS` | `sensor=0.5,video=0.5` | fusion | Fusion voting weights. |
| `SMOOTHING_WINDOW` | `5` | fusion | Smoothing ke liye window size. |
| `FALL_ACCEL_THRESHOLD` | *(SisFall pe tuned)* | fusion | Fall ke liye motion spike limit. |
| `INACTIVITY_SECONDS` | `1800` | fusion | Kitni der still = inactivity (1800s = 30 min). |
| `LLM_PROVIDER` | `ollama` | feedback | `ollama` (local) ya `gemini`/`openai`/`anthropic`. |
| `LLM_MODEL` | `llama3.2:3b` | feedback | Kaun sa LLM model. |
| `OLLAMA_HOST` | `http://localhost:11434` | feedback | Local Ollama ka address. |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | *(optional)* | feedback | Cloud API keys (agar cloud use ho). |
| `DATASET` | `uci-har` | simulator | Kaun sa dataset replay ho. |

> **Port** = ek computer pe alag-alag services ke "darwaze ke number". Jaise MQTT ka 1883,
> database ka 5432. Isse ek hi computer pe kai services alag-alag chal sakte hain.
> **`.env` file** = ek chit jisme saari settings likhi hoti hain. Code isko padhta hai.
> Isse ek hi code alag-alag settings pe chal sakta hai (bina code badle).

---

# SECTION 8: SEQUENCE DIAGRAMS (Step-by-step time ke saath kaun kya bolta hai)

**Sequence diagram** = time ke hisaab se batata hai kaun kisko kya message bhejta hai (top se
bottom = time aage badhta).

## 8.1 Normal Activity Update (aam din)
1. Simulator → Sensor: `har/sensor/raw` (IMU window).
2. Sensor → Fusion: `har/sensor/prediction` `{label, conf}`.
3. Video → Fusion: `har/video/prediction` `{label, conf, orientation}`.
4. Fusion khud me: align + confidence-weighted vote + smooth.
5. Fusion → PostgreSQL: `activity_timeline` me insert.
6. Fusion → Dashboard (WebSocket): `{channel:"activity", data:{...}}`.
7. Dashboard: Live Monitor card update.

## 8.2 Fall Alert Flow (fall hone pe) 🚨
1. Sensor → Fusion: prediction `{motion_intensity high}`.
2. Video → Fusion: prediction `{orientation: horizontal}`.
3. Fusion: fall rule = **spike AND horizontal** → sach.
4. Fusion → PostgreSQL: `events(type=FALL, critical)` insert.
5. Fusion → Feedback (MQTT): `har/event {FALL}`.
6. Fusion → Dashboard (WebSocket): `{channel:"event", data:{FALL}}`.
7. Feedback: LLM ko prompt (alert mode, structured).
8. Feedback → PostgreSQL: `feedback(mode=alert)` insert.
9. Feedback → Dashboard (WebSocket): `{headline, detail, disclaimer}`.
10. Dashboard: laal FallAlertBanner + AI message dikhata hai.

> Dekho — fall pe **do cheezein parallel** hoti hain: (a) Dashboard turant raw event dikhata
> hai (fast), aur (b) Feedback service AI se ek acche shabdo wala alert banata hai (thoda
> slow, par better). Isliye caregiver ko pehle turant alert, phir AI ka detail milta hai.

---

# SECTION 9: TESTING STRATEGY (System sahi kaam kar raha, kaise check karein)

**Testing** = code sahi chal raha hai ye pakka karna. 5 level:

| Level | Kya test hota hai | Tool |
|---|---|---|
| **Unit** | Chhote tukde: feature maths, geometric rule thresholds, fusion voting/smoothing, fall rule, label mapping. | pytest |
| **Integration** | Services ka aapas me kaam: MQTT round-trip (raw → sensor prediction → fusion activity), DB writes, WS push. | pytest + local Mosquitto |
| **Contract** | Saare payloads `shared/schemas.py` (pydantic) se match karte hain? | pytest |
| **GenAI** | Feedback me required fields + disclaimer hai? alert mode critical severity deta hai? | pytest (mock + live LLM) |
| **Metrics harness** (FR-X5, NFR-2) | Labeled dataset replay → fused predictions → **per-class F1**, **fall precision/recall**, **latency** nikaalo; **fusion vs sensor-only vs video-only** compare. | `tests/metrics/` |

**Metrics harness output (report ke liye):** ek table `{method: F1}` — Sensor-only / Video-only /
Fusion — plus fall precision/recall aur average latency. Ye seedha results slide me jaata hai.

> **Unit test** = ek chhote function ko akela test karna. **Integration test** = kai parts ko
> saath test karna. **Contract test** = messages sahi format me hain ya nahi.
> **pydantic** = Python ka tool jo JSON ka format check karta hai (galat format ho to pakad le).
> **Mock** = nakli version (jaise asli LLM ke bina test karne ke liye ek fake LLM).
> **Ye metrics harness project ka sabse important proof hai** — yahi dikhata hai **Fusion F1 >
> single-modality F1** (project ka main claim).

---

# SECTION 10: DEPLOYMENT & LOCAL SETUP (One-command demo kaise chalta hai)

## 10.1 Prerequisites (pehle kya chahiye)
- Docker + docker-compose, Python 3.11+, Node 18+ (dashboard dev ke liye), working webcam.
- **PostgreSQL** (container ya local).
- *(Optional)* **Ollama** (sirf agar local open-source LLM use karo); model pull:
  `ollama pull llama3.2:3b`.
- Ek dataset (UCI HAR / SisFall) `data/` me download (one-time, online).

## 10.2 Run (chalane ke steps)
```bash
# 1) one-time: local LLM aur datasets laao
ollama pull llama3.2:3b
python simulator/datasets/download.py --dataset uci-har   # data/ me aayega

# 2) sab kuch start karo (Mosquitto + PostgreSQL + 4 services + dashboard)
docker-compose up --build

# 3) sensor replay start karo (koi hardware nahi, sirf software simulator)
python simulator/replay.py --dataset uci-har --realtime

# 4) dashboard kholo
#    http://localhost:5173
```

`docker-compose` ye sab uthata hai: `db` (PostgreSQL), `mosquitto`, `sensor_service`,
`video_service`, `fusion_service`, `feedback_service`, `dashboard`. Video service host ki
webcam use karta hai (device passthrough).

## 10.3 Ports (kaun sa service kis darwaze pe)
| Service | Port | Kya |
|---|---|---|
| PostgreSQL | 5432 | Database |
| Mosquitto (MQTT) | 1883 | Message broker |
| Fusion API/WS | 8001 | Fused activity & alerts API |
| Feedback API/WS | 8002 | GenAI API |
| Ollama | 11434 | Local LLM (optional) |
| Dashboard | 5173 | User interface |

> **`bash` commands ka matlab:** ye terminal (command line) me type karne wale commands hain.
> `docker-compose up --build` = "sab kuch bana ke chalu karo". `--realtime` = "asli speed pe
> replay karo (jaise live ho raha ho)".
> **`localhost`** = "yahi computer" (koi internet address nahi, tumhara apna laptop).
> **Device passthrough** = Docker container ko laptop ki asli webcam use karne dena.

---

# SECTION 11: IMPLEMENTATION ROADMAP (Kaam kis order me, kaun karega)

**Roadmap** = kaam ka plan/order. Ye original 10-phase plan ko software-only ke hisaab se
re-scope karta hai, aur 4-person team me baant deta hai (parallel kaam ho sake):

| Phase | Re-scoped deliverable | Owner (suggested) |
|---|---|---|
| 1 | Do `core_docs` + repo skeleton + `shared/` contracts. | All |
| 2 | Short survey notes (HAR, pose, fusion) report ke liye. | All |
| 3 | **Simulator** (UCI-HAR/SisFall replay over MQTT) + Mosquitto up. | Dev A |
| 4 | **Video Service**: MediaPipe + geometric rules (no training). | Dev B |
| 5 | **Sensor Service**: features + pre-trained HF model + fallback. | Dev A |
| 6 | **Fusion Service**: confidence-weighted voting + smoothing + fall rule. | Dev C |
| 7 | Cloud ki jagah **MQTT + PostgreSQL**; end-to-end real-time wire. | Dev C |
| 8 | **React + Vite dashboard** (live + history + trends). | Dev D |
| 9 | **Feedback Service** with LLM (Ollama / Cloud APIs). | Dev B/D |
| 10 | **Metrics harness**, demo checklist (FSD §11), PPT/report. | All |

> **Deliverable** = jo cheez us phase me ban ke tayaar honi chahiye.
> **Parallelize** = ek saath alag-alag log alag hisse pe kaam karein (waqt bache). Microservice
> architecture isliye accha hai — Dev B video pe, Dev C fusion pe, alag-alag kaam kar sakte hain.

---

# SECTION 12: OPTIONAL FUTURE HARDWARE PATH (Abhi nahi, future ke liye documented)

Project strictly **software-only** hai. Par agar future me koi team **real hardware** jodna
chahe, to **same software pipeline** extend ho sakti hai:

Ek physical microcontroller **ESP32 + MPU6050 IMU sensor** asli motion padh sakta hai, use
`har/sensor/raw` JSON schema me format kare, aur Mosquitto pe Wi-Fi (MQTT) se publish kare —
**software simulator ko replace karke, downstream me zero change**.

> Ye **beauty of the design** hai: kyunki simulator aur real hardware **same topic pe same
> JSON format** bhejte hain, baaki poora system ko farq hi nahi padta ki data nakli hai ya
> asli. Sirf ek input source badal do, baaki sab waise ka waisa. (Future: heart rate sensor,
> real cameras, multi-person tracking, edge-AI chips.)

---

# SECTION 13: RISKS & MITIGATIONS (Engineering khatre + ilaaj)

| Risk (khatra) | Mitigation (ilaaj) |
|---|---|
| HF HAR model ke labels hamare 6 classes pe map na hon. | Label-mapping table (§5.2) + statistical/zero-shot fallback (FR-S6). |
| Local LLM CPU pe slow. | Chhota 3B model; feedback on-demand/periodic, per-frame nahi; template fallback. |
| Webcam rule galat classify kare. | Fusion + temporal smoothing; config se threshold tune. |
| Modalities ke beech time-sync drift. | Har message pe timestamp; fusion buffer me tolerance window se align. |
| False fall alarms. | Fall ke liye dono modalities chahiye; hysteresis smoothing. |
| Docker webcam passthrough issue. | Video service ke liye non-Docker run mode document karo. |

> **Time-sync drift** = do modalities ki ghadiyaan thodi alag ho sakti hain, isliye har message
> pe timestamp lagate hain aur "tolerance window" (thoda margin) ke saath align karte hain.

---

# SECTION 14: COMPLIANCE CHECKLIST (Rules follow ho rahe? Final check)

- [ ] §2 ki har dependency open-source license ki hai (ya cloud credentials set hain agar closed).
- [ ] Database poora PostgreSQL pe, docker-compose me containerized.
- [ ] Agar cloud models use ho rahe (Gemini/GPT/Azure), to internet + valid API keys check.
- [ ] **Koi custom model training nahi** — sirf pre-trained inference models.
- [ ] **Raw video kabhi store/transmit nahi hoti** (NFR-3, FR-V5).

> **Compliance** = "rules maane ja rahe hain" ka confirmation. Ye checklist project ke 4 golden
> rules ka final verification hai.

---

# 🧠 POORA SYSTEM EK KAHANI ME (Sabse Important Recap)

Ek line me: **Do input (webcam + nakli sensor) → do services label banate → broker ke through
Fusion sab milata → final activity + fall → database me save + AI se advice → dashboard pe
live dikhta.**

Thoda detail me, ek fall ki kahani:

```
1. Patient girta hai.
2. SIMULATOR (ya real sensor) → high motion data → BROKER (har/sensor/raw)
3. SENSOR SERVICE → "motion spike bahut high!" → BROKER (har/sensor/prediction)
4. VIDEO SERVICE (webcam) → "body horizontal ho gayi!" → BROKER (har/video/prediction)
5. FUSION SERVICE → dono milata → "spike AND horizontal = FALL!" (dimaag)
      ├── PostgreSQL me FALL event save
      ├── DASHBOARD ko turant laal banner (WebSocket)
      └── FEEDBACK SERVICE ko event bhejta
6. FEEDBACK SERVICE → LLM se acche shabdo me alert likhwata (+ disclaimer)
      ├── PostgreSQL me feedback save
      └── DASHBOARD pe AI message dikhata
7. CAREGIVER → laal banner + AI advice dekh ke turant patient ke paas jaata.
```

---

# 📌 8 SABSE ZAROORI CONCEPTS (Viva/Exam ke liye)

1. **Microservices + MQTT Broker (Pub/Sub):** 5 alag services, ek beech ka post-office
   (Mosquitto) ke through YouTube-subscribe-style baat karte hain. Loosely coupled.

2. **REST vs WebSocket:** REST = SMS (maango-tab-milega, history ke liye). WebSocket = call
   (live, khud push, current activity/alerts ke liye).

3. **Confidence-weighted Late Fusion:** har modality alag predict kare, phir
   `confidence × weight` se jo zyada score, wo jeet. Isse Fusion single se better hota hai.

4. **Fall = spike (sensor) AND horizontal (video):** dono chahiye, tabhi FALL. Isse false
   alarm kam. Ye Fusion Service me hota hai.

5. **Privacy by construction:** Video Service raw frame turant delete karta hai, sirf numbers
   (landmarks) bhejta hai. Video kabhi database me nahi.

6. **Pre-trained models + Inference only (No training):** ready-made models sirf use karte
   hain. Video me to ML bhi nahi, sirf geometry rules.

7. **PostgreSQL persistence:** 3 tables (activity_timeline, events, feedback) — restart ke
   baad bhi data safe.

8. **Docker one-command start:** `docker-compose up` se poora system (broker + db + 4 services
   + dashboard) ek saath. Simulator alag command se replay.

---

# 🔗 FSD aur TDD ka Rishta (dono kaise jude)

- **FSD** ne bataya: "system ko fall detect karna chahiye" (requirement FR-F4).
- **TDD** batata hai: "fall rule = motion spike AND horizontal, Fusion Service ki `falldetect.py`
  me, `FALL_ACCEL_THRESHOLD` config se" (implementation).

Har `FR-*` (functional requirement) aur `NFR-*` (non-functional) ka TDD me ek technical jawab
hai. Dono milke poora project banate hain: **WHAT (FSD) + HOW (TDD)**.

---

*Ye learning note `core_docs/TECHNICAL_DESIGN.md` (Version 1.0) par based hai. Agar tumhe koi
specific section aur detail me chahiye (jaise sirf Fusion ka maths, ya sirf MQTT), to bol dena
— main us par ek aur alag note bana dunga.* 🚀
