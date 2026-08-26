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

    # Available Groq models in order of priority
    candidate_models = [
        "llama-3.1-8b-instant",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    last_error = ""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for model_name in candidate_models:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are Jarvis, a smart AI assistant. Answer concisely in Hinglish."},
                    {"role": "user", "content": data.message}
                ]
            }
            try:
                response = await client.post(url, json=payload, headers=headers)
                res_json = response.json()

                if response.status_code == 200:
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
                else:
                    last_error = res_json.get("error", {}).get("message", str(res_json))
                    print(f"Failed with {model_name}: {last_error}")
            except Exception as e:
                last_error = str(e)

    return {"status": "error", "reply": f"Groq Error: {last_error}"}