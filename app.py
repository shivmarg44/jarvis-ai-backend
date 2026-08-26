import os
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="AI Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MONGO_URI = os.getenv("MONGO_URI", "").strip()
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
    if not GEMINI_KEY:
        return {"status": "error", "reply": "GEMINI_API_KEY Render par set nahi hai."}

    # Direct Google API URL with query key parameter
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"You are Jarvis, a smart AI assistant. Answer in Hinglish.\n\nUser: {data.message}\nJarvis:"}
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            res_json = response.json()

        if response.status_code != 200:
            err_msg = res_json.get("error", {}).get("message", str(res_json))
            print(f"GOOGLE ERROR: {err_msg}")
            return {"status": "error", "reply": f"Google Error: {err_msg}"}

        ai_reply = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()

        if chats_collection is not None:
            try:
                chats_collection.insert_one({
                    "user_id": data.user_id,
                    "user_message": data.message,
                    "ai_reply": ai_reply,
                    "timestamp": datetime.utcnow()
                })
            except Exception as db_err:
                print(f"DB Error: {db_err}")

        return {"status": "success", "reply": ai_reply}

    except Exception as e:
        print(f"CRASH ERROR: {str(e)}")
        return {"status": "error", "reply": f"Backend Error: {str(e)}"}