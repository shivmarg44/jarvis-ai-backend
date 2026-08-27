import os
import shutil
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Jarvis Real-Time VoIP AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

call_logs = []
AUDIO_UPLOAD_DIR = "recordings"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
app.mount("/recordings", StaticFiles(directory=AUDIO_UPLOAD_DIR), name="recordings")


# ==========================================
# 1. TEXT CHAT ROUTE
# ==========================================

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"

@app.post("/api/chat")
async def chat_with_jarvis(payload: ChatMessage):
    user_msg = payload.message.lower().strip()
    if "hello" in user_msg or "hi" in user_msg:
        reply = "Hello! Main Jarvis hoon. Main aapki kya madad kar sakta hoon?"
    elif "kaise ho" in user_msg:
        reply = "Main badhiya hoon! Aap batayein?"
    else:
        reply = f"Aapka message prapt hua: '{payload.message}'"
    return {"status": "success", "reply": reply, "timestamp": datetime.now().strftime("%I:%M %p")}


# ==========================================
# 2. REAL-TIME 2-WAY VOIP WEBSOCKET ENGINE
# ==========================================

@app.websocket("/ws/voice-agent")
async def voice_agent_socket(websocket: WebSocket):
    """
    Live real-time 2-way VoIP voice stream channel.
    Connects phone mic directly to AI backend without cellular carrier limits.
    """
    await websocket.accept()
    caller_id = f"VoIP_User_{datetime.now().strftime('%M%S')}"
    print(f"🎙️ [VoIP AI] Live voice connection started with {caller_id}")

    try:
        # Step 1: Send AI Greeting audio / initial handshake
        await websocket.send_json({
            "event": "greeting",
            "text": "Namaste! Main Vishal ka AI Assistant Jarvis hoon. Kripya apna message boliye, main live sun raha hoon."
        })

        while True:
            # Receive real-time audio chunk or text packet from phone
            data = await websocket.receive_json()
            event_type = data.get("event")

            if event_type == "user_speaking":
                user_transcript = data.get("text", "")
                print(f"🗣️ Caller said: {user_transcript}")

                # AI generates instant response
                ai_reply = f"Ji, maine note kar liya hai: '{user_transcript}'. Main yeh sandesh Vishal tak pahuncha dunga."

                await websocket.send_json({
                    "event": "ai_response",
                    "text": ai_reply
                })

            elif event_type == "call_end":
                print(f"🔴 [VoIP AI] Call disconnected by {caller_id}")
                break

    except WebSocketDisconnect:
        print(f"⚠️ [VoIP AI] Stream disconnected unexpectedly.")
    finally:
        log_item = {
            "id": len(call_logs) + 1,
            "caller_number": caller_id,
            "duration_seconds": 15,
            "audio_url": "",
            "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "type": "Live VoIP AI Call (Real-Time)"
        }
        call_logs.insert(0, log_item)


# ==========================================
# 3. DIRECT DASHBOARD & CALL LOGS
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
def get_web_dashboard():
    rows = ""
    for log in call_logs:
        rows += f"""
        <div style="background: #1e293b; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 4px solid #38bdf8;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                <b style="color:#f8fafc; font-size:16px;">📞 {log['caller_number']}</b>
                <span style="color:#94a3b8; font-size:12px;">{log['timestamp']}</span>
            </div>
            <p style="color:#cbd5e1; margin: 4px 0 10px 0; font-size: 13px;">Type: {log['type']}</p>
        </div>
        """

    if not rows:
        rows = '<div style="color:#94a3b8; text-align:center; padding: 40px;">Koi live call record nahi hai. App se call start karein.</div>'

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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>⚡ JARVIS CALL HUB (LIVE VOIP)</h2>
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
    return {"status": "success", "total_calls": len(call_logs), "logs": call_logs}