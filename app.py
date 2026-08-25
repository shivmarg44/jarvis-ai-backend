import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

app = FastAPI(title="AI Assistant Backend")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Gemini AI Config
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# 2. MongoDB Setup with Fallback
MONGO_URI = os.getenv("MONGO_URI", "")
db_client = None
chats_collection = None
calls_collection = None

if MONGO_URI:
    try:
        db_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = db_client["jarvis_db"]
        chats_collection = db["conversations"]
        calls_collection = db["call_logs"]
    except Exception as e:
        print(f"MongoDB connection init warning: {e}")

class ChatRequest(BaseModel):
    user_id: str
    message: str

class CallLogRequest(BaseModel):
    user_id: str
    phone_number: str
    call_type: str
    duration: int
    summary: str = ""

@app.get("/")
def home():
    return {"status": "online", "message": "Jarvis AI Backend is Running 24/7!"}

@app.post("/api/chat")
async def chat_with_ai(data: ChatRequest):
    if not GEMINI_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable is not set on Render.")
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        system_instruction = (
            "You are Jarvis, a smart, friendly, and witty AI assistant. "
            "Respond in natural Hinglish (Hindi + English mix) unless the user asks otherwise. "
            "Keep answers clear, helpful, and concise."
        )
        prompt = f"{system_instruction}\n\nUser: {data.message}\nJarvis:"
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()

        # Save to DB if connected
        if chats_collection is not None:
            try:
                chats_collection.insert_one({
                    "user_id": data.user_id,
                    "user_message": data.message,
                    "ai_reply": ai_reply,
                    "timestamp": datetime.utcnow()
                })
            except Exception as db_err:
                print(f"Database log error: {db_err}")

        return {"status": "success", "reply": ai_reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))