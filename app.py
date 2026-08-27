import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Jarvis AI Cloud Backend & Assistant")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
call_logs = []

# Directory for recorded audio files
AUDIO_UPLOAD_DIR = "recordings"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
app.mount("/recordings", StaticFiles(directory=AUDIO_UPLOAD_DIR), name="recordings")


# ==========================================
# 1. ROOT & STATUS CHECK
# ==========================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Jarvis AI Assistant & Call Hub",
        "total_calls_logged": len(call_logs)
    }


# ==========================================
# 2. JARVIS CHAT / MESSAGE ENDPOINT (RESTORED)
# ==========================================

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"

@app.post("/api/chat")
async def chat_with_jarvis(payload: ChatMessage):
    """
    Restores the Jarvis text message / chat response capability.
    """
    user_msg = payload.message.lower().strip()
    
    # Intelligent quick rule responses / fallback
    if "hello" in user_msg or "hi" in user_msg:
        reply = "Hello! Main Jarvis hoon. Main aapki kya madad kar sakta hoon?"
    elif "kaise ho" in user_msg or "how are you" in user_msg:
        reply = "Main bilkul theek hoon! Aap batayein, aaj ka kya plan hai?"
    elif "call" in user_msg or "recording" in user_msg:
        reply = f"Total {len(call_logs)} call logs recorded hain. Aap dashboard par jaakar direct audio sun sakte hain."
    else:
        reply = f"Maine aapka message prapt kar liya: '{payload.message}'. Jarvis system poori tarah active hai!"

    return {
        "status": "success",
        "reply": reply,
        "timestamp": datetime.now().strftime("%I:%M %p")
    }


# ==========================================
# 3. DIRECT MOBILE APP UPLOAD ENDPOINT
# ==========================================

@app.post("/api/call/upload-recording")
async def upload_call_recording(
    caller_number: str = Form("Unknown"),
    duration_seconds: int = Form(0),
    audio_file: UploadFile = File(...)
):
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{caller_number}_{audio_file.filename}"
    file_path = os.path.join(AUDIO_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)

    audio_url = f"https://jarvis-ai-backend-y402.onrender.com/recordings/{filename}"

    log_item = {
        "id": len(call_logs) + 1,
        "caller_number": caller_number,
        "duration_seconds": duration_seconds,
        "audio_url": audio_url,
        "timestamp": timestamp,
        "type": "Direct Voice Stream"
    }

    call_logs.insert(0, log_item)
    print(f"✅ Call recording stored from {caller_number}: {filename}")

    return {
        "status": "success",
        "message": "Call recording uploaded successfully",
        "log": log_item
    }


# ==========================================
# 4. BUILT-IN WEB DASHBOARD (NO NOT FOUND ERROR)
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
def get_web_dashboard():
    """
    Direct web dashboard hosted right inside FastAPI backend.
    No need to manage local file paths.
    """
    rows = ""
    for log in call_logs:
        rows += f"""
        <div style="background: #1e293b; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 4px solid #38bdf8;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                <b style="color:#f8fafc; font-size:16px;">📞 {log['caller_number']}</b>
                <span style="color:#94a3b8; font-size:12px;">{log['timestamp']}</span>
            </div>
            <p style="color:#cbd5e1; margin: 4px 0 10px 0; font-size: 13px;">Duration: {log['duration_seconds']}s | Type: {log['type']}</p>
            <audio controls style="width: 100%; height: 35px;">
                <source src="{log['audio_url']}" type="audio/mp4">
                <source src="{log['audio_url']}" type="audio/mpeg">
                Aapka browser audio support nahi karta.
            </audio>
        </div>
        """

    if not rows:
        rows = '<div style="color:#94a3b8; text-align:center; padding: 40px;">Abhi tak koi recording upload nahi hui hai. App se live test ya call karke refresh karein.</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jarvis Call Assistant Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 650px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }}
            .btn {{ background: #0284c7; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
            .btn:hover {{ background: #0369a1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>⚡ JARVIS CALL HUB</h2>
                <button class="btn" onclick="location.reload()">🔄 Refresh</button>
            </div>
            <div id="logs-container">
                {rows}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/call/logs")
def get_call_logs():
    return {
        "status": "success",
        "total_calls": len(call_logs),
        "logs": call_logs
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.py:app", host="0.0.0.0", port=8000, reload=True)