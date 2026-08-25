import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from pymongo import MongoClient

app = FastAPI(title="AI Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google GenAI Client with Key
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
client = None
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"GenAI Init Error: {e}")

# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI", "")
chats_collection = None
if MONGO_URI:
    try:
        db_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = db_client["jarvis_db"]
        chats_collection = db["conversations"]
    except Exception as e:
        print(f"MongoDB Init Warning: {e}")

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.get("/")
def home():
    return {"status": "online", "message": "Jarvis AI is Live"}

@app.post("/api/chat")
async def chat_with_ai(data: ChatRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini Client is not initialized. Check GEMINI_API_KEY on Render.")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"You are Jarvis, a smart and witty assistant. Respond in clear Hinglish.\n\nUser: {data.message}\nJarvis:",
        )
        ai_reply = response.text.strip()

        if chats_collection is not None:
            try:
                chats_collection.insert_one({
                    "user_id": data.user_id,
                    "user_message": data.message,
                    "ai_reply": ai_reply,
                    "timestamp": datetime.utcnow()
                })
            except Exception as db_err:
                print(f"DB Insert Error: {db_err}")

        return {"status": "success", "reply": ai_reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))