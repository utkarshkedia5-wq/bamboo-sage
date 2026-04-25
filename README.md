# 🎋 SAGE — Voice Agent Demo Pipeline (Bamboo AI)

> Research 20 builders → screenshot their site → overlay Bamboo AI voice widget
> → Claude writes personalised email → send. 100% Python. No n8n.

---

## End-to-end flow

```
leads.csv (20 builders)
    │
    ▼  ResearchAgent
    │  scrapes website → Claude extracts JSON (projects, price, pain points, language)
    │
    ▼  DemoBuilderAgent  ← THE MAGIC
    │  gets a live screenshot of their website via thum.io (free, no key needed)
    │  wraps it as a full-page background image
    │  places the Bamboo AI voice widget on top
    │  → output/demo_<slug>.html
    │
    ▼  EmailAgent
    │  Claude writes a hyper-personalised email (mentions their actual projects)
    │  sends via Gmail SMTP with the demo URL as a big button
    │
    ▼  Client opens email → clicks link
    │  sees THEIR OWN WEBSITE with Bamboo AI widget floating on top
    │  clicks "Start Voice Demo" → talks to an agent that knows their projects
    │  clicks "Book Setup Call" → Calendly → you close the deal
```

---

## File structure

```
bamboo-sage/
├── agents/
│   ├── researcher.py      # Scrapes site → Claude extracts structured JSON
│   ├── demo_builder.py    # Screenshot approach → full HTML demo page
│   └── emailer.py         # Claude writes email → Gmail SMTP
├── leads/
│   └── leads.csv          # Your targeted leads
├── output/                # Generated demo HTML files (deploy to Vercel)
├── main.py                # Run this — orchestrates the full pipeline
├── server.py              # FastAPI: Claude proxy + Sarvam proxy + analytics
├── .env.example           # Copy to .env and fill keys
└── requirements.txt
```

---

## Tech stack

| Layer | Tool | Reason |
|---|---|---|
| Research | Claude Sonnet + httpx + BeautifulSoup | Scrape + structured extraction |
| Screenshot | thum.io (free) / screenshotone.com ($) | Show their own site as backdrop |
| Voice STT | Sarvam AI | Best Hindi/Telugu/regional accuracy in India |
| Voice LLM | Claude Sonnet (via your backend proxy) | Smart property advisor |
| Voice TTS | Sarvam AI — Meera voice | Natural Indian accent |
| Email copy | Claude Sonnet | Personalised, not spammy |
| Email send | Gmail SMTP + App Password | Simple, free, reliable |
| Backend | FastAPI on Render/Railway (free tier) | Proxy keys, track events |
| Demo hosting | Vercel (free) | Static HTML, instant CDN |

---

## Setup

### 1. Install

```bash
cd bamboo-sage
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Keys you need

**Anthropic (Claude)** — console.anthropic.com → API Keys → Create Key

**Sarvam AI** (regional voice) — sarvam.ai → Dashboard → API Keys
Free tier is enough to start.

**Gmail App Password** (NOT your regular Gmail password)
Gmail → profile pic → Manage Google Account → Security → App Passwords
Create one called "SAGE" → copy the 16-char password.

**Screenshot API** (optional, better quality)
screenshotone.com → 100 free/month. Leave blank to use thum.io (zero setup).

### 3. Configure

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, SARVAM_API_KEY, SMTP_USER, SMTP_PASS
```

### 4. Add leads

Edit `leads/leads.csv` — the sample has 10 real Indian builders already.
Format: `company_name,website,contact_name,contact_email,city,phone`

### 5. Dry run (no emails)

```bash
python main.py --dry-run
```

Open any `output/demo_*.html` in Chrome to see the demo.

### 6. Deploy backend (needed for voice to work)

The demo page calls your backend for Claude + Sarvam proxying and analytics.

**Render.com (free):**
- New Web Service → connect GitHub repo
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Set all .env variables in the Render dashboard

Update `BACKEND_URL` in .env to your Render URL.

### 7. Host demo files

```bash
# After dry run generates output/ files:
npm i -g vercel
vercel output/
# Update DEMO_BASE_URL in .env to the Vercel URL
```

### 8. Run for real

```bash
python main.py
```

---

## What the client sees

```
┌───────────────────────────────────────────────────────────────┐
│ 🎋 Bamboo AI     [Live Demo · Rajpushpa Properties]  [📅 Book]│  top bar
│                                                               │
│   ╔═══════════════════════════════════════════╗               │
│   ║ 🎋 Bamboo AI · Personalised Demo          ║               │
│   ║                                           ║               │
│   ║  This is Rajpushpa Properties' website.  ║               │
│   ║  With your AI agent on top.              ║               │
│   ║                                           ║               │
│   ║   [👀 See Demo]    [📅 Add to My Site]    ║               │
│   ╚═══════════════════════════════════════════╝               │
│                                                               │
│       [Their actual website screenshot as background]         │
│                                                               │
│  ⚡ Losing leads after hours   ╔══════════════════════════╗   │
│  📞 Team overwhelmed at launch ║ 🏠 Rajpushpa AI Agent   ║   │
│  📊 Slow follow-up             ║ Bamboo AI · Hindi        ║   │
│                                ║ ────────────────────     ║   │
│                                ║ [transcript here]        ║   │
│                                ║                          ║   │
│                                ║ [📞 Start Voice Demo]    ║   │
│                                ║  EN  हिं  తె  म           ║   │
│                                ╚══════════════════════════╝   │
└───────────────────────────────────────────────────────────────┘
```

They see their own site. They click Start. They talk to an agent that knows
their projects, responds in Hindi/Telugu, and offers to book a site visit.

---

## Voice pipeline (technical)

```
User speaks → 5s audio chunk
    ↓
POST /api/stt → Sarvam AI Speech-to-Text → transcript
    ↓
POST /api/chat → Claude Sonnet (company system prompt + history) → reply text
    ↓
POST /api/tts → Sarvam AI TTS (Meera voice) → base64 audio → plays in browser
    ↓
Loop (next chunk)
```

If mic is unavailable, auto-falls back to a scripted simulation.

---

## Regional languages supported (Sarvam AI)

Hindi (hi-IN) · Telugu (te-IN) · Tamil (ta-IN) · Kannada (kn-IN) · Marathi (mr-IN) · English (en-IN)

The widget auto-sets the right language based on the builder's city.
The prospect can switch language live during the call.

---

## Analytics

Visit `https://your-backend.com/dashboard` to see:
- Which demos were opened
- Which had a call started
- Which booked on Calendly (via webhook)

---

## Cost for 20 leads

| Item | Cost |
|---|---|
| Claude API (research + email per lead) | ~$0.05 × 20 = $1 |
| Sarvam AI (covered by free tier in dev) | ₹0 |
| Screenshots (thum.io free) | $0 |
| Render backend (free tier) | $0 |
| Vercel hosting (free tier) | $0 |
| **Total** | **~$1–2** |
