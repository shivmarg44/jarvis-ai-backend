import os
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pymongo import MongoClient
import httpx

app = FastAPI(title="AI Assistant Backend")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audio files store karne ka directory
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)
app.mount("/recordings", StaticFiles(directory=RECORDINGS_DIR), name="recordings")

# API Keys & Database
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MONGO_URI = os.getenv("MONGO_URI", "").strip()

chats_collection = None
calls_collection = None

# In-memory backup agar MongoDB connect na ho
local_call_logs = []

if MONGO_URI:
    try:
        db_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = db_client["jarvis_db"]
        chats_collection = db["conversations"]
        calls_collection = db["call_logs"]
        print("MongoDB Connected Successfully!")
    except Exception as e:
        print(f"MongoDB Init Warning: {e}")

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.get("/")
def home():
    return {"status": "online", "message": "Jarvis AI is Live"}

# ----------------- CALL MANAGEMENT ENDPOINTS -----------------

@app.post("/api/call/upload-recording")
async def upload_call_recording(
    caller_number: str = Form(...),
    duration_seconds: str = Form("0"),
    audio_file: UploadFile = File(...)
):
    try:
        # File save karna
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_number = caller_number.replace("+", "").strip()
        filename = f"call_{safe_number}_{timestamp_str}_{audio_file.filename}"
        file_path = os.path.join(RECORDINGS_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        audio_url = f"/recordings/{filename}"
        recorded_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

        log_data = {
            "caller_number": caller_number,
            "duration_seconds": duration_seconds,
            "audio_url": audio_url,
            "recorded_at": recorded_time,
            "timestamp": datetime.utcnow()
        }

        # MongoDB me save ya local memory me
        if calls_collection is not None:
            calls_collection.insert_one(log_data)
        
        # Local memory me bhi save rakhein
        log_data_copy = log_data.copy()
        if "_id" in log_data_copy:
            log_data_copy["_id"] = str(log_data_copy["_id"])
        local_call_logs.insert(0, log_data_copy)

        print(f"Recorded audio saved for {caller_number}: {file_path}")
        return {"status": "success", "message": "Call recording saved successfully", "url": audio_url}

    except Exception as e:
        print(f"Upload Error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/call/logs")
def get_call_logs():
    try:
        if calls_collection is not None:
            logs = list(calls_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(50))
            return {"status": "success", "logs": logs}
        return {"status": "success", "logs": local_call_logs}
    except Exception as e:
        return {"status": "error", "message": str(e), "logs": local_call_logs}

# ----------------- AI CHAT ENDPOINT -----------------

@app.post("/api/chat")
async def chat_with_ai(data: ChatRequest):
    if not API_KEY:
        return {"status": "error", "reply": "API Key Render par set nahi hai."}

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "user",
                "content": f"You are Jarvis AI. Reply concisely in friendly Hinglish to the user.\n\nUser: {data.message}\nJarvis:"
            }
        ],
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            res_json = response.json()

        if response.status_code != 200:
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