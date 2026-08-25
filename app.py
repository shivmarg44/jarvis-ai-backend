import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

# 1. FastAPI App Initialization
app = FastAPI(title="AI Assistant Backend")

# 2. CORS Setup (Browser & Mobile Access ke liye compulsory)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "Aapki_Gemini_API_Key_Yahan")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 4. MongoDB Database Setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin123@cluster0.mongodb.net/?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["jarvis_db"]
chats_collection = db["conversations"]
calls_collection = db["call_logs"]

# 5. Pydantic Models (Request Structure)
class ChatRequest(BaseModel):
    user_id: str
    message: str

class CallLogRequest(BaseModel):
    user_id: str
    phone_number: str
    call_type: str
    duration: int
    summary: str = ""

# 6. Routes / Endpoints

@app.get("/")
def home():
    return {"status": "online", "message": "Jarvis AI Backend is Running 24/7!"}

@app.post("/api/chat")
async def chat_with_ai(data: ChatRequest):
    try:
        # Prompt setup
        system_instruction = (
            "You are Jarvis, a smart, friendly, and witty AI assistant. "
            "Respond in natural Hinglish (Hindi + English mix) unless the user asks otherwise. "
            "Keep answers clear, helpful, and concise."
        )
        prompt = f"{system_instruction}\n\nUser: {data.message}\nJarvis:"
        
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()

        # Database me record save karna
        chats_collection.insert_one({
            "user_id": data.user_id,
            "user_message": data.message,
            "ai_reply": ai_reply,
            "timestamp": datetime.utcnow()
        })

        return {"status": "success", "reply": ai_reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-call")
async def save_call_record(data: CallLogRequest):
    try:
        record = {
            "user_id": data.user_id,
            "phone_number": data.phone_number,
            "call_type": data.call_type,
            "duration": data.duration,
            "summary": data.summary,
            "timestamp": datetime.utcnow()
        }
        result = calls_collection.insert_one(record)
        return {"status": "success", "inserted_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/call-logs")
async def get_all_calls(user_id: str = "vishal_mobile"):
    try:
        logs = list(calls_collection.find({"user_id": user_id}, {"_id": 0}))
        return {"status": "success", "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))