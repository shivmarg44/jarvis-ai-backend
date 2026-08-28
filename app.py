import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from twilio.twiml.voice_response import Gather, VoiceResponse

app = FastAPI(title="Jarvis Cloud Voice Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory call log storage
call_logs = []


# ==========================================
# 1. CLOUD VOICE WEBHOOKS (IN-CALL ENGINE)
# ==========================================

@app.post("/voice/incoming")
async def incoming_call_webhook(request: Request):
    """
    Jab caller number dial karega, Cloud Telephony is endpoint ko hit karega.
    Jarvis direct line ke andar studio voice me bolega aur caller ki aawaz sunega.
    """
    form_data = await request.form()
    caller_number = form_data.get("From", "Unknown Caller")
    print(f"📞 [Cloud Bridge] Live Incoming Call from: {caller_number}")

    response = VoiceResponse()

    # Step A: Gather User Speech via High-Accuracy STT
    gather = Gather(
        input="speech",
        action="/voice/process-speech",
        method="POST",
        language="hi-IN",
        speech_timeout="auto",
        timeout=4
    )

    # Line ke andar crystal clear greeting
    gather.say(
        "Namaste! Main Vishal ka AI Assistant Jarvis hoon. Kripya apna sandesh boliye, main sun raha hoon.",
        language="hi-IN",
        voice="Polly.Aditi"
    )

    response.append(gather)

    # Agar caller kuch na bole
    response.say("Mujhe koi aawaz sunai nahi di. Call disconnect ki ja rahi hai. Dhanyawad.", language="hi-IN", voice="Polly.Aditi")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")


@app.post("/voice/process-speech")
async def process_speech_webhook(request: Request):
    """
    Caller jo bolega, wo yahan text ban kar aayega aur Jarvis instant line par reply dega.
    """
    form_data = await request.form()
    caller_number = form_data.get("From", "Unknown Caller")
    speech_result = form_data.get("SpeechResult", "").strip()

    print(f"🗣️ [Caller: {caller_number}] Said: '{speech_result}'")

    response = VoiceResponse()

    if speech_result:
        # AI Response Generation
        ai_reply = f"Ji, maine aapka sandesh note kar liya hai. Vishal ko jald hi suchit kar diya jayega. Dhanyawad!"

        # Save to Dashboard Logs
        log_entry = {
            "id": len(call_logs) + 1,
            "caller_number": caller_number,
            "transcript": speech_result,
            "ai_response": ai_reply,
            "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "status": "Success"
        }
        call_logs.insert(0, log_entry)

        # Line par AI ka crystal clear reply
        response.say(ai_reply, language="hi-IN", voice="Polly.Aditi")
        response.pause(length=1)
        response.hangup()
    else:
        response.say("Aapki aawaz theek se nahi suni ja saki. Kripya dobara call karein.", language="hi-IN", voice="Polly.Aditi")
        response.hangup()

    return Response(content=str(response), media_type="application/xml")


# ==========================================
# 2. REST CHAT API (MOBILE APP / TESTING)
# ==========================================

class ChatMessage(BaseModel):
    message: str
    caller_number: Optional[str] = "App_User"

@app.post("/api/chat")
async def chat_api(payload: ChatMessage):
    user_msg = payload.message.lower().strip()
    if "hello" in user_msg or "hi" in user_msg:
        reply = "Namaste! Main Jarvis hoon. Main aapki kya madad kar sakta hoon?"
    else:
        reply = f"Aapka sandesh prapt hua: '{payload.message}'. Main ise Vishal tak pahuncha dunga."
    return {"status": "success", "reply": reply, "timestamp": datetime.now().strftime("%I:%M %p")}


# ==========================================
# 3. LIVE WEB DASHBOARD
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
def get_web_dashboard():
    rows = ""
    for log in call_logs:
        rows += f"""
        <div style="background: #1e293b; padding: 18px; border-radius: 12px; margin-bottom: 14px; border-left: 4px solid #38bdf8; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                <b style="color:#f8fafc; font-size:16px;">📞 {log['caller_number']}</b>
                <span style="color:#94a3b8; font-size:12px;">{log['timestamp']}</span>
            </div>
            <p style="color:#e2e8f0; margin: 6px 0; font-size: 14px;"><b>Caller:</b> "{log['transcript']}"</p>
            <p style="color:#38bdf8; margin: 4px 0; font-size: 13px;"><b>Jarvis Reply:</b> "{log['ai_response']}"</p>
        </div>
        """

    if not rows:
        rows = '<div style="color:#94a3b8; text-align:center; padding: 50px 20px;">Abhi koi live call logs nahi hain. Call aane par yahan real-time dikhega.</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jarvis Cloud Voice Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 700px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 25px; }}
            .btn {{ background: #0284c7; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; }}
            .btn:hover {{ background: #0369a1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h2 style="margin:0; color:#38bdf8;">⚡ JARVIS CLOUD VOICE HUB</h2>
                    <span style="color:#4ade80; font-size:13px;">● Cloud Bridge Active</span>
                </div>
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