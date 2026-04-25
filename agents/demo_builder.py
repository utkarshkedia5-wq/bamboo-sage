"""
Demo Builder Agent — Bamboo AI
================================
Generates a personalized HTML demo page for each builder using the
SCREENSHOT APPROACH — the client sees their own website as a background
with the Bamboo AI voice widget floating on top.

Strategy:
  1. Get a screenshot of their website via thum.io (free, no key needed)
     OR screenshotone.com (100 free/month, better quality)
  2. Use screenshot as full-page background image
  3. Overlay the Bamboo AI voice widget (floating bottom-right)
  4. Show intro card explaining what they're seeing
  5. Pain point cards on the left
  6. Calendly CTA at the top

This is what top sales orgs actually do for demos.
Looks identical to their real site. Works every time.
"""

import anthropic
import json
from pathlib import Path
import hashlib
import os
import urllib.parse

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

CALENDLY_URL       = os.getenv("CALENDLY_URL",       "https://calendly.com/your-link/30min")
BACKEND_URL        = os.getenv("BACKEND_URL",        "https://api.bamboo-ai.in")
SARVAM_API_KEY     = os.getenv("SARVAM_API_KEY",     "")
SCREENSHOT_API_KEY = os.getenv("SCREENSHOT_API_KEY", "")   # screenshotone.com


class DemoBuilderAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()

    async def build(self, lead: dict, research: dict) -> Path:
        slug       = self._make_slug(research["company_name"])
        demo_path  = OUTPUT_DIR / f"demo_{slug}.html"
        shot_url   = self._get_screenshot_url(lead.get("website", ""))
        voice_prompt = self._make_voice_prompt(research)
        html       = self._generate_html(research, voice_prompt, slug, shot_url)
        demo_path.write_text(html, encoding="utf-8")
        return demo_path

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_slug(self, company: str) -> str:
        s = "".join(c if c.isalnum() or c == "-" else "-" for c in company.lower().replace(" ", "-"))
        return f"{s}-{hashlib.md5(company.encode()).hexdigest()[:6]}"

    def _get_screenshot_url(self, website: str) -> str:
        if not website:
            return ""
        if not website.startswith("http"):
            website = "https://" + website
        if SCREENSHOT_API_KEY:
            encoded = urllib.parse.quote(website, safe="")
            return (
                f"https://api.screenshotone.com/take"
                f"?access_key={SCREENSHOT_API_KEY}"
                f"&url={encoded}&full_page=true"
                f"&viewport_width=1280&viewport_height=900"
                f"&format=jpg&image_quality=85"
                f"&block_ads=true&block_cookie_banners=true"
            )
        # Free fallback — thum.io, no API key needed
        return f"https://image.thum.io/get/width/1280/crop/900/allowJPG/wait/3/noanimate/{website}"

    def _make_voice_prompt(self, research: dict) -> str:
        projects = ", ".join(research.get("projects", ["Premium Properties"])[:3])
        lang     = research.get("primary_language", "English")
        return (
            f"You are a smart voice AI assistant for {research['company_name']}, "
            f"a real estate developer in {research.get('city', 'India')}.\n\n"
            f"Your role: Handle property inquiries, qualify leads, and schedule site visits — 24/7.\n\n"
            f"About {research['company_name']}:\n"
            f"- Projects: {projects}\n"
            f"- Price range: {research.get('price_range', 'Rs 50L - Rs 2Cr')}\n"
            f"- Targeting: {research.get('target_customer', 'homebuyers')}\n"
            f"- Key strength: {research.get('key_selling_point', 'Quality homes')}\n\n"
            f"Personality: Warm, knowledgeable, helpful. Speak primarily in {lang} "
            f"but switch if the customer prefers another language.\n\n"
            f"When someone calls:\n"
            f"1. Greet warmly using {research['company_name']}'s name\n"
            f"2. Ask what they are looking for (budget, BHK, timeline)\n"
            f"3. Share relevant project info\n"
            f"4. Offer to schedule a site visit or send brochure on WhatsApp\n"
            f"5. Capture their name and number before ending\n\n"
            f"NEVER say you are an AI unless directly asked. You represent {research['company_name']}.\n"
            f"Keep responses concise — under 60 words, conversational."
        )

    # ── HTML ─────────────────────────────────────────────────────────────────

    def _generate_html(self, research: dict, voice_prompt: str, slug: str, shot_url: str) -> str:
        co       = research["company_name"]
        city     = research.get("city", "India")
        lang     = research.get("primary_language", "English")
        projects = research.get("projects", ["Premium Residences"])[:3]
        price    = research.get("price_range", "")
        pains    = research.get("pain_points", [
            "Losing leads after office hours",
            "Sales team overwhelmed during project launches",
            "Slow follow-up hurts conversions",
        ])
        tone = research.get("tone", "professional")

        palettes = {
            "luxury":       ("#c9a84c", "#0a0a0a"),
            "affordable":   ("#e85d26", "#1a3a6b"),
            "trusted":      ("#52b788", "#1b4332"),
            "modern":       ("#4361ee", "#0f1b2d"),
            "professional": ("#e94560", "#1a1a2e"),
        }
        accent, dark = palettes.get(tone, palettes["professional"])

        lang_map = {"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","Kannada":"kn-IN","Marathi":"mr-IN","English":"en-IN"}
        sarvam_lang = lang_map.get(lang, "en-IN")

        prompt_js  = json.dumps(voice_prompt)
        projects_js = json.dumps(projects)

        bg_css = f"background:url('{shot_url}') center top/cover no-repeat;" if shot_url else f"background:{dark};"
        overlay_opacity = "0.55" if shot_url else "0.0"

        pain_cards_html = ""
        icons = ["⚡", "📞", "📊"]
        labels = ["Problem", "Challenge", "Impact"]
        for i, p in enumerate(pains[:3]):
            pain_cards_html += f"""
            <div class="pain-card" style="animation-delay:{i*0.1}s">
                <div class="pain-icon">{icons[i]}</div>
                <div class="pain-text">
                    <strong>{labels[i]}</strong>{p}
                </div>
            </div>"""

        lang_btns = [
            ("en-IN","EN"), ("hi-IN","हिं"), ("te-IN","తె"), ("mr-IN","म")
        ]
        lang_btns_html = ""
        for code, label in lang_btns:
            active = "active" if code == sarvam_lang else ""
            lang_btns_html += f'<button class="lang-btn {active}" onclick="setLang(\'{code}\',this)">{label}</button>'

        proj_str = ", ".join(projects[:2]) if projects else "properties"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bamboo AI Demo — {co}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Figtree:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--accent:{accent};--dark:{dark};--r:18px}}
body{{font-family:'Figtree',sans-serif;background:{dark};min-height:100vh;overflow-x:hidden}}

/* stage */
.stage{{position:relative;min-height:100vh;width:100%;{bg_css}}}
.overlay{{position:absolute;inset:0;background:rgba(0,0,0,{overlay_opacity});pointer-events:none}}

/* top bar */
.topbar{{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;justify-content:space-between;align-items:center;padding:13px 28px;background:rgba(0,0,0,0.78);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.07)}}
.brand{{display:flex;align-items:center;gap:9px;color:#fff}}
.brand-logo{{width:30px;height:30px;background:var(--accent);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.95rem}}
.brand-name{{font-family:'Cormorant Garamond',serif;font-size:1.25rem;font-weight:600;letter-spacing:-.02em}}
.badge{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:.7rem;font-weight:600;padding:5px 13px;border-radius:100px;letter-spacing:.08em;text-transform:uppercase}}
.btn-book{{background:var(--accent);color:#fff;border:none;padding:9px 20px;border-radius:100px;font-family:'Figtree',sans-serif;font-weight:600;font-size:.82rem;cursor:pointer;text-decoration:none;transition:all .2s;white-space:nowrap}}
.btn-book:hover{{filter:brightness(1.12);transform:translateY(-1px)}}

/* intro card */
.intro{{position:fixed;top:76px;left:50%;transform:translateX(-50%);z-index:998;background:rgba(255,255,255,.97);backdrop-filter:blur(20px);border-radius:20px;padding:32px 40px;max-width:580px;width:calc(100% - 48px);box-shadow:0 24px 60px rgba(0,0,0,.22);text-align:center;border-top:3px solid var(--accent);animation:slideDown .5s cubic-bezier(.34,1.56,.64,1)}}
@keyframes slideDown{{from{{opacity:0;transform:translateX(-50%) translateY(-18px)}}to{{opacity:1;transform:translateX(-50%) translateY(0)}}}}
.intro.gone{{display:none}}
.intro-kicker{{font-size:.68rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);margin-bottom:9px}}
.intro h2{{font-family:'Cormorant Garamond',serif;font-size:1.9rem;font-weight:700;color:var(--dark);line-height:1.2;margin-bottom:9px}}
.intro p{{color:#666;font-size:.89rem;line-height:1.6;margin-bottom:22px}}
.btn-dismiss{{background:var(--dark);color:#fff;border:none;padding:12px 24px;border-radius:100px;font-family:'Figtree',sans-serif;font-weight:600;font-size:.87rem;cursor:pointer;margin-right:8px;transition:opacity .2s}}
.btn-dismiss:hover{{opacity:.82}}
.btn-intro-cta{{background:var(--accent);color:#fff;border:none;padding:12px 24px;border-radius:100px;font-family:'Figtree',sans-serif;font-weight:600;font-size:.87rem;cursor:pointer;text-decoration:none;display:inline-block;transition:filter .2s}}
.btn-intro-cta:hover{{filter:brightness(1.1)}}

/* pain strip */
.pain-strip{{position:fixed;bottom:0;left:0;right:430px;z-index:997;padding:0 28px 28px;display:none;flex-direction:column;gap:10px}}
.pain-card{{background:rgba(255,255,255,.95);backdrop-filter:blur(14px);border-radius:13px;padding:13px 16px;display:flex;align-items:flex-start;gap:11px;box-shadow:0 4px 16px rgba(0,0,0,.14);border-left:3px solid var(--accent);animation:slideLeft .4s ease both}}
@keyframes slideLeft{{from{{opacity:0;transform:translateX(-16px)}}to{{opacity:1;transform:none}}}}
.pain-icon{{font-size:1.1rem;flex-shrink:0;margin-top:2px}}
.pain-text{{font-size:.8rem;color:#333;line-height:1.4}}
.pain-text strong{{display:block;font-size:.72rem;color:var(--accent);text-transform:uppercase;letter-spacing:.05em;margin-bottom:1px}}

/* voice widget */
.widget{{position:fixed;bottom:28px;right:28px;width:370px;z-index:999;background:rgba(255,255,255,.97);backdrop-filter:blur(24px);border-radius:var(--r);box-shadow:0 28px 70px rgba(0,0,0,.28),0 2px 0 var(--accent);overflow:hidden}}
.w-header{{background:var(--dark);padding:15px 18px;display:flex;align-items:center;justify-content:space-between;cursor:pointer}}
.w-header-l{{display:flex;align-items:center;gap:9px}}
.w-avatar{{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#ff6b35);display:flex;align-items:center;justify-content:center;font-size:.95rem;position:relative}}
.dot{{position:absolute;bottom:0;right:0;width:9px;height:9px;background:#22c55e;border:2px solid var(--dark);border-radius:50%}}
.w-title strong{{color:#fff;font-size:.88rem;display:block;line-height:1.2}}
.w-title small{{color:rgba(255,255,255,.55);font-size:.7rem}}
.w-toggle{{background:rgba(255,255,255,.1);border:none;color:#fff;width:26px;height:26px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.85rem;transition:background .2s}}
.w-toggle:hover{{background:rgba(255,255,255,.2)}}
.w-body{{padding:18px}}

/* transcript */
.transcript{{background:#f8f9fa;border-radius:11px;padding:13px;height:175px;overflow-y:auto;margin-bottom:14px;font-size:.83rem;line-height:1.5;scroll-behavior:smooth}}
.msg{{margin-bottom:9px;animation:msgIn .25s ease}}
@keyframes msgIn{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:none}}}}
.msg-agent .label{{color:var(--accent);font-weight:700;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase}}
.msg-user .label{{color:#888;font-weight:700;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase}}
.ph{{text-align:center;color:#bbb;padding:38px 0;font-size:.8rem}}

/* call btn */
.call-btn{{width:100%;padding:13px;border-radius:11px;border:none;font-family:'Figtree',sans-serif;font-weight:700;font-size:.88rem;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:7px}}
.start{{background:var(--accent);color:#fff}}
.start:hover{{filter:brightness(1.1);transform:translateY(-1px)}}
.end{{background:#fee2e2;color:#dc2626}}

/* status */
.status-row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}}
.status-pill{{font-size:.7rem;font-weight:600;padding:3px 9px;border-radius:100px;background:#f0fdf4;color:#16a34a}}
.status-pill.off{{background:#f3f4f6;color:#9ca3af}}

/* waves */
.waves{{display:flex;gap:2px;align-items:center;height:18px}}
.w{{width:3px;background:#fff;border-radius:2px;animation:wv 1s ease-in-out infinite}}
.w:nth-child(2){{animation-delay:.1s}}.w:nth-child(3){{animation-delay:.2s}}.w:nth-child(4){{animation-delay:.3s}}
@keyframes wv{{0%,100%{{height:4px}}50%{{height:14px}}}}

/* lang */
.lang-row{{display:flex;gap:5px;margin-top:11px;flex-wrap:wrap;align-items:center}}
.lang-row span{{font-size:.7rem;color:#aaa}}
.lang-btn{{padding:4px 11px;border:1.5px solid #e5e7eb;border-radius:100px;background:#fff;color:#555;font-size:.72rem;font-weight:600;cursor:pointer;transition:all .15s;font-family:'Figtree',sans-serif}}
.lang-btn.active{{border-color:var(--accent);background:var(--accent);color:#fff}}

@media(max-width:640px){{
  .widget{{width:calc(100% - 32px);right:16px;bottom:16px}}
  .pain-strip{{display:none!important}}
  .intro{{padding:22px 18px}}
}}
</style>
</head>
<body>

<div class="topbar">
  <div class="brand">
    <div class="brand-logo">🎋</div>
    <span class="brand-name">Bamboo AI</span>
  </div>
  <div class="badge">Live Demo · {co}</div>
  <a href="{CALENDLY_URL}?utm_source=demo&utm_campaign={slug}" class="btn-book" target="_blank">📅 Book Setup Call</a>
</div>

<div class="stage">
  <div class="overlay"></div>

  <!-- INTRO CARD -->
  <div class="intro" id="intro">
    <div class="intro-kicker">🎋 Bamboo AI · Personalised Demo</div>
    <h2>This is {co}'s website.<br>With your AI agent on top.</h2>
    <p>We built a voice agent specifically for <strong>{co}</strong> — it knows your {proj_str} projects, responds in {lang}, and handles enquiries 24/7. Try talking to it below.</p>
    <button class="btn-dismiss" onclick="dismissIntro()">👀 See the Demo</button>
    <a href="{CALENDLY_URL}?utm_source=intro&utm_campaign={slug}" class="btn-intro-cta" target="_blank">📅 Add to My Site</a>
  </div>

  <!-- PAIN CARDS (left) -->
  <div class="pain-strip" id="painStrip">
    {pain_cards_html}
  </div>
</div>

<!-- VOICE WIDGET -->
<div class="widget" id="widget">
  <div class="w-header" onclick="toggleWidget()">
    <div class="w-header-l">
      <div class="w-avatar">🏠<div class="dot"></div></div>
      <div class="w-title">
        <strong>{co} AI Agent</strong>
        <small>Bamboo AI · {lang}</small>
      </div>
    </div>
    <button class="w-toggle" id="toggleBtn">−</button>
  </div>
  <div class="w-body" id="wBody">
    <div class="status-row">
      <span style="font-size:.76rem;color:#888">Ask about a property</span>
      <span class="status-pill off" id="statusPill">Ready</span>
    </div>
    <div class="transcript" id="transcript">
      <div class="ph" id="ph">🎙️ Press the button below to begin</div>
    </div>
    <button class="call-btn start" id="callBtn" onclick="toggleCall()">
      📞 Start Voice Demo
      <div class="waves" id="waves" style="display:none">
        <div class="w"></div><div class="w"></div><div class="w"></div><div class="w"></div>
      </div>
    </button>
    <div class="lang-row">
      <span>Language:</span>
      {lang_btns_html}
    </div>
  </div>
</div>

<script>
const PROMPT   = {prompt_js};
const CO       = "{co}";
const PROJECTS = {projects_js};
const PRICE    = "{price}";
const BACKEND  = "{BACKEND_URL}";
const SARVAM   = "{SARVAM_API_KEY}";
const SLUG     = "{slug}";

let lang   = "{sarvam_lang}";
let active = false;
let rec    = null;
let chunks = [];
let hist   = [];
let wOpen  = true;

function dismissIntro() {{
  document.getElementById('intro').classList.add('gone');
  document.getElementById('painStrip').style.display = 'flex';
}}

function toggleWidget() {{
  wOpen = !wOpen;
  document.getElementById('wBody').style.display = wOpen ? 'block' : 'none';
  document.getElementById('toggleBtn').textContent = wOpen ? '−' : '+';
}}

function setLang(code, el) {{
  lang = code;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}}

async function toggleCall() {{
  if (!active) await startCall(); else endCall();
}}

async function startCall() {{
  active = true; hist = [];
  document.getElementById('transcript').innerHTML = '';
  setStatus('Connected', true);
  setBtnEnd();
  const greet = `Namaste! Welcome to ${{CO}}. I'm your AI property advisor, available 24/7. Are you looking for a home or an investment property?`;
  addMsg('agent', greet);
  await speak(greet);
  if (active) await listenLoop();
}}

function endCall() {{
  active = false;
  if (rec?.state === 'recording') rec.stop();
  setStatus('Ready', false);
  setBtnStart();
  addMsg('agent', `Thank you for experiencing the Bamboo AI demo for ${{CO}}! 🎋 Tap "Book Setup Call" to get this live on your site.`);
}}

async function listenLoop() {{
  if (!active) return;
  setStatus('Listening…', true);
  try {{
    const stream = await navigator.mediaDevices.getUserMedia({{audio:true}});
    const mime = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'].find(t=>MediaRecorder.isTypeSupported(t))||'audio/webm';
    rec = new MediaRecorder(stream, {{mimeType:mime}});
    chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = async () => {{
      stream.getTracks().forEach(t=>t.stop());
      const blob = new Blob(chunks, {{type:mime}});
      if (blob.size > 1000) await processAudio(blob);
      if (active) await listenLoop();
    }};
    rec.start();
    setTimeout(()=>{{ if(rec.state==='recording') rec.stop(); }}, 5000);
  }} catch(e) {{
    console.log('No mic, simulating…');
    await simulateChatScript();
  }}
}}

async function processAudio(blob) {{
  setStatus('Transcribing…', true);
  let text = '';
  if (SARVAM) {{
    try {{
      const fd = new FormData();
      fd.append('file', blob, 'audio.webm');
      fd.append('language_code', lang);
      const r = await fetch(`${{BACKEND}}/api/stt`, {{method:'POST',body:fd}});
      const d = await r.json();
      text = d.transcript || '';
    }} catch(e) {{ text = ''; }}
  }}
  if (text.trim()) {{ addMsg('user', text); await getReply(text); }}
}}

async function getReply(userText) {{
  setStatus('Thinking…', true);
  hist.push({{role:'user',content:userText}});
  try {{
    const r = await fetch(`${{BACKEND}}/api/chat`, {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{system_prompt:PROMPT,messages:hist,demo_slug:SLUG,company:CO}})
    }});
    const d = await r.json();
    const reply = d.reply || 'Could you repeat that?';
    hist.push({{role:'assistant',content:reply}});
    addMsg('agent', reply);
    await speak(reply);
  }} catch(e) {{
    const fb = `Thank you for your interest in ${{CO}}! Our properties: ${{PRICE||'₹50L–₹2Cr'}}. Want to schedule a site visit?`;
    addMsg('agent', fb); await speak(fb);
  }}
}}

async function speak(text) {{
  setStatus('Speaking…', true);
  if (SARVAM) {{
    try {{
      const r = await fetch(`${{BACKEND}}/api/tts`, {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{text, language_code:lang, speaker:'meera'}})
      }});
      const d = await r.json();
      if (d.audios?.[0]) {{
        const audio = new Audio('data:audio/wav;base64,'+d.audios[0]);
        await new Promise(res => {{ audio.onended=res; audio.play(); }});
        setStatus(active?'Listening…':'Ready', active); return;
      }}
    }} catch(e) {{}}
  }}
  await new Promise(res => {{
    const u = new SpeechSynthesisUtterance(text);
    u.lang=lang; u.rate=0.92; u.onend=res; speechSynthesis.speak(u);
  }});
  setStatus(active?'Listening…':'Ready', active);
}}

async function simulateChatScript() {{
  const lines = [
    {{u:`Hi, I'm looking for a 3BHK apartment`,a:`Great choice! We have beautiful 3BHK options starting from ${{PRICE||'₹70 lakhs'}}. Are you looking for immediate possession or under-construction?`}},
    {{u:`What is the price range?`,a:`Our 3BHK units range from ${{PRICE||'₹70L to ₹1.5Cr'}} depending on the floor and view. We also have flexible payment plans. Would you like a site visit this weekend?`}},
    {{u:`Yes, Saturday works`,a:`Perfect! I'll book a Saturday slot. Can I get your name and mobile number so our team can confirm?`}},
  ];
  for (const line of lines) {{
    if (!active) break;
    await delay(1500); addMsg('user', line.u);
    await delay(700);  addMsg('agent', line.a); await speak(line.a);
  }}
}}

function addMsg(role, text) {{
  const box = document.getElementById('transcript');
  const ph  = document.getElementById('ph');
  if (ph) ph.remove();
  const d = document.createElement('div');
  d.className = `msg msg-${{role}}`;
  d.innerHTML = `<div class="label">${{role==='agent'?'🎋 '+CO+' AI':'👤 You'}}</div><div class="text">${{text}}</div>`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}}

function setStatus(text, on) {{
  const p = document.getElementById('statusPill');
  p.textContent = text;
  p.className = 'status-pill' + (on?'':' off');
}}

function setBtnEnd() {{
  const b = document.getElementById('callBtn');
  b.className='call-btn end';
  b.innerHTML='⏹ End Call <div class="waves" style="display:flex"><div class="w"></div><div class="w"></div><div class="w"></div><div class="w"></div></div>';
}}
function setBtnStart() {{
  const b = document.getElementById('callBtn');
  b.className='call-btn start';
  b.innerHTML='📞 Start Voice Demo';
}}

function delay(ms) {{ return new Promise(r=>setTimeout(r,ms)); }}

// Track demo open (best-effort)
try {{
  fetch(`${{BACKEND}}/api/track`,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{slug:SLUG,event:'demo_opened',company:CO}})}}).catch(()=>{{}});
}} catch(e){{}}
</script>
</body>
</html>"""
