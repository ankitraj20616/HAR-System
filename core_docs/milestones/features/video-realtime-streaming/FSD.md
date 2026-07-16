# Feature FSD: Real-Time Video Streaming (DroidCam / IP Camera Latency Fix)

> **FSD = Functional Spec Document.** Yeh batata hai ki **kya problem hai** aur **kya banna chahiye** — beginner-friendly language me, bina code ke.
> Iska technical jodidar document: [TDD.md](./TDD.md) — wahan **kaise banega** likha hai.

---

## 1. Ek line me problem

Phone ka camera video HAR system tak **pahunch to raha hai, par late pahunch raha hai** — aur yeh late-pan apne aap kabhi theek nahi hota.

Matlab: aap camera ke saamne gir gaye, par system ko woh 3 second baad pata chala. Fall detection system ke liye yeh **fail** hai.

---

## 2. Abhi setup kya hai (aaj ki sachchai)

Aapke phone me **DroidCam** app chal rahi hai. Woh phone ko ek chhota network camera bana deti hai.

[.env](../../../../.env) file me line 70 par yeh likha hai:

```
CAMERA_INDEX=http://192.168.0.145:4747/video
```

Yani HAR ka video service is URL se video utha raha hai.

### Data ka poora rasta

```
📱 Phone (DroidCam app)
      ↓   Wi-Fi router ke through, HTTP protocol
🖥️  Video Service (OpenCV se frame padhta hai)
      ↓   MediaPipe se body ke joints nikalta hai
      ↓   Classifier decide karta hai: walking / sitting / falling
📡 MQTT message
      ↓
🧠 Fusion Service (sensor + video milata hai)
      ↓
💻 Dashboard par label dikhta hai
```

### Protocol ka naam: **MJPEG over HTTP**

Yeh sunne me bada lagta hai, par idea bahut simple hai.

**MJPEG = Motion JPEG.** Phone koi fancy video encoding (jaise H.264) nahi kar raha. Woh bas **ek ke baad ek poori JPEG photo** bhej raha hai — jaise WhatsApp par 30 photo per second bhej de. Aapki aankh unhe jodkar "video" samajh leti hai.

**over HTTP** ka matlab: yeh normal website wali request jaisa hi hai, par ek twist ke saath —

- Normal website: browser request bhejta hai → server HTML deta hai → **connection band**.
- MJPEG: OpenCV request bhejta hai → phone photo bhejta hai → **connection band nahi hota** → phone photo bhejta rehta hai... hamesha.

Technically ise `multipart/x-mixed-replace` kehte hain. "Multipart" = ek response ke andar bahut saare hisse (har hissa ek photo). "x-mixed-replace" = har naya hissa purane ko replace kar dega.

### Jo protocol hum **use nahi** kar rahe

Confusion door karne ke liye:

| Protocol | Hum use kar rahe? | Kya hai |
|---|---|---|
| **MJPEG over HTTP** | ✅ **Haan, yahi** | JPEG photos ki continuous line |
| RTSP | ❌ Nahi | CCTV camera wala standard protocol |
| WebRTC | ❌ Nahi | Video call wala (Zoom/Meet) — sabse kam latency |
| HLS / DASH | ❌ Nahi | YouTube/Netflix wala — jaanbujhkar 5-30 sec late |
| USB webcam (V4L2) | ❌ Nahi | `CAMERA_INDEX=0` set karne par yeh hota |

**Achhi khabar:** MJPEG-over-HTTP latency ke liye bura choice **nahi** hai. Woh bilkul theek hai. Problem protocol me nahi, **hamare padhne ke tareeke me** hai. Yeh baat important hai — protocol badalne ki zaroorat nahi.

---

## 3. "Real-time" ka matlab kya hai?

Beginner log sochte hain real-time matlab "live". Par live aur real-time alag cheezein hain.

- **Live** = recording nahi hai, abhi ho raha hai. ✅ Hamara stream live hai.
- **Real-time** = live **+ delay itna kam ki decision lene layak ho**. ❌ Yeh hamare paas nahi hai.

YouTube live stream bhi "live" hai, par 20 second peeche chalti hai. Woh real-time nahi hai. Aapka system abhi thoda-bahut wahi kar raha hai.

### Real-time ka number kya hona chahiye?

Iska ek naam hai: **glass-to-decision latency** — "camera ke kaanch ke saamne kuch hua" se lekar "system ne decide kiya" tak ka time.

| Delay | Kaisa hai | Fall detection ke liye |
|---|---|---|
| 0 – 300 ms | Bahut badhiya | ✅ Ekdum sahi |
| 300 – 700 ms | Theek hai | ✅ Chalega |
| 700 ms – 1.5 s | Kharaab | ⚠️ Alert late |
| 1.5 s se zyada | Fail | ❌ Bekaar |

**Hamara target: video service ka apna hissa 300 ms se kam.**

---

## 4. Real-time kyun nahi hai? (asli explanation)

Ab main aapko exact wajah samjhaata hoon. Dhyan se padhna, yeh doc ka sabse zaroori hissa hai.

### 4.1 Nal aur baalti wali kahani 🪣

Socho ek **nal** hai jo **30 glass paani per second** gira raha hai. (= phone 30 frames per second bhej raha hai.)

Neeche aap khade ho aur **12 glass per second** hi utha paa rahe ho. (= hamara code 12 FPS par padhta hai, [.env:69](../../../../.env#L69) me `FPS=12`.)

Har second **18 glass extra** ho rahe hain. Woh gayab nahi hote — beech me rakhi **baalti** me jama hote hain.

Ab sabse important baat:

> **Aap baalti me se hamesha sabse PURANA paani uthate ho, naya nahi.**

Kyunki baalti ek **queue** hai — jo pehle aaya, woh pehle nikalta hai (FIFO: First In, First Out).

Toh 10 second baad aapke haath me jo glass hai, woh nal se 10 second pehle gira tha. **Aap ateet dekh rahe ho.**

### 4.2 Asli me baalti kahan hai?

Yeh "baalti" koi kalpana nahi — yeh aapke computer ke andar sach me hai. Ye hai aapke **operating system ka socket receive buffer** — network se aaya hua data jo abhi tak kisi ne padha nahi.

Phone TCP se data bhejta hai. TCP ka rule: **data kabhi gayab nahi hota**. Toh jo frames aapne nahi padhe, woh OS ki memory me line lagakar khade rehte hain, aapka intezaar karte hue.

### 4.3 To kya delay infinite ho jayega?

Nahi — aur yeh nuance samajhna zaroori hai (viva me poocha ja sakta hai).

TCP me ek safety feature hai jise **backpressure** kehte hain. Jab baalti (socket buffer) poori bhar jaati hai, TCP phone se kehta hai: **"ruk ja, mere paas jagah nahi."** Phir DroidCam ya to rukega ya frames drop karega.

Iska matlab: delay theoretically baalti ki gehrai par ja kar **atak** jaana chahiye. **Par woh delay khud kabhi kam nahi hota** — ek baar peeche ho gaye, peeche hi rahoge.

> **📊 Humne ise sach me naapa (guess nahi hai).** Ek local MJPEG server banaya jo 30 FPS bhejta hai, aur aaj ke code ki tarah 12 FPS par padha. Result:
>
> | Kitni der chala | Kitna peeche |
> |---|---|
> | Shuru me | 783 ms |
> | 25 second baad | **14,280 ms (14 second!)** |
>
> Yani delay **plateau hua hi nahi** — woh 25 second me hi 14 second tak pahunch gaya aur badhta ja raha tha. Asli Wi-Fi par TCP backpressure ise kisi point par rokega, par woh point **bahut hi ooncha** hai. Yeh problem maine socha tha usse bhi **zyada kharaab** nikli.

**Sar-sanshep:** Aapka system **live** hai (recording nahi), par **lagataar peeche girta ja raha hai**, aur woh gap apne aap kabhi band nahi hoga. Jitni der chalayenge, utna kharaab.

### 4.4 Teesri chhoti dikkat: MediaPipe slow hai

Har frame par MediaPipe body ke 33 joints dhoondhta hai. Isme **40-90 milliseconds** lagte hain.

12 FPS ka matlab hai har frame ke liye sirf **83 ms** ka budget. Toh MediaPipe kabhi-kabhi budget se bahar chala jaata hai, aur loop aur peeche gir jaata hai.

### 4.5 Chauthi dikkat: ek setting jo kaam hi nahi karti

Code me ek line hai jo **camera ki speed set karne ki koshish** karti hai — [adapters.py:30](../../../../services/video_service/adapters.py#L30):

```python
self._capture.set(cv2.CAP_PROP_FPS, fps)
```

Yeh line **USB webcam** par kaam karti hai. Par network stream par yeh **chupchaap ignore** ho jaati hai. Aap Wi-Fi ke through phone ko yeh nahi keh sakte ki "bhai dheere bhej". DroidCam apni marzi ki speed se bhejta rahega.

Yani code sochta hai usne speed set kar di, par kuch hua hi nahi. Yeh **silent failure** hai — sabse khatarnaak kism ka bug.

### 4.6 Ek aur delay jo video service ke bahar hai

[.env:102](../../../../.env#L102) me `FUSION_INTERVAL=1.0` hai. Fusion service **har 1 second me ek baar** hi decision leta hai.

Toh agar video service ko instantly bhi pata chal jaye, dashboard tak pahunchne me 1 second aur lag sakta hai. **Yeh feature ke scope me nahi hai** (Section 7 dekho), par honest rehna zaroori hai — video fix karne ke baad bhi yeh 1 second baaki rahega.

---

## 5. Solution ka core idea (ek hi line)

> **Baalti me se purana paani uthana band karo. Baalti ko lagataar khaali karte raho, aur hamesha SABSE NAYA frame lo.**

Bas. Yahi poora fix hai.

Technically: ek alag **background thread** banao jiska ek hi kaam ho — frames ko jitni tezi se aayein utni tezi se padhte rehna, aur unhe **fenkte rehna**. Sirf **sabse aakhri frame** ek dabbe me rakho. Jab MediaPipe taiyaar ho, woh dabbe me se **taaza** frame uthaye.

Purane frames ka koi mol nahi hai. Fall detection me 2 second purana frame **kachra** hai — usko process karna sirf time barbaad karna hai.

### Naya nal-baalti model

- Ek banda (background thread) nal ke neeche khada hai. Woh **har glass turant** uthata hai aur **fenk deta hai** — sirf aakhri glass ek mez par rakhta hai, purane ko hata kar.
- Doosra banda (MediaPipe) jab free hota hai, mez par se **taaza** glass uthata hai.
- **Baalti kabhi bharti hi nahi.** Delay kabhi jama nahi hota.

Yeh pattern ka asli naam: **"latest-frame-wins"** ya **"frame dropping"**. Har professional real-time video system yahi karta hai.

---

## 6. Functional Requirements

| ID | Priority | Behaviour | Acceptance (kaise pata chalega ki ho gaya) |
|---|---|---|---|
| FR-V1 | Must | Video service hamesha network camera ka **sabse naya** frame process kare, purana nahi. | Phone par stopwatch chalao, camera usko dikhao. Dashboard/log ka time aur stopwatch ka time me **300 ms se kam** farak ho. |
| FR-V2 | Must | Bina padhe frames **drop** ho jaayein, jama na hon. | 10 minute lagataar chalao. Latency shuru me jitni thi, ant me bhi utni hi ho (badhe nahi). |
| FR-V3 | Must | Delay **waqt ke saath badhna band** ho jaye. | 1 minute par aur 10 minute par measure karo — farak 100 ms se kam ho. |
| FR-V4 | Must | Latency ek **health/log field** me dikhe taaki naapi ja sake. | `GET /health` ya log me `frames_dropped` aur `frame_age_ms` dikhe. |
| FR-V5 | Must | Phone ka stream ruk jaye (app band, Wi-Fi gaya) to service **crash na ho**, reconnect kare. | DroidCam band karo → service `degraded` ho, crash na ho. Wapas chalu karo → 5 second me apne aap judd jaye. |
| FR-V6 | Must | USB webcam (`CAMERA_INDEX=0`) aur simulator **pehle jaise hi** chalein. | Purane saare tests bina badle pass hon. |
| FR-V7 | Must | **Privacy boundary na toote** — koi frame disk par save na ho. | Memory me ek hi frame rahe (jo turant replace ho jaye). `tests/contract/test_video_privacy.py` pass rahe. |
| FR-V8 | Should | Naya behaviour `.env` se on/off ho sake. | `VIDEO_LOW_LATENCY=false` karne par purana behaviour wapas aa jaye. |

---

## 7. Scope limit (isme kya NAHI hai)

Yeh saaf likhna zaroori hai, warna feature kabhi khatam nahi hoga:

- ❌ `FUSION_INTERVAL=1.0` wala 1-second delay — woh **alag feature** hai (Section 4.6).
- ❌ Protocol badalna (WebRTC/RTSP) — zaroorat hi nahi, MJPEG theek hai.
- ❌ MediaPipe ko tez banana (GPU, model_complexity=0) — alag optimization.
- ❌ Video ko browser me dikhana — privacy rule ke against hai, frames kabhi bahar nahi jaate.
- ❌ Video recording — **kabhi nahi**, yeh project ka core privacy vaada hai.

---

## 8. Kaise test karoge (stopwatch method)

Yeh sabse simple aur sabse pukka tareeka hai. Koi tool nahi chahiye.

1. Phone par **stopwatch app** kholo, start karo (milliseconds dikhne chahiye).
2. Laptop ki screen par apna **video service ka log** khol kar rakho.
3. Ab phone ka **camera** us stopwatch ki taraf... ruko — DroidCam ka camera aur stopwatch ek hi phone par nahi ho sakte.

**Sahi tareeka:** Laptop screen par ek online stopwatch chalao. Phone ka DroidCam camera **laptop screen** ki taraf ghumao. Ab laptop screen par ek saath do cheezein dikhengi:
- Asli stopwatch: `00:12.480`
- Aur uske bagal me: aapke video service ka live log, jisme frame ka time-stamp hai

Dono ka farak = **aapki latency**. 300 ms se kam matlab **paas** ✅

> **Aur bhi aasan (bina camera ghumaye):** TDD me `frame_age_ms` naam ka number add kar rahe hain — woh seedha log me delay bata dega. Details [TDD.md](./TDD.md) Section 7 me.

---

## 9. Risks (kya galat ho sakta hai)

| Risk | Kitna bada | Kya karenge |
|---|---|---|
| Background thread band nahi hoga, service hang ho jayegi | Medium | Thread ko `daemon=True` banayenge; `release()` me proper join with timeout |
| Frames drop karne se koi activity miss ho jaye | Low | 12 FPS fall detect karne ke liye kaafi hai; aur waise bhi purana frame kaam ka nahi tha |
| Do thread ek hi frame ko chhuenge → crash/garbage | Medium | Lock use karenge; frame **replace** hoga, edit nahi |
| Wi-Fi kharaab hone par latency wapas aa jaye | Low | Yeh network ki problem hai, code ki nahi. Log me dikhega |

---

## 10. Definition of Done

- [ ] Stopwatch test me latency **300 ms se kam**
- [ ] 10 minute chalane ke baad bhi latency **nahi badhi**
- [ ] DroidCam band/chalu karne par service **apne aap reconnect**
- [ ] `CAMERA_INDEX=0` (USB webcam) **pehle jaisa** chal raha hai
- [ ] Privacy contract test **pass**
- [ ] Saare purane tests **pass**, lint clean

---

## 11. Aage padho

- Technical design, code, aur test plan: **[TDD.md](./TDD.md)**
- Video service ka purana bug-fix history: [../../../learning/06_VIDEO_SERVICE_BUG_FIX_Hinglish.md](../../../learning/06_VIDEO_SERVICE_BUG_FIX_Hinglish.md)
