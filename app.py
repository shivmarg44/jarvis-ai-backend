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

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

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
    if not API_KEY:
        return {"status": "error", "reply": "API Key Render par set nahi hai."}

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Groq ke active models auto-fetch karein
            models_res = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
            models_data = models_res.json()
            
            # Text generation models filter karein (whisper/audio exclude karke)
            available_models = [
                m["id"] for m in models_data.get("data", [])
                if "whisper" not in m["id"].lower() and "embed" not in m["id"].lower()
            ]

            if not available_models:
                return {"status": "error", "reply": "Koi active Groq model nahi mila."}

            # 2. Pehle available active model ke sath chat karein
            chosen_model = available_models[0]
            for m in available_models:
                if "llama" in m.lower():
                    chosen_model = m
                    break

            payload = {
                "model": chosen_model,
                "messages": [
                    {"role": "system", "content": "You are Jarvis, an intelligent and helpful AI assistant. Always respond concisely in friendly Hinglish."},
                    {"role": "user", "content": data.message}
                ]
            }

            chat_res = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            res_json = chat_res.json()

            if chat_res.status_code != 200:
                err_msg = res_json.get("error", {}).get("message", str(res_json))
                return {"status": "error", "reply": f"Groq Error: {err_msg}"}

            ai_reply = res_json["choices"][0]["message"]["content"].strip()

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
        return {"status": "error", "reply": f"Backend Error: {str(e)}"}