from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import google.generativeai as genai
from datetime import datetime

app = FastAPI(title="AI Assistant Backend")

# ==========================================
# 1. API & DATABASE CREDENTIALS
# ==========================================
GEMINI_API_KEY = "AQ.Ab8RN6K-qab7RwiKUS6K5kDq9A1oFSzwUCSr7RU-Hjb0VXY9Jw"
MONGO_URI = "mongodb+srv://admin:jarvis123@cluster0.kbyb4fm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ==========================================
# 2. DATABASE CONNECTION
# ==========================================
client = MongoClient(MONGO_URI)
db = client["ai_assistant_db"]
chat_collection = db["conversations"]
call_logs_collection = db["call_records"]

# ==========================================
# 3. AI MODEL CONFIGURATION
# ==========================================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="models/gemini-3.6-flash",
    system_instruction="""
Tumhara naam Jarvis hai.
Tum ek smart multilingual AI assistant ho.
User ya Caller jis bhasha me baat kare (Hindi, English, Bhojpuri, etc.), usi bhasha me natural, polite aur clear jawab do.
"""
)

# ==========================================
# 4. REQUEST DATA MODELS
# ==========================================
class ChatRequest(BaseModel):
    user_id: str
    message: str

class CallLogRequest(BaseModel):
    caller_number: str
    transcription: str
    detected_language: str
    audio_url: str

# ==========================================
# 5. API ENDPOINTS
# ==========================================
@app.get("/")
def home():
    return {"status": "AI Server is Live and Running!"}

@app.post("/api/chat")
def chat_with_ai(data: ChatRequest):
    try:
        response = model.generate_content(data.message)
        reply = response.text

        # MongoDB me conversation history save karna
        chat_collection.insert_one({
            "user_id": data.user_id,
            "user_message": data.message,
            "assistant_reply": reply,
            "timestamp": datetime.utcnow()
        })

        return {"status": "success", "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-call")
def save_call_record(data: CallLogRequest):
    try:
        # Caller logs aur recording details save karna
        record = {
            "caller_number": data.caller_number,
            "transcription": data.transcription,
            "detected_language": data.detected_language,
            "audio_url": data.audio_url,
            "timestamp": datetime.utcnow()
        }
        call_logs_collection.insert_one(record)
        return {"status": "success", "message": "Call log & recording saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/call-logs")
def get_all_calls():
    try:
        logs = list(call_logs_collection.find({}, {"_id": 0}))
        return {"status": "success", "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))