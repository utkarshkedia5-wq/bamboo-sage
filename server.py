"""
SAGE Backend Server
===================
FastAPI server that:
1. Serves generated demo HTML pages
2. Proxies Claude API calls (so keys aren't exposed client-side)
3. Proxies Sarvam AI calls (STT + TTS)
4. Tracks demo opens and interactions
5. Webhook for Calendly bookings

Run with: uvicorn server:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import anthropic
import httpx
import os
import json
from pathlib import Path
from datetime import datetime
import sqlite3

app = FastAPI(title="SAGE Voice AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
OUTPUT_DIR = Path("output")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─── DATABASE SETUP ────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect("sage_leads.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS demo_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demo_slug TEXT,
            company TEXT,
            event_type TEXT,
            user_ip TEXT,
            timestamp TEXT,
            data TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demo_slug TEXT,
            role TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


def log_event(demo_slug: str, company: str, event_type: str, ip: str, data: dict = {}):
    conn = sqlite3.connect("sage_leads.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO demo_events (demo_slug, company, event_type, user_ip, timestamp, data) VALUES (?,?,?,?,?,?)",
        (demo_slug, company, event_type, ip, datetime.utcnow().isoformat(), json.dumps(data))
    )
    conn.commit()
    conn.close()


# ─── DEMO PAGES ───────────────────────────────────────────────────────────────

@app.get("/demo/{filename}", response_class=HTMLResponse)
async def serve_demo(filename: str, request: Request):
    """Serve a generated demo page and track the open."""
    demo_path = OUTPUT_DIR / filename
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo not found")

    slug = filename.replace("demo_", "").replace(".html", "")
    log_event(slug, slug, "demo_opened", request.client.host)

    return HTMLResponse(content=demo_path.read_text(encoding='utf-8'))


# ─── CLAUDE PROXY ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    system_prompt: str
    messages: list[dict]
    demo_slug: str = ""
    company: str = ""

@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    """Proxy Claude API calls from the demo page."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=req.system_prompt,
            messages=req.messages
        )
        reply = response.content[0].text

        # Log conversation
        if req.demo_slug:
            log_event(req.demo_slug, req.company, "conversation_turn",
                      request.client.host, {"reply_preview": reply[:100]})

        return {"reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── SARVAM AI PROXY ──────────────────────────────────────────────────────────
"""
#@app.post("/api/stt")
#async def speech_to_text(request: Request):
   """Proxy Sarvam AI Speech-to-Text."""
   # form = await request.form()
   # audio_file = form.get("file")
   # language_code = form.get("language_code", "hi-IN")

   # async with httpx.AsyncClient() as http_client:
    #    files = {"file": (audio_file.filename, await audio_file.read(), "audio/webm")}
    #    data = {"language_code": language_code}
    #    headers = {"api-subscription-key": SARVAM_API_KEY}
#
      #  res = await http_client.post(
     #       "https://api.sarvam.ai/speech-to-text",
       #     headers=headers, files=files, data=data, timeout=15
       # )
       # return res.json()


#class TTSRequest(BaseModel):
    #text: str
    #language_code: str = "hi-IN"
    #speaker: str = "meera"
       """





@app.post("/api/stt")
async def speech_to_text(request: Request):
    try:
        form = await request.form()
        audio_file = form.get("file")
        language_code = form.get("language_code", "hi-IN")

        # 🔴 Validate input
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file received")

        file_bytes = await audio_file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        print("📥 Received audio:", audio_file.filename, len(file_bytes))

        async with httpx.AsyncClient(timeout=20) as http_client:
            files = {
                "file": (
                    audio_file.filename or "audio.webm",
                    file_bytes,
                    audio_file.content_type or "audio/webm"
                )
            }

            data = {"language_code": language_code}

            headers = {
                "api-subscription-key": SARVAM_API_KEY
            }

            res = await http_client.post(
                "https://api.sarvam.ai/speech-to-text",
                headers=headers,
                files=files,
                data=data
            )

            print("🧠 SARVAM STATUS:", res.status_code)
            print("🧠 SARVAM RESPONSE:", res.text[:300])

            if res.status_code != 200:
                raise HTTPException(status_code=500, detail=res.text)

            return res.json()

    except Exception as e:
        print("❌ STT ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
class TTSRequest(BaseModel):
    text: str
    language_code: str = "hi-IN"
    speaker: str = "meera"

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    try:
        async with httpx.AsyncClient(timeout=20) as http_client:
            headers = {
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json"
            }

            payload = {
                "inputs": [req.text],
                "target_language_code": req.language_code,
                "speaker": req.speaker or "meera",
                "speech_sample_rate": 24000  # slightly better
            }

            res = await http_client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers=headers,
                json=payload
            )

            print("🔊 TTS STATUS:", res.status_code)
            print("🔊 TTS RESPONSE:", res.text[:200])

            if res.status_code != 200:
                raise HTTPException(status_code=500, detail=res.text)

            return res.json()

    except Exception as e:
        print("❌ TTS ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


    
    

   """ 
@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    """Proxy Sarvam AI Text-to-Speech."""
    async with httpx.AsyncClient() as http_client:
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [req.text],
            "target_language_code": req.language_code,
            "speaker": req.speaker,
            "speech_sample_rate": 22050
        }
        res = await http_client.post(
            "https://api.sarvam.ai/text-to-speech",
            headers=headers, json=payload, timeout=15
        )
        return res.json()
        """


# ─── ANALYTICS DASHBOARD ──────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple analytics dashboard."""
    conn = sqlite3.connect("sage_leads.db")
    c = conn.cursor()

    c.execute("""
        SELECT demo_slug, event_type, COUNT(*) as count, MAX(timestamp) as last_seen
        FROM demo_events GROUP BY demo_slug, event_type ORDER BY last_seen DESC
    """)
    rows = c.fetchall()
    conn.close()

    rows_html = ''.join([f"""
        <tr>
            <td>{r[0]}</td>
            <td><span class="badge">{r[1]}</span></td>
            <td><strong>{r[2]}</strong></td>
            <td style="color:#888">{r[3][:16]}</td>
        </tr>
    """ for r in rows])

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>SAGE Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family:'DM Sans',sans-serif; background:#f8f9fa; margin:0; padding:32px; }}
        h1 {{ font-size:1.8rem; margin-bottom:4px; }}
        .subtitle {{ color:#888; margin-bottom:32px; }}
        table {{ width:100%; border-collapse:collapse; background:white; border-radius:12px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.06); }}
        th {{ background:#0f1b2d; color:white; padding:14px 20px; text-align:left; font-size:0.85rem; letter-spacing:0.05em; }}
        td {{ padding:14px 20px; border-bottom:1px solid #f0f0f0; }}
        .badge {{ background:#e8f5e9; color:#2e7d32; padding:4px 10px; border-radius:100px; font-size:0.8rem; font-weight:600; }}
    </style>
</head>
<body>
    <h1>🏗️ SAGE Dashboard</h1>
    <p class="subtitle">Live demo tracking — who opened, who interacted, who booked</p>
    <table>
        <thead><tr><th>Demo Slug</th><th>Event</th><th>Count</th><th>Last Seen</th></tr></thead>
        <tbody>{rows_html or '<tr><td colspan="4" style="text-align:center;color:#aaa;padding:40px">No events yet</td></tr>'}</tbody>
    </table>
</body>
</html>"""


# ─── CALENDLY WEBHOOK ─────────────────────────────────────────────────────────

@app.post("/webhook/calendly")
async def calendly_webhook(request: Request):
    """Receive Calendly booking notifications."""
    body = await request.json()
    event_type = body.get("event", "")

    if "invitee.created" in event_type:
        invitee = body.get("payload", {}).get("invitee", {})
        name = invitee.get("name", "")
        email = invitee.get("email", "")
        scheduled_at = invitee.get("scheduled_event", {}).get("start_time", "")

        log_event("calendly", name, "booking_confirmed", "",
                  {"name": name, "email": email, "scheduled_at": scheduled_at})

        print(f"🎉 NEW BOOKING: {name} ({email}) — {scheduled_at}")

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


# ─── LIGHTWEIGHT EVENT TRACKER (called from demo page JS) ─────────────────────

class TrackRequest(BaseModel):
    slug: str
    event: str
    company: str = ""

@app.post("/api/track")
async def track_event(req: TrackRequest, request: Request):
    """Track demo page events (open, call_start, etc.) from the browser."""
    log_event(req.slug, req.company, req.event, request.client.host)
    return {"ok": True}
