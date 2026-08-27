import os
import shutil
from datetime import datetime
from typing import List
from fastapi import FastAPI, File, Form, UploadFile, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Jarvis AI Cloud Backend & Call Center")

# Enable CORS for local and web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory call storage (can also connect to MongoDB)
call_logs = []

# Directory to save recorded call audio files locally on server
AUDIO_UPLOAD_DIR = "recordings"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)

# Mount recordings folder for direct playback access
app.mount("/recordings", StaticFiles(directory=AUDIO_UPLOAD_DIR), name="recordings")


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Jarvis AI Cloud Telephony & Assistant Server",
        "total_calls_logged": len(call_logs)
    }


# ==========================================
# 1. DIRECT MOBILE APP UPLOAD ENDPOINT
# ==========================================

@app.post("/api/call/upload-recording")
async def upload_call_recording(
    caller_number: str = Form("Unknown"),
    duration_seconds: int = Form(0),
    audio_file: UploadFile = File(...)
):
    """
    Receives recorded audio files directly from the Android App,
    saves the file, and stores the metadata for the dashboard.
    """
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{caller_number}_{audio_file.filename}"
    file_path = os.path.join(AUDIO_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)

    audio_url = f"/recordings/{filename}"

    log_item = {
        "id": len(call_logs) + 1,
        "caller_number": caller_number,
        "duration_seconds": duration_seconds,
        "audio_url": audio_url,
        "timestamp": timestamp,
        "type": "Android App Stream"
    }

    call_logs.insert(0, log_item)
    print(f"✅ [Android App] Call recorded from {caller_number}: {filename}")

    return {
        "status": "success",
        "message": "Call recording uploaded successfully",
        "log": log_item
    }


# ==========================================
# 2. TWILIO CLOUD TELEPHONY AI WEBHOOKS
# ==========================================

@app.post("/api/twilio/voice")
async def twilio_voice_webhook(
    From: str = Form(None),
    CallSid: str = Form(None)
):
    """
    Executed when an incoming call hits the Twilio Virtual Number.
    Jarvis answers the carrier line and speaks directly to the caller in Hindi.
    """
    caller = From or "Unknown_Caller"
    print(f"📞 [Twilio Carrier] Incoming call from {caller} (CallSid: {CallSid})")

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN" voice="Polly.Aditi">
        Namaste. Main Vishal ka AI Assistant Jarvis hoon. Vishal abhi vyast hain. Kripya beep ke baad apna sandesh chodiye.
    </Say>
    <Record 
        action="/api/twilio/recording-complete?caller={caller}" 
        method="POST" 
        maxLength="180" 
        playBeep="true" 
        trim="trim-silence"
    />
    <Say language="hi-IN" voice="Polly.Aditi">
        Dhanyawad. Aapka sandesh surakshit kar liya gaya hai. Alvida.
    </Say>
    <Hangup/>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")


@app.post("/api/twilio/recording-complete")
async def twilio_recording_complete(
    caller: str,
    RecordingUrl: str = Form(None),
    RecordingDuration: int = Form(0),
    CallSid: str = Form(None)
):
    """
    Executed when the caller finishes speaking and disconnects.
    Receives high-definition audio URL directly from Twilio.
    """
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    
    # Twilio provides .mp3 format by appending .mp3 to the URL
    final_audio_url = f"{RecordingUrl}.mp3" if RecordingUrl else ""

    log_item = {
        "id": len(call_logs) + 1,
        "caller_number": caller,
        "duration_seconds": RecordingDuration,
        "audio_url": final_audio_url,
        "timestamp": timestamp,
        "type": "Twilio Carrier AI (HD)"
    }

    call_logs.insert(0, log_item)
    print(f"✅ [Twilio Carrier] Recorded {RecordingDuration}s message from {caller}: {final_audio_url}")

    return {"status": "success", "message": "Twilio call log saved"}


# ==========================================
# 3. DASHBOARD LOGS FETCH ENDPOINT
# ==========================================

@app.get("/api/call/logs")
def get_call_logs():
    """
    Returns all logged calls (both Android App and Twilio Carrier calls)
    to render on index.html.
    """
    return {
        "status": "success",
        "total_calls": len(call_logs),
        "logs": call_logs
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.py:app", host="0.0.0.0", port=8000, reload=True)