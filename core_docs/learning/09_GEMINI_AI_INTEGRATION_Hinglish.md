# GenAI Service - Google Gemini API Integration (Hinglish)

Pehle hamari Feedback Service puri tarah se **Ollama** (Local AI) par dependent thi. Ollama offline chalne ke liye kaafi accha hai, par isko chalane ke liye system me bohot saari RAM aur CPU/GPU power lagti hai, jiski wajah se low-end laptops par system slow ho jata hai.

Is problem ko solve karne ke liye, humne codebase me ek naya **`GeminiProvider`** add kiya hai. Ab hamara system Google ke Gemini API ko directly use kar sakta hai feedback generate karne ke liye.

## 1. Kya Changes Kiye Gaye?
1. **`services/feedback_service/llm.py`**: Yahan humne ek naya class banaya hai `GeminiProvider`. Ye class Google ki API (`generativelanguage.googleapis.com`) ko JSON request bhejti hai.
2. **`services/feedback_service/config.py`**: Configuration update ki gayi hai taaki system ab `"ollama"` aur `"gemini"` dono ko pehchaan sake.
3. **`services/feedback_service/runtime.py`**: Yahan humne logic update kiya hai—agar aap `.env` me `LLM_PROVIDER=gemini` set karte hain, toh system automatically local Ollama ki jagah Cloud-based Gemini ka use karna shuru kar deta hai.
4. **`docker-compose.yml` aur `.env.example`**: Environment variables me `GEMINI_API_KEY` ko add kiya gaya hai taaki security key securely Docker container ke andar paas ho sake.

## 2. Gemini Kaise Chalu Karein? (Steps)
Agar aapko apne laptop par Gemini chalana hai (taaki speed fast ho aur RAM bache):

1. **API Key Le:** [Google AI Studio](https://aistudio.google.com/app/apikey) par jayen aur ek free API key generate karein.
2. **`.env` File Update Karein:** Apni `.env` file kholiye (jo HAR-System folder me hai) aur wahan ye 3 lines update karein:
   ```env
   LLM_PROVIDER=gemini
   LLM_MODEL=gemma-2-27b-it
   GEMINI_API_KEY=AIzaSy... (yahan apni key daalein)
   ```
3. **Restart Karein:** Terminal me `./dev.sh down` chalayen, aur fir wapas `./dev.sh up` chalayen.

Ab aapki Feedback Service turant chalegi aur bina system lag kiye Cloud par AI analysis karke Dashboard me result bhejegi! 
VIVA me aap bol sakte hain: *"Humne system architecture ko modular banaya hai (using Protocol interfaces), isliye hum local AI (Ollama) se Cloud AI (Gemini) par seamlessly switch kar sakte hain without changing core logic."*
