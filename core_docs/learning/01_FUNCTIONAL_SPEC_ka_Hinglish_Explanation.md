# 📚 FUNCTIONAL SPEC ko samjho — Ekdam Easy Hinglish me (Scratch se, Full Detail)

> Ye file `core_docs/FUNCTIONAL_SPEC.md` ka **poora explanation** hai — bilkul aasan Hinglish me.
> Yahan hum har cheez ko **zero se** samjhenge. Koi bhi word tough lage to ghabrao mat,
> hum use pehle define karenge, phir aage badhenge.
>
> **Padhne ka tarika:** Isse ek kahani ki tarah upar se neeche padho. Har section
> pehle "ye kya hai" batata hai, phir "aisa kyun" aur "kaise" samjhata hai.

---

## 🎯 Sabse Pehle: Ye Project Hai Kya? (One-line me)

Socho ek **budhe (elderly) ya bimaar patient** hain ghar pe. Unko 24 ghante koi
insaan watch nahi kar sakta. Agar wo **gir jaayein (fall)** to turant pata chalna
chahiye taaki help mil sake.

Hamara project ek **software system** banata hai jo:

1. **Camera (webcam)** se dekhta hai patient kya kar raha hai — chal raha, baith raha,
   khada, let raha, ya exercise kar raha.
2. Ek **nakli sensor (simulated wearable)** se bhi motion data leta hai.
3. Dono cheezein **milaakar (fuse karke)** decide karta hai patient ka activity kya hai
   aur **fall hua ya nahi**.
4. Ek **AI (GenAI/LLM)** se **simple bhasha me advice aur alert** likhwata hai.
5. Ye sab ek **web dashboard** pe dikhata hai jise **caregiver/doctor** dekh sakein.

Aur sabse important baat: **Ye sab bina kisi physical hardware ke, bina koi model train
kiye, sirf free/open-source tools se banega.** (Ya optionally paid cloud API se bhi.)

---

## 📖 Document ke Naam Samajh lo (FSD vs TDD)

Is project me do main documents hain:

| Document | Full Naam | Ye kya batata hai |
|---|---|---|
| **FSD** | Functional Specification Document | System **KYA** karta hai (features, behaviour) |
| **TDD** | Technical Design Document | System **KAISE** banta hai (code, libraries, database) |

> 🧠 **Yaad rakho:** FSD = "WHAT" (kya). TDD = "HOW" (kaise).
> Ye jo file tum abhi padh rahe ho, wo **FSD (WHAT)** ke baare me hai.

Iska matlab: FSD me hum ye nahi likhte "konsa Python function use karenge". Hum sirf
likhte "system ko fall detect karna chahiye". Code ki detail TDD me jaati hai.

---

# SECTION 1: OVERVIEW (Poora Intro)

## 1.1 Is document ka maksad kya hai?

FSD batata hai system **kya karega** — user ke point of view se. Yaani:
- Kaun se **features** honge.
- User **kaise interact** karega (screen by screen).
- Har feature **"done" (complete)** kab maana jaayega — iski **measurable condition**.

> **Measurable condition** ka matlab: aisi cheez jise naap sakein. Jaise "fall alert
> 2 second ke andar aana chahiye" — ye naapi ja sakti hai. Isse **Acceptance Criteria**
> kehte hain (aage bahut baar aayega ye word).

## 1.2 Product ka ek-line summary (thoda tough tha, ab tod ke samjho)

Original line lambi hai, hum use tukdo me todte hain:

- **"HAR System ek software application hai"** → sirf software, koi machine/gadget nahi.
- **"jo patient ki activities pehchanta hai"** → walking, sitting, standing, lying, exercising.
- **"aur real-time me falls detect karta hai"** → girna turant pakadta hai (live).
- **"camera pose stream process karke"** → webcam se body ke joints (landmarks) nikaal ke.
- **"aur optionally ek simulated software-wearable-sensor stream se"** → ek nakli sensor
  bhi data de sakta hai (real device nahi).
- **"phir personalized health feedback aur alerts banata hai GenAI model se"** → ek AI
  patient ke liye simple advice likhta hai.
- **"Caregiver/doctor sab kuch web dashboard pe dekhte hain, jiske peeche PostgreSQL
  database hai"** → data ek database me save hota hai, dashboard pe dikhta hai.
- **"Ye sab bina physical hardware aur bina custom training ke banega."** → hamari sabse
  badi constraint (rule).

## 1.3 Ye document kaun padhega? (Intended audience)

- **Project team + evaluators (teachers)** — scope pe agree karne aur grade dene ke liye.
- **Developers (khud team)** — build karte waqt "source of truth" (sach ka source).
- **Demo dekhne wale / faculty guide** — capabilities aur limits samajhne ke liye.

## 1.4 Guiding Constraints (4 Golden Rules) ⭐

Ye 4 rules **poore project ki neev (foundation)** hain. Inhe dhyaan se samjho:

1. **Flexible Model Choices (Open + Closed Source dono chalenge).**
   - Free local open-source models bhi use kar sakte ho (koi paise nahi).
   - Ya paid cloud API (jaise ChatGPT) bhi — par usme internet + API key chahiye.

2. **No custom model training (Koi model train nahi karenge).**
   - Sirf **pehle se trained (pre-trained)** models use honge.
   - Matlab hum khud kisi AI ko sikhaayenge nahi; ready-made model lekar sirf **use**
     (inference) karenge.

3. **Sirf Software (No physical hardware).**
   - Ek normal computer/laptop pe chalega. Koi IoT device nahi.
   - Jo "wearable sensor" chahiye, wo ek **software simulator** banata hai jo ek
     public dataset ko **replay** karta hai (dobara chala ke live jaisa dikhata hai).

4. **Privacy-first (Privacy sabse pehle).**
   - Camera ka **raw video kabhi save nahi hoga**.
   - Sirf **numbers (body landmark data)** hi camera component se bahar jaayenge.
   - Isse patient ki privacy bachti hai — koi tumhari video store nahi kar raha.

> 🧠 **In 4 rules ko baar-baar yaad rakho.** Poore document me ye ghoom-phir ke aate hain.

## 1.5 Glossary (Zaroori Words ki Dictionary) 📕

Ye words aage bahut aayenge. Ek baar aaram se padh lo:

| Word | Easy Matlab |
|---|---|
| **HAR** | Human Activity Recognition — insaan kya kar raha hai, uski pehchaan. |
| **Multi-modal** | Ek se zyada data source use karna (yahan: camera + sensor). |
| **Modality** | Ek single data source/channel (jaise "video modality"). |
| **Pose estimation** | Image se body ke joints ki position nikaalna. |
| **Landmark** | Body ka ek tracked point (jaise left shoulder) — (x, y, z, visibility) ke saath. |
| **IMU** | Inertial Measurement Unit — accelerometer + gyroscope wala sensor. |
| **Fusion** | Dono modalities ke predictions ko mila ke ek final decision banana. |
| **Late fusion** | Pehle har modality alag predict kare, phir baad me predictions combine karo. |
| **Temporal smoothing** | Recent history use karke label ko baar-baar flicker (badalne) se rokna. |
| **GenAI / LLM** | Generative AI model jo natural language (insaani bhasha) me likhta hai. |
| **Ollama** | Ek free tool jo open-source LLM ko laptop pe locally chalata hai. |
| **MQTT** | Ek halka messaging protocol — services aapas me baat karne ke liye. |
| **Microservice** | Ek independent chhota service jo system ke ek hisse ka kaam sambhaalta hai. |
| **Simulator** | Component jo recorded dataset ko live device jaise replay karta hai. |
| **F1 score** | Accuracy naapne ka ek number (0 se 1, jitna zyada utna accha). |

> **Thoda extra samajh (kyunki ye 3 baar aayenge):**
>
> - **Accelerometer** = speed/motion ka change naapta hai (jhatka pakadta hai).
> - **Gyroscope** = ghoomna/rotation naapta hai.
> - **Landmark (x, y, z, visibility)** → x,y = screen pe position, z = depth (kitna door),
>   visibility = wo point dikh raha hai ya chhupa hai (0 se 1).

---

# SECTION 2: PROBLEM & OBJECTIVES (Dikkat kya hai, aur hum kya solve karenge)

## 2.1 Problem Statement (Asli dikkat kya hai)

Aajkal healthcare **"ilaaj ke baad"** se **"pehle se monitoring"** ki taraf badh raha hai.
Par patients (khaaskar **budhe, operation ke baad wale, aur lambi bimaari wale**) ko koi
insaan 24×7 nahi dekh sakta.

Purane automatic tareeke har ek **akele weak (kamzor)** hain:

- **Sirf sensor wale system:** Motion accha pakadte hain, PAR **posture (baithna vs
  khada hona)** me farq nahi bata paate, aur visual context miss karte hain.
- **Sirf camera wale system:** Posture achhe se padhte hain, PAR **lighting/occlusion**
  (andhera / cheez saamne aa jaana) me fail hote hain, aur **privacy** ka bada issue —
  agar raw video store ho jaaye.
- Dono me **false alarm (galat alarm)** bahut aate hain. Aur khud patient ka bataya data
  bharosemand nahi hota.

**Core Problem (ek line me):**
> *Ek aisa real-time, accurate, privacy-preserving activity recognition system kaise
> banayein jo caregiver ko useful personalized feedback bhi de — wo bhi sirf free,
> open-source, pre-trained technology se?*

> **Occlusion** ka matlab: jab koi cheez body ke aage aa jaaye aur camera poora nahi
> dekh paaye. Jaise patient table ke peeche ho.

## 2.2 Objectives (6 Main Goals) 🎯

| # | Goal (Easy me) |
|---|---|
| **O1** | Patient ki activities pehchano — walking, sitting, standing, lying, exercising — real-time me. |
| **O2** | **Falls detect karo** bharose ke saath, kam false-positive ke saath. |
| **O3** | Sensor + video ko **fuse (mila)** karo taaki combined accuracy kisi ek se zyada ho. |
| **O4** | **Personalized simple-language feedback** aur **alerts** banao GenAI se. |
| **O5** | Live status, history, trends, alerts — sab ek **web dashboard** pe dikhao. |
| **O6** | Poora system **open-source, free, privacy-safe, aur laptop pe chalne wala** rakho. |

> **False-positive** = jab kuch hua nahi par system keh de "hua". Jaise patient sirf
> aaram se leta, par system keh de "fall ho gaya" — ye false positive hai. Inhe kam karna
> hai warna caregiver alarm pe bharosa karna band kar dega.

## 2.3 Success Criteria (Project safal kab maana jaayega)

- Fusion model ka **activity F1 score** kisi bhi single modality se **zyada** ho.
- Fall detection ka **precision aur recall** dono **high** ho (bahut kam false positive).
- End-to-end **latency itni kam** ho ki **real-time feel** ho.
- Live demo **ek laptop pe end-to-end** chale — **koi paid service nahi, koi self-trained
  model nahi**.

> **Latency** = deri. Event hone aur dashboard pe dikhne ke beech ka time.
> Kam latency = fast = real-time feel.
>
> **Precision vs Recall (super important, dhyaan se):**
> - **Precision:** Jab system ne "fall" bola, to usme se kitne sach me fall the?
>   (galat alarm kitne kam?)
> - **Recall:** Jitne asli falls hue, unme se kitne system ne pakde?
>   (miss kitne kam?)
> - **F1 score:** In dono ka balance ek number me (0–1).

---

# SECTION 3: SCOPE (Kya karenge, Kya NAHI karenge)

## 3.1 In Scope (Ye banayenge ✅)

- Laptop **webcam** se real-time activity recognition (video modality).
- **Simulated wearable sensor** se activity + fall signals (sensor modality) — ek
  **public dataset replay** karke.
- Dono modalities ka **multi-modal fusion** — ek final activity + fall event.
- **GenAI se banaya** personalized feedback, daily summary, aur alert messages.
- Ek **web dashboard** — live activity, timeline/history, trends, alerts.
- **Local persistence** — activity timeline aur events save karna (taaki history/summary
  kaam kare).
- Ek **metrics harness** — F1 / fall precision-recall / latency naapne ke liye (report ke liye).

## 3.2 Out of Scope (Ye NAHI banayenge ❌)

- **Physical IoT hardware** kharidna/jodna (ESP32/MPU6050/heart-rate sensor). Ek optional
  firmware path TDD me *documented* hai future ke liye, par **banayenge nahi**.
- **Koi model train/fine-tune/build** karna. Sirf pre-trained models.
- **Clinical/medical certification.** Ye ek academic prototype hai, medical device nahi.
- **Multi-patient / multi-camera tracking, telemedicine, mobile apps** — ye Future Scope me.
- **Cloud hosting / paid infrastructure.**

> **Persistence** = data ko permanently save karna (database/file me) taaki system band
> hoke phir chalu ho to data na khoye.
>
> **Firmware** = wo software jo physical device (chip) ke andar chalta hai. Hum wo nahi
> bana rahe, sirf docs me likha hai "agar future me karna ho to aise hoga".

## 3.3 Assumptions (Jo hum maan ke chal rahe hain)

- Ek laptop hoga jismein **webcam** aur **≥8 GB RAM** hoga.
- Laptop ek **chhota local LLM (3B-class)** chala sakta hai Ollama se — CPU pe (slow) ya
  GPU pe (fast).
- Internet **ek baar** chahiye — datasets, pre-trained models, LLM weights download karne
  ke liye. Uske baad system **poori tarah offline** chalega.
- Demo ke time camera ke saamne **ek hi patient** hoga.

> **3B-class model** = "3 Billion parameters" wala AI model. Bade models (jaise 70B) zyada
> smart par bhaari hote hain. 3B chhota hota hai, laptop pe chal jaata hai.
>
> **LLM weights** = model ki "seekhi hui knowledge" jo ek file me hoti hai. Ise ek baar
> download karna padta hai.

## 3.4 Dependencies (Kaun se tools use honge — options)

Yahan ye batate hain har kaam ke liye kaun se ready-made tools use kar sakte hain:

- **Video Modality (Pose & Posture) ke liye:**
  - *Open-Source:* MediaPipe Pose, YOLOv8 Pose, YOLOv11 Pose, OpenPose
  - *Closed/Cloud:* Google Cloud Video Intelligence, Azure Vision, AWS Rekognition

- **Sensor Modality (Software Replay) ke liye:**
  - *Open-Source:* Pre-trained HuggingFace HAR models (CNN ya LSTM classifiers)

- **GenAI / LLM (Feedback & Alerts) ke liye:**
  - *Open-Source (Local):* Llama 3.2 (1B/3B), Qwen2.5 (1.5B/3B), Phi-3-mini (Ollama se)
  - *Closed (API):* Google Gemini, OpenAI GPT-4o/mini, Anthropic Claude 3.5 Sonnet

- **Backend & Middleware:** FastAPI, Uvicorn, Mosquitto (MQTT Broker), PostgreSQL (Database),
  Docker, docker-compose, React + Vite (Frontend)

> **In naamo ko rattaane ki zaroorat nahi abhi.** Bas itna samjho: har kaam ke liye ek
> ready-made tool available hai. Detail TDD me hai.
>
> **CNN / LSTM** = do tarah ke neural network. CNN patterns pehchanta hai, LSTM time-series
> (sequence) data me acha hai (sensor data time ke saath aata hai, isliye LSTM fit hota hai).

---

# SECTION 4: STAKEHOLDERS, PERSONAS & USER STORIES (Kaun use karega)

## 4.1 Personas (System ke asli users)

**Persona** = ek imaginary example-user jo ek type ke logo ko represent karta hai.

| Persona | Kaun | Kya chahiye | Aaj kya dikkat |
|---|---|---|---|
| **Patient** | Budha / operation ke baad / bimaar. | Safe rahe; girne pe turant help; thodi privacy. | 24×7 dekh nahi sakte; camera se privacy dar. |
| **Caregiver/Nurse** | Ghar ka member ya nurse. | Patient ka state ek nazar me; instant fall alert; simple advice. | Continuous visibility nahi; false alarm se thak jaate. |
| **Doctor** | Recovery/trends periodically dekhta hai. | Time ke saath activity trends; chhota summary. | Patient ke khud bataye data pe depend karna padta. |
| **Admin/Developer (team)** | System setup + run + tune + demo. | Easy setup; observability; tunable rules; reproducible metrics. | Complex multi-service setup; paid tools. |

## 4.2 User Stories (Chhoti chhoti "main chahta hoon" wali lines)

**User story** ka format: *"As a [kaun], I want [kya] so that [kyun]."*

**Patient:**
- **US-P1:** Fall automatically detect ho taaki help aaye chahe main hil na sakoon.
- **US-P2:** Camera sirf body-position data rakhe (video nahi) taaki privacy bache.

**Caregiver/Nurse:**
- **US-C1:** Patient ki **current activity live** dikhe.
- **US-C2:** Fall pe **turant, saaf-saaf alert** mile.
- **US-C3:** Activity pattern pe **simple-language advice** mile.
- **US-C4:** **Kam false alarm** ho taaki bharosa bane.

**Doctor:**
- **US-D1:** Ghanto/dino ka **activity timeline aur trends** dikhe.
- **US-D2:** **Chhota daily summary** apne-aap ban jaaye.

**Admin/Developer:**
- **US-A1:** Poora system **ek command** se start ho.
- **US-A2:** Ek **dataset replay** kar sakoon (bina hardware ke).
- **US-A3:** Fall/activity **thresholds config** se tune kar sakoon (bina code badle).
- **US-A4:** **F1/precision/recall/latency naap** sakoon.

> **Threshold** = ek limit/line. Jaise "agar motion is number se upar gaya to fall".
> Ise config file me rakhte hain taaki code chhue bina badla ja sake.

---

# SECTION 5: ACTIVITIES & EVENTS (System kya-kya pehchanega)

## 5.1 Activity Classes (6 activities)

System patient ki current activity ko in me se **exactly ek** batayega:

| Code | Activity | Note |
|---|---|---|
| `WALKING` | Chalna / ghoomna | Dynamic motion. |
| `SITTING` | Baithna | Torso seedha, kam motion, hips mude. |
| `STANDING` | Khada hona | Torso seedha, kam motion, body vertical. |
| `LYING` | Lehta hua | Body horizontal (aadi). |
| `EXERCISING` | Exercise | Repetitive tez motion. |
| `UNKNOWN` | Pata nahi | Low confidence / patient frame me nahi. |

> **Torso** = body ka beech ka hissa (chest + pet). Seedha torso = baithe ya khade.
> Horizontal torso = lete hue.

## 5.2 Events (3 special ghatnaayein)

Activities ke alawa, system ye **events** bhi pakadta hai:

| Code | Event | Kab hota hai |
|---|---|---|
| `FALL` | Fall detect | Achanak **high-motion spike** + body ka **horizontal** ho jaana, ek saath. |
| `INACTIVITY` | Lambi inactivity | Kuch time tak koi meaningful change nahi (jaise bahut der se still lete). |
| `ABNORMAL_PATTERN` | Abnormal pattern | Activity recent baseline se hat jaaye (jaise din me bahut der lete rehna). |

> **Fall ki definition super important hai:** sirf tez motion (spike) se fall nahi maana
> jaata. **Motion spike AUR body horizontal — dono ek saath** hone chahiye. Isse false
> alarm kam hote hain (kyunki normal exercise me bhi motion hota hai, par body horizontal
> nahi hoti).
>
> **Baseline** = patient ka normal pattern. Usse hatna = abnormal.

---

# SECTION 6: FUNCTIONAL REQUIREMENTS (System ko exactly kya karna chahiye)

Ye section poore document ka **dil (heart)** hai. Yahan har chhoti zaroorat likhi hai.

**Har requirement ke 4 parts:**
- **ID** — jaise FR-S1 (F=Functional, R=Requirement, S=Sensor service, 1=number).
- **Priority** — **M**=Must (zaroori), **S**=Should (hona chahiye), **C**=Could (ho to accha).
- **Requirement** — kya karna hai.
- **Acceptance Criteria** — "done" kab maana jaayega (naapne wali condition).

System **5 microservices** me bata hai. Chalo har ek dekhte hain.

> **Microservice kya hai?** Poore system ko ek bada program banane ke bajaye, hum use
> chhote-chhote alag programs (services) me todte hain. Har service ka ek kaam. Fayda:
> ek fail ho to baaki chalte rahein; alag-alag develop/test kar sakte hain.

---

## 6.1 Sensor Service (FR-S) — Nakli sensor ka data sambhaalne wala

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-S1** | M | Simulator se sensor readings (accelerometer + gyroscope) ka continuous stream lena. |
| **FR-S2** | M | Stream ko fixed time **windows** me todna, aur har window ke **features** nikaalna. |
| **FR-S3** | M | Har window ko ek activity class me classify karna — **pre-trained model** se (no training). Label + confidence (0–1). |
| **FR-S4** | M | Har window ki prediction (label + confidence + timestamp) Fusion Service ko bhejna. |
| **FR-S5** | S | Ek **motion-intensity signal** dena jo fall logic use kar sake (acceleration spike). |
| **FR-S6** | C | Agar pre-trained model available na ho to ek simple statistical/zero-shot fallback pe chala jaana. |

> **Window kya hai?** Sensor data bahut tez aata hai (jaise 50 readings/second). Hum use
> chhote chunks (jaise 2 second = ek window) me todte hain, aur har window ko ek activity
> maante hain.
>
> **Feature kya hai?** Raw numbers se nikaali gayi summary — jaise average, max, min,
> standard deviation. Model raw data ke bajaye features padhta hai.
>
> **Fallback (FR-S6)** = "Plan B". Agar main model na chale to ek simple tareeka use karo
> taaki system band na ho.

---

## 6.2 Video Service (FR-V) — Webcam ka data sambhaalne wala

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-V1** | M | Laptop **webcam** se real-time frames capture karna. |
| **FR-V2** | M | **Pre-trained pose estimation** chala ke har frame me body landmarks nikaalna. |
| **FR-V3** | M | Landmarks se posture features (joint angles, orientation, vertical/horizontal) nikaalna. |
| **FR-V4** | M | Posture ko activity class me classify karna — **deterministic geometric rules** se (no training). |
| **FR-V5** | M | **Raw frames kabhi store na karna**; sirf numeric landmark/posture data bahar jaaye. |
| **FR-V6** | M | Har window ki posture prediction (label + confidence + orientation + timestamp) Fusion ko bhejna. |
| **FR-V7** | S | Ek orientation flag dena (jaise "body horizontal") jo fall logic use kare. |
| **FR-V8** | C | Jab koi frame me na ho to graceful degrade — `UNKNOWN` bhejo, crash mat karo. |

> **Deterministic geometric rules (FR-V4) — bahut important idea:**
> Machine learning ki jagah hum **simple geometry rules** use karte hain. Jaise:
> "agar torso ki line vertical hai aur hips mude hain → SITTING". Ye rules fixed hote hain
> (deterministic = har baar same input pe same output). **Isse koi training ki zaroorat
> nahi** — jo hamari constraint hai.
>
> **Joint angle** = do body parts ke beech ka angle (jaise ghutna kitna muda hai).
>
> **Graceful degrade (FR-V8)** = "shaanti se kaam kam karna" — crash hone ke bajaye
> `UNKNOWN` bol ke chalte rehna.
>
> **FR-V5 (Privacy) = Golden Rule #4 ka enforcement.** Video kabhi save nahi hoti,
> sirf numbers jaate hain.

---

## 6.3 Fusion / HAR Service (FR-F) — Dono ko milaane wala (system ka dimaag 🧠)

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-F1** | M | Time-aligned sensor + video predictions ko mila ke **ek final activity** banana per interval. |
| **FR-F2** | M | **Confidence-weighted voting** — jo modality zyada confident, uski zyada chalti hai. |
| **FR-F3** | M | **Temporal smoothing** — label ko baar-baar flicker hone se rokna. |
| **FR-F4** | M | **Fall detect** — combined rule: motion spike (sensor) **AUR** horizontal body (video). |
| **FR-F5** | M | Final activity + events ko persistence + Feedback + Dashboard ko bhejna. |
| **FR-F6** | S | Fused timeline se `INACTIVITY` aur `ABNORMAL_PATTERN` detect karna. |
| **FR-F7** | S | Ek modality thodi der ke liye gaayab ho to bhi chalte rehna (jo available hai usse). |

> **Confidence-weighted voting (FR-F2) — example se samjho:**
> Maano sensor bole "WALKING (confidence 0.6)" aur video bole "STANDING (confidence 0.9)".
> Video zyada confident hai (0.9 > 0.6), isliye final = **STANDING**. Isse zyada bharosemand
> modality jeet ti hai.
>
> **Temporal smoothing (FR-F3):** Ek single frame ka noise poora label na badle. Jaise
> agar 10 window me se 9 me "SITTING" aur beech me 1 me galti se "LYING" aaye, to smoothing
> use "SITTING" hi rakhti hai. Isse label "flicker" (kaanpna) band hota hai.
>
> **FR-F4 = fall ki asli logic.** Yaad karo Section 5.2 — fall = motion spike AND horizontal.
> Dono chahiye. Isliye ye "Fusion" service me hai (kyunki motion sensor se aata hai aur
> horizontal video se — dono chahiye).

---

## 6.4 Feedback Service — GenAI (FR-G) — AI se advice likhwane wala

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-G1** | M | Recent timeline se **personalized simple-language feedback** banana — **local LLM** se. |
| **FR-G2** | M | Jab `FALL`/abnormal event ho to ek **saaf natural-language alert message** banana. |
| **FR-G3** | S | Ek **daily/periodic summary** banana. |
| **FR-G4** | M | Hamesha ek **safety disclaimer** dena; koi medical diagnosis nahi karna. |
| **FR-G5** | M | Feedback ko **structured output** me dena (taaki dashboard fields reliably dikha sake). |
| **FR-G6** | S | Model download hone ke baad **poori tarah offline** chalna. |

> **LLM (Large Language Model)** = ChatGPT jaisa AI jo insaani bhasha me likhta hai. Hum
> ise timeline dete hain (jaise "patient 3 ghante baitha, 20 min chala") aur ye simple
> advice likhta hai.
>
> **Structured output (FR-G5) — kyun zaroori:** Agar AI free-form paragraph de to dashboard
> ko samajh nahi aayega ki kaunsa hissa "headline" hai, kaunsa "advice". Isliye AI ko
> fixed fields me output dena hota hai — jaise `{headline, detail, severity, advice}`.
> Tab dashboard har field alag box me dikha sakta hai.
>
> **Safety disclaimer (FR-G4) — bahut important:** AI **kabhi bimaari diagnose nahi karega**
> ("aapko ye disease hai" aisa nahi bolega). Hamesha likhega "ye sirf general guidance hai,
> doctor se milein". Ye legally aur ethically zaroori hai.

---

## 6.5 Dashboard Service (FR-D) — Screen jahan sab dikhta hai

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-D1** | M | Patient ki **current activity live** dikhana. |
| **FR-D2** | M | Fall/abnormal event pe ek **live banner/notification** dikhana. |
| **FR-D3** | M | **Activity timeline / history** dikhana. |
| **FR-D4** | M | **Trends** (kis activity me kitna time, din bhar ka pattern) **charts** me dikhana. |
| **FR-D5** | M | **GenAI feedback / summary** panel dikhana. |
| **FR-D6** | S | Ek **system/health panel** — kaun se services/modalities online hain. |
| **FR-D7** | C | Alert ko **acknowledge** (dekh liya) mark karne dena. |

> **Banner (FR-D2)** = screen ke upar ek dhyaan-kheenchne wali patti (usually laal rang me
> fall ke liye).
>
> **Acknowledge (FR-D7)** = caregiver "maine dekh liya" pe click kare, taaki naya aur
> dekha-hua alert alag dikhein.

---

## 6.6 Cross-cutting / Platform (FR-X) — Poore system ke common kaam

| ID | Pri | Kya karna hai (easy) |
|---|---|---|
| **FR-X1** | M | Timeline + events ko **locally persist** karna (restart ke baad bhi history rahe). |
| **FR-X2** | M | Ek **simulator** dena jo public dataset ko sensor channel pe replay kare. |
| **FR-X3** | M | Poore system ko **ek command** se start karna. |
| **FR-X4** | S | **Config** dena (thresholds, window sizes, model names) — bina code badle. |
| **FR-X5** | S | Ek **metrics harness** dena jo labeled replay pe F1/precision/recall/latency nikaale. |

> **Cross-cutting** = wo cheezein jo kisi ek service ki nahi, balki poore system ki hain.
>
> **Metrics harness (FR-X5)** = ek chhota testing tool. Hum ek dataset chalate hain jiska
> sahi jawab (ground-truth) pehle se pata hai. Phir system ki prediction aur sahi jawab
> compare karke F1/precision/recall/latency nikaalte hain. Ye numbers project report me
> jaate hain.
>
> **Ground-truth** = "asli sahi jawab" jo pehle se labeled hota hai.

---

# SECTION 7: USE CASES (Real duniya me system kaise use hota hai)

**Use case** = ek scenario jisme ek user system se apna kaam karvaata hai — start se end tak.

## 7.1 Use-case diagram (kaun kaun sa kaam kaun karta hai)

- **Patient** → live activity monitor, fall detect & alert.
- **Caregiver** → live monitor, fall alert, AI feedback padhna.
- **Doctor** → timeline & trends dekhna, daily summary padhna.
- **Admin** → system start/configure, dataset replay / metrics run.

## 7.2 Detailed Use Cases

### UC-2: Detect & alert on fall (sabse important safety case) 🚨

- **Actors:** Patient (trigger karta hai), Caregiver (alert receive karta hai).
- **Precondition:** System chal raha; webcam + sensor dono active.
- **Main flow (step by step):**
  1. Patient girta hai → sensor stream me achanak **motion spike**.
  2. Video stream me body **horizontal** ho jaati hai.
  3. Fusion dono signals mila ke ek **`FALL` event** raise karta hai.
  4. Event persist hota hai; Feedback Service ek **saaf alert message** banata hai.
  5. Dashboard turant ek **prominent fall alert** dikhata hai.
- **Postcondition:** Fall event record ho gaya; caregiver ko screen pe notify.
- **Alternate flows (agar kuch alag ho):**
  - Sirf ek modality fall bole → low-confidence maana jaayega, hard alert nahi (false-alarm
    protection).
  - Patient frame se bahar chala jaaye → fusion sirf sensor use karega.
- **Acceptance:** Simulated fall reliably **ek** alert raise kare; normal lete hue **koi
  alert nahi**.

### UC-1: Monitor live activity
- **Flow:** Streams aate hain → Fusion current activity banata hai → Dashboard live dikhata.
- **Acceptance:** Demo me activity change ~1–2 sec me dashboard pe dikhe.

### UC-4: Read AI personalized feedback
- **Flow:** Caregiver feedback panel khole → Feedback Service local LLM se recent activity
  summarize kare → advice + disclaimer de → dashboard dikhaye.
- **Acceptance:** Feedback readable, recent timeline se relevant, aur disclaimer ho.

### UC-7: Replay dataset / run metrics
- **Flow:** Developer labeled dataset pe simulator chalaye → system process kare → metrics
  harness prediction vs ground-truth compare kare → F1/precision/recall/latency print kare.
- **Acceptance:** Metrics produce hon aur har run me reproducible (same) hon.

---

# SECTION 8: DASHBOARD SCREENS & UX (Screens kaise dikhengi)

## 8.1 Screen Inventory (Kaun kaun si screens)

| Screen | Maksad | Main cheezein |
|---|---|---|
| **Live Monitor (home)** | Ek nazar me current state. | Bada "current activity" card; live status dot; fall-alert banner; mini activity feed. |
| **Activity Timeline** | Activities ki history. | Timestamps + durations wali chronological list; time range filter. |
| **Trends & Insights** | Time ke saath patterns. | Charts: time-per-activity (pie/bar), activity-over-time; key stats. |
| **AI Feedback** | GenAI output. | Personalized feedback card; daily summary; severity badge; disclaimer footer. |
| **Alerts** | Events ka log. | Fall/abnormal/inactivity events time + status ke saath; acknowledge action. |
| **System Health** | Operational view. | Har modality/service ka online/offline; last-updated timestamps. |

## 8.2 Primary UX Flow (caregiver ka normal raasta)

1. Dashboard kholo → **Live Monitor** current activity + green "all online" dot dikhaye.
2. Patient girta hai → upar ek **laal fall banner** aata hai generated alert message ke saath.
3. Caregiver banner pe click kare → **Alerts** pe jaaye, event detail + AI advice dekhe.
4. Baad me caregiver **AI Feedback** khole daily summary padhne.

## 8.3 UX Principles (Design ke soch)

- **Glanceability:** Current state door se bhi padha ja sake (bada font, color-coded).
- **Alarm clarity:** Fall alert visually sabse strong ho; kam-important info shaant ho.
- **Trust:** Modality/health status dikhao taaki users ko pata ho data live hai.
- **Plain language:** Sara AI text simple, non-technical shabdo me.

> **Glanceability** = "ek jhalak me samajh aana". Nurse kamre ke doosre kone se bhi dekh
> ke pata laga le patient ka state.

---

# SECTION 9: NON-FUNCTIONAL REQUIREMENTS (NFR) — Quality ki shartein

**Functional requirement** = system **kya** kare. **Non-functional requirement** = system
**kitne acche se** kare (speed, privacy, reliability, cost, etc.).

| ID | Category | Requirement (easy) | Target |
|---|---|---|---|
| **NFR-1** | Real-time latency | Event se dashboard tak deri real-time feel kare. | Activity update **< 1 sec**; fall alert **~1–2 sec** me. |
| **NFR-2** | Accuracy | Fusion single modalities se better ho. | Fusion **F1 > har single modality**; fall precision & recall **≥ ~0.9**. |
| **NFR-3** | Privacy | Raw video na store ho; sirf numbers bahar jaayein. | Audit me zero stored images; messages sirf numbers. |
| **NFR-4** | Reliability | Ek modality/service fail ho to system crash na ho. | Video off → sensor se chale (aur ulta bhi). |
| **NFR-5** | Usability | Non-technical caregiver bina training samajh sake. | Walkthrough: caregiver khud state + fall pehchaane. |
| **NFR-6** | Portability | Normal laptop pe chale; one-command start. | `docker-compose up` se poora system chale. |
| **NFR-7** | Cost / licensing | Sirf free, open-source components. | Audit me koi paid/closed component nahi. |
| **NFR-8** | Offline operation | Initial download ke baad bina internet chale. | Networking off karke full demo chale. |
| **NFR-9** | Maintainability | Microservice isolation; config-driven thresholds. | Threshold/model config se badle, code se nahi. |
| **NFR-10** | Observability | Har service apni activity log kare. | Logs me inbound data, predictions, events dikhein. |
| **NFR-11** | AI Safety | GenAI diagnosis na de; hamesha disclaim. | Text me disclaimer; koi diagnostic claim nahi. |

> **Docker / docker-compose (NFR-6):** Docker har service ko ek "container" (box) me pack
> karta hai. `docker-compose up` ek command se saare containers ek saath chala deta hai.
> Isliye "one-command start" possible hota hai.
>
> **Audit (NFR-3, NFR-7):** Ek check/jaanch. Jaise dependency audit dekhta hai koi paid
> tool to nahi use ho raha.

---

# SECTION 10: RISKS & MITIGATIONS (Kya galat ho sakta hai + uska ilaaj)

| Risk (khatra) | Impact (nuksaan) | Mitigation (ilaaj) |
|---|---|---|
| Webcam rules ajeeb pose galat padh dein. | Galat activity label. | Fusion + temporal smoothing; confidence gating; config se threshold tune. |
| Local LLM CPU pe slow. | Feedback laggy lage. | Chhota 3B model; feedback on-demand/periodically banao, har frame pe nahi. |
| Pre-trained HAR model ke labels hamare classes se match na karein. | Sensor labels mismatch. | Model labels ko hamare classes pe map karo; statistical/zero-shot fallback (FR-S6). |
| False fall alarm bharosa todein. | Alert fatigue. | Fall ke liye **dono** modalities chahiye; temporal smoothing. |
| Real hardware nahi → "IoT" story simulated hai. | Evaluator realism pe sawaal. | Optional ESP32 firmware path document karo; batao software pipeline identical hai. |

> **Alert fatigue** = itne galat alarm ki caregiver thak ke ignore karne lage. Isliye
> false alarm kam rakhna itna zaroori hai.
>
> **Confidence gating** = agar confidence kam ho to us prediction ko ignore/hold karo.
>
> **Label mapping** = ready-made model apne labels deta hai (jaise "run", "walk_upstairs")
> jo hamare 5 classes se alag ho sakte hain. Hum unko apne classes pe map (translate) karte
> hain.

---

# SECTION 11: ACCEPTANCE & DEMO CHECKLIST (Project "complete" kab?)

Project tab functionally complete maana jaayega jab **saare "Must" requirements pass** hon
aur ye live demo **ek laptop pe, poori tarah offline** safal ho:

- [ ] Ek command saare 5 services + simulator + dashboard start kare.
- [ ] Dashboard **live current activity** dikhaye jo webcam pe posture change hone pe badle.
- [ ] Simulator replay **sensor modality** chalaye; dono modalities "online" dikhein.
- [ ] Ek **acted/simulated fall** dashboard pe **exactly ek fall alert** ~1–2 sec me laaye.
- [ ] Normal **baithna/lehna** koi fall alert **na** laaye (false-alarm control).
- [ ] **AI feedback** panel relevant, simple advice **disclaimer ke saath** dikhaye.
- [ ] **Daily summary** ek coherent recap banaye.
- [ ] **Timeline & trend** views persisted history se bharein.
- [ ] **Webcam off** karne pe system crash na ho (sensor-only chale).
- [ ] **Metrics harness** F1 / fall precision-recall / latency print kare, aur **fusion F1 >
      single-modality F1** ho.
- [ ] Dependency audit confirm kare — model selection sahi (local open-source ya API keys),
      aur **koi custom-trained model nahi**.

> Ye checklist tumhari **final demo ki script** hai. Isme har box tick hona chahiye tabhi
> project "done" hai. Isliye ise print karke rakh lo.

---

# SECTION 12: TRACEABILITY (Har Goal kis requirement se poora hota hai)

**Traceability** = ye dikhana ki har objective (goal) kaun se requirements se pura hota hai.
Isse pata chalta hai koi goal chhoot to nahi gaya.

| Objective | Kis se pura hota hai |
|---|---|
| **O1** Activities recognize | FR-S1–S4, FR-V1–V6, FR-F1–F3, FR-D1, FR-D3 |
| **O2** Falls detect | FR-S5, FR-V7, FR-F4, FR-G2, FR-D2 |
| **O3** Fusion > single | FR-F1–F3, FR-F7, NFR-2, FR-X5 |
| **O4** GenAI feedback | FR-G1–G6, FR-D5 |
| **O5** Dashboard | FR-D1–D7, FR-X1 |
| **O6** Open-source/free/privacy/laptop | FR-V5, FR-X2–X4, NFR-3, NFR-6–NFR-8 |

---

# 🧠 POORE SYSTEM KA FLOW — Ek Kahani me (Sabse important recap)

Chalo poore system ko ek data ki yatra (journey) ki tarah dekhein:

```
   [Webcam]                          [Simulated Sensor]
      |                                     |
      | (frames)                            | (accel + gyro readings)
      v                                     v
 [Video Service]                      [Sensor Service]
  - pose landmarks nikaalo             - windows me todo
  - geometry rules se posture          - features nikaalo
  - RAW VIDEO STORE NAHI!              - pre-trained model se label
  - label + orientation bhejo          - label + confidence bhejo
      |                                     |
      +------------------+------------------+
                         |
                         v
                  [Fusion Service]  <-- system ka dimaag
                  - dono ko time pe align karo
                  - confidence-weighted voting
                  - temporal smoothing
                  - FALL = motion spike AND horizontal
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
   [Persistence]   [Feedback Svc]  [Dashboard]
   - timeline      - LLM se advice  - live activity
   - events        - alert message  - fall banner
     (PostgreSQL)  - daily summary  - timeline/trends
                   - DISCLAIMER     - AI feedback
                                    - health panel
```

**Ek line me poori kahani:** Webcam aur nakli sensor data dete hain → do services usse
label banate hain → Fusion dono ko mila ke final activity + fall decide karta hai →
data save hota hai, AI advice likhta hai, aur dashboard sab live dikhata hai.

---

# 📌 5 SABSE ZAROORI CHEEZEIN (Exam/Viva ke liye yaad rakho)

1. **4 Golden Constraints:** (a) Flexible models open/closed, (b) No custom training,
   (c) Software-only (no hardware), (d) Privacy-first (no raw video store).

2. **Fall ki definition:** motion spike (sensor) **AND** horizontal body (video) — **dono
   ek saath**. Isliye Fusion Service me hai. Isse false alarm kam hote hain.

3. **Fusion kyun better hai:** Sensor motion me strong par posture me weak; camera posture
   me strong par lighting/privacy me weak. Dono ko fuse karne se ek doosre ki kamzori dhak
   jaati hai → **Fusion F1 > single modality F1** (ye project ka main proof hai).

4. **5 Microservices:** Sensor, Video, Fusion, Feedback (GenAI), Dashboard + cross-cutting
   platform (simulator, persistence, config, metrics).

5. **Privacy trick:** Camera se **sirf numbers (landmarks)** bahar jaate hain, video kabhi
   store nahi hoti. Ye NFR-3 aur FR-V5 me enforce hota hai.

---

# ✅ Aage kya padhein?

Ab jab tumne FSD (WHAT — system kya karta hai) samajh liya, agli file **TDD** (HOW — kaise
banega, code/database/architecture) ke liye hai:
`core_docs/TECHNICAL_DESIGN.md`

Agar chaho to main uska bhi aisa hi easy Hinglish explanation bana doon is `learning` folder
me. Bas bol dena. 🚀

---

*Ye learning note `core_docs/FUNCTIONAL_SPEC.md` (Version 1.0) par based hai. Agar original
document update ho, to ye bhi update kar lena.*
