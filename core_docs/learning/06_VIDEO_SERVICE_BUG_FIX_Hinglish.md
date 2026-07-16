# Video Service Bug Fix & Mocking (Hinglish)

## Issue 1: Video Service Crashing (No Camera Found)
**Problem:** 
Dashboard par "Video: No update yet" (red alert) dikh raha tha. Job logs check kiye toh pata chala ki `video-service` baar-baar crash aur retry kar raha hai with error: `can't open camera by index` aur `Camera index out of range`. 
Iska reason yeh tha ki Docker (Windows/WSL) by default host machine ke webcam (`/dev/video0`) ko access nahi kar pata.

**Solution (Feature Update):**
1. Maine `services/video_service/config.py` mein `camera_index` ka type `int` se change karke `str` (string) kar diya.
2. `services/video_service/adapters.py` ko update kiya taaki agar string input (jaise kisi video file ka path ya DroidCam/IP Webcam ka URL) diya jaye, toh OpenCV usko seamlessly read kar sake. Ab `CAMERA_INDEX="http://192.168.x.x:8080/video"` directly `.env` se pass kiya ja sakta hai.

---

## Issue 2: Dashboard UI Mocking for Demo (Without Real Camera)
**Problem:** 
Humein dashboard par poora "Green Checkmark" (Live monitoring active) chahiye tha demo ke liye, lekin bina kisi asli camera setup ya phone connect kiye.

**Solution (Simulator Modification):**
1. Maine `simulator/demo.py` file ko open kiya. Pehle yeh script sirf mock **Sensor** data (`SensorRaw`) publish karta tha.
2. Maine script mein **Video Prediction** (`VideoPrediction`) ka mock data publish karne ka logic add kar diya. Iske liye `Modality.VIDEO`, `ActivityLabel`, aur `Orientation` enums ka use karke ek saath dono streams chalani shuru ki.

---

## Issue 3: Simulator Loop Crash (Enum Typo)
**Problem:** 
Simulator modify karne ke baad "Data is stale" aa gaya aur sensor ki feed bhi band ho gayi. Logs me error aayi: `AttributeError: FACING`.

**Solution:**
1. Code mein galti se `Orientation.FACING` use ho gaya tha, jabki `shared/labels.py` ke hisaab se sahi enum `Orientation.VERTICAL` tha.
2. Maine `demo.py` mein wapas jakar `Orientation.FACING` ko `Orientation.VERTICAL` se replace kiya aur container ko wapas rebuild (`docker compose up -d --build simulator`) kiya.

**Final Outcome:**
Ab `fusion-service` ko lag raha hai ki hardware camera bilkul sahi chal raha hai, aur dashboard par **Sensor** aur **Video** dono ka feed perfectly green checkmark ✅ ke sath update ho raha hai. Demo ke liye ek perfect isolated environment ban gaya hai!
