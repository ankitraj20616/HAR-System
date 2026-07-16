# 10. Video Service & Auth Service Fixes (Hinglish)

Ye document un sabhi practical issues aur bug fixes ki summary hai jo humne system (khaskar Video Service aur Auth Service) me theek kiye hain, taaki live camera demonstration smoothly ho sake aur naye users successfully login kar sakein.

## Part 1: Video Service & Live Camera Demo Fixes

Live camera (DroidCam/WiFi) testing ke dauran kuch major accuracy aur setup issues the, jinhe humne system code aur environment configuration dono jagah fix kiya hai:

### 1. Camera vs Simulator Clash Fix (Real-Time vs Fake Data)
**Problem:** Jab hum laptop ya DroidCam se real time video service test kar rahe the, toh system ko pichhe background se simulator ke "mock video" predictions bhi mil rahe the, jisse dashboard confuse ho raha tha.
**Fix:** `simulator/demo.py` aur `.env` mein ek naya toggle `SIMULATOR_MOCK_VIDEO=false` add kiya gaya. Ab simulator se aane wali nakli video predictions ko roki ja sakti hai taaki sirf real camera feed hi backend ko jaye.

### 2. Fusion Service Override Fix (Sensor vs Video Weightage)
**Problem:** Fusion service Sensor aur Video ko 50/50 weightage de raha tha (`MODALITY_WEIGHTS=sensor=0.5,video=0.5`). Real camera "STANDING" bhej raha tha lekin simulator se pichhe fake sensor data "WALKING" bhej raha tha, jisse dashboard "Walking" show kar raha tha jab insaan khada tha.
**Fix:** `.env` mein modality weights ko change karke `sensor=0.01,video=0.99` kar diya gaya. (Zero allow nahi tha kyunki strict safety check `weight <= 0.0` crash karwa deta). Isse ab jab video demo chalega, toh sensor data practically ignore ho jayega aur video data 99% prioritize hoga.

### 3. Video Classifier Deadzones & Sitting Fix (Fixing 'UNKNOWN', 'LYING' & 'SITTING')
**Problem:** Video classification logic mein bare gaps ("deadzones") the:
- Agar angle 20° se 70° ke beech tha, toh system "Unknown" output karta tha, lekin slight tilt pe 25° aam baat hai.
- Agar ghutne/hips 135° se 145° ke beech the, toh bhi "Unknown" aata tha, lekin 2D phone camera angle aksar seedhi taango ko bhi 130°-140° read karta hai.
- **Sitting detection fail** ho rahi thi kyunki 2D phone camera mein perspective distortion ki wajah se baithne pe bhi joint angles 130° se upar dikhte the. System usse STANDING bol deta tha.

**Fix:** `classifier.py` ke core logic ko rewrite kiya gaya aur thresholds `.env` me update kiye gaye:
- `HORIZONTAL_ANGLE_THRESHOLD=35.0`: Ab agar insaan 35° tak bhi aage jhukta hai, toh use upright (standing/sitting) maana jata hai, unknown nahi. Transition zone me body height ka use hota hai tie-breaker ke liye.
- `SITTING_JOINT_ANGLE=145.0` aur `STANDING_JOINT_ANGLE=160.0`: Thresholds ko badha diya gaya taaki 2D camera perspective ko accommodate kar sake.
- **Naya `hip_knee_ratio` heuristic add kiya gaya:** Jab insaan baitha hota hai, toh uske hips aur knees lagbhag ek hi height pe hote hain (vertically compressed). Yeh ratio (`hip-knee vertical distance / total body height`) angles se kahin zyada reliable hai 2D cameras ke liye. Agar ratio `< 0.18` hai, toh insaan sitting hai — chahe angles kuch bhi dikhayein. Isse ab phone camera se bhi SITTING accurately detect hoti hai.

### 4. Lying Foreshortening & Walking Accuracy Fixes
**Problem:**
- **Lying:** Agar insaan camera ki taraf pair karke leta ho (feet-to-camera), toh 2D camera mein sir aur pair vertically aligned dikhte hain, jisse system use "STANDING" bata raha tha.
- **Walking:** Walking ke liye system pairo (ankles) ka aage-peeche jana check karta tha. Agar pair camera me nahi dikh rahe, toh walking detect nahi hoti thi.

**Fix:** `classifier.py` mein PoseFeatures extend kiye gaye:
- **Z-Depth (3D) for Lying:** MediaPipe ki `z` (depth) dimension ka use karke naya `torso_depth_ratio` add kiya gaya. Agar kandhe aur hips ke depth (aage-peeche ki doorie) me bada farq hai (`> 0.4`), toh system samajh jata hai ki insaan kisi bhi angle se leta hua (LYING) hai.
- **Wrist Swing for Walking:** Walking ke temporal metrics mein `wrist_offset` (haatho ka hilna) add kiya gaya. Ab agar pairo ki movement frame se cut bhi jaye, lekin insaan ke haath (arms) swing kar rahe hain, toh system perfectly WALKING detect kar leta hai.

### 5. DroidCam Auto-Reconnect Fix (Preventing Permanent Drops)
**Problem:** Agar WiFi me minor jhatka lagta tha ya phone screen lock hoti thi, toh `video_service` sirf 5 attempts (`RECONNECT_ATTEMPTS=5`) me 10 seconds ke andar give up kar deta tha aur ruk jata tha. Uske baad docker container ko stop/start (`./dev.sh down` & `up`) karna padta tha.
**Fix:** `.env` aur code limits check karke `RECONNECT_ATTEMPTS=100` set kiya gaya aur max backoff 5 seconds rakha gaya. Ab camera disconnect hone par system agley 8 minutes tak usko patient ho kar wapas dhundhta rahega.


## Part 2: Auth Service Signup Role Fix

**Problem:** 
Jab koi naya user signup karta tha, usko directly system access nahi mil pata tha aur wo `"pending"` state me phase reh jata tha. Iski wajah thi database me pehle se maujood ek **trigger (`assign_pending_role`)**. Jaise hi `users` table me naya user insert hota tha, yeh trigger fraction of a millisecond me automatically `user_roles` me `"pending"` role set kar deta tha. Pehle ka Python code `ON CONFLICT DO NOTHING` use kar raha tha, jiski wajah se trigger ka "pending" role overwrite nahi hota tha aur user fasa reh jata tha.

**Fix (`services/auth_service/local_auth.py`):**
Humne `signup()` function ko modify kiya taaki jab user database me insert ho, toh trigger dwara banaye gaye "pending" role ko forcefully `"caregiver"` se **replace (UPSERT)** kar diya jaye.
1. Code me check lagaya gaya ki agar email super admin ki list (`SUPER_ADMIN_EMAILS`) me hai, toh default role `"admin"` hoga, warna `"caregiver"` hoga.
2. `users` table ke successful insertion ke baad ek aggressive SQL statement add ki gayi:
   ```sql
   INSERT INTO user_roles (user_id, role, updated_by)
   VALUES (%s, %s::app_role, %s) 
   ON CONFLICT (user_id) DO UPDATE SET role = EXCLUDED.role, updated_by = EXCLUDED.updated_by
   ```
Isse signup karte hi directly database me role set ho jata hai aur first login par dashboard perfectly access ho jata hai bina admin dashboard se manually role update kiye. Admin panel ab bhi kisi ko baad me update karne ke liye fully functional hai.

## Part 3: Admin User Deletion Feature

**Feature:**
Admin ko system se permanently users ko delete karne ki sahuliyat dena taaki unwanted ya test accounts system mein data clutter na badhayein.

**Implementation:**
1. **Backend API (`services/auth_service`):**
   - Naya `delete_user` function banaya gaya jo database query `DELETE FROM users WHERE id = %s` execute karta hai.
   - Database mein pehle se hi `ON DELETE CASCADE` lada hua tha, toh `users` se account udate hi uska `user_roles` map aur sab kuch automatically clean ho jata hai.
   - Naya API route `DELETE /api/admin/users/{user_id}` expose kiya gaya jisme strict role check hai ki user `"admin"` hi hona chahiye, aur koi admin galti se apne aap ko lock out na kar baithe isliye khud apna account delete karna disabled hai.

2. **Frontend UI (`dashboard/src`):**
   - Admin Dashboard ke "Registered Users" list mein har account ke side mein ek **Trash** (delete) icon add kiya gaya hai.
   - Accidental click rokne ke liye native browser `window.confirm` popup lagaya gaya hai jo double check karega ki account sach mein udana hai ya nahi. Delete hote hi page update hoke deleted user ko hata dega.
