# 🚆 Conversational IVR Modernization Framework
### IRCTC Smart IVR System — Infosys Springboard Internship Project

---

## 🌐 Live Demo

**[https://irctc-smart-ivr.onrender.com](https://irctc-smart-ivr.onrender.com)**

> Login → `admin` / `irctc123`
> ⚠️ First load may take 30–60 seconds (Render free tier wakes up from sleep)

---

## 📌 Project Overview

This project modernizes a legacy **VXML-based IVR (Interactive Voice Response)** system by building a full **Conversational AI Integration Layer** using Python and FastAPI.

Traditional IVR systems force users to press keys on a phone. This project upgrades that experience so users can **speak or type naturally** — *"Check my PNR 4521679834"* — and the system understands, extracts data, and responds intelligently.

No Twilio. No paid APIs. Runs completely free using a browser-based web simulator.

---

## 🗂️ Project Structure

```


📁 Milestone-3/                        ← Complete working project
│   ├── static/
│   │   ├── style.css
│   │   ├── script.js
│   │   └── assets/
│   ├── templates/
│   │   ├── login.html
│   │   └── dashboard.html
│   ├── main.py
│   ├── nlu_engine.py
│   ├── dialog_manager.py
│   ├── speech_services.py
│   ├── test.py
│   ├── requirements.txt
│   ├── render.yaml
│   └── .python-version
│
└── README.md
```

---

## 🗺️ Milestone Roadmap

---

### ✅ Milestone 1 — System Analysis and Requirements Gathering
**Weeks 1–2**

Conducted research and documentation on:

- What is IVR (Interactive Voice Response) and how it works
- Architecture of VXML-based legacy IVR systems
- Limitations of traditional IVR — no natural language, rigid menus, poor UX
- How Conversational AI (ACS/BAP) can modernize legacy IVR
- Integration strategy and technical requirements

📄 **Deliverable:** `Milestone-1/IVR_Research_Analysis.pdf`

---

### ✅ Milestone 2 — Integration Layer Development
**Weeks 3–4**

Built the middleware/API layer connecting legacy IVR logic to a modern web simulator.

**What was built:**
- FastAPI application with full configuration and CORS middleware
- 9 REST API endpoints for all IRCTC IVR services
- DTMF key press routing — press 1–6 exactly like a real phone call
- Session management with unique UUIDs per call
- Browser-based IVR phone simulator UI with dialpad
- English-only welcome prompt with full menu spoken on call start

**Tech used:** Python, FastAPI, Uvicorn, Pydantic, HTML/CSS/JS

---

### ✅ Milestone 3 — Conversational AI Interface Development
**Weeks 5–6**

Added full natural language capabilities on top of the M2 integration layer.

**What was built:**

| Feature | Details |
|---|---|
| 🧠 NLU Intent Recognition | 9 intents — pnr_status, book_ticket, search_trains, cancel_ticket, complaint, train_status, talk_to_agent, greeting, goodbye |
| 📦 Entity Extraction | 7 regex patterns — PNR, train number, date, stations, travel class, passenger count |
| 🔊 Text-to-Speech (TTS) | Browser Web Speech API — speaks every IVR response in Indian English |
| 🎤 Speech-to-Text (STT) | Browser SpeechRecognition — mic input transcribed and sent to NLU |
| ⌨️ DTMF Keypad | Classic key press 1–6 fully working alongside chat |
| 💬 Chat Interface | Conversational chat with live intent + entity + confidence display |
| 🔐 Login Page | Credential-based login with session |
| 🗣️ Dialogue Manager | Maps intent + entities → auto-calls correct M2 endpoint |
| 🚂 Train Selection Flow | After search, user types train number → system auto-books |

**Modules:**

| File | Purpose |
|---|---|
| `main.py` | FastAPI app, all endpoints, session store |
| `nlu_engine.py` | Intent classifier + entity extractor |
| `dialog_manager.py` | Dialogue manager — intent to action routing |
| `speech_services.py` | TTS and STT configuration helpers |
| `static/` | CSS styling and JavaScript logic |
| `templates/` | Login and dashboard HTML pages |

---

### ✅ Milestone 4 — Testing and Deployment
**Weeks 7–8**

**Testing — `test.py`:**

| Type | Tests | What It Checks |
|---|---|---|
| Unit | 2 | `classify_intent()` and `extract_entities()` in isolation |
| Integration | 2 | NLU output correctly feeds into M2 endpoints |
| End to End | 2 | Full user journey from start call to end call |
| Performance | 2 | All endpoints respond under 300ms |

**Deployment:**
- Hosted live on **Render.com** (free tier)
- Python 3.11, Uvicorn ASGI server
- Automatic redeploy on every GitHub push
- Live URL: [https://irctc-smart-ivr.onrender.com](https://irctc-smart-ivr.onrender.com)

---

## ⚙️ Run Locally

```bash
# 1 — Install
pip install -r requirements.txt

# 2 — Run
python main.py

# 3 — Open Chrome → http://localhost:8000
# Login: admin / irctc123
```

> Chrome or Edge recommended — required for microphone (STT) feature.

---

## 🧪 How to Test the Project

### Step 1 — Start a Call
Click **▶ START CALL** on the left panel. Welcome message appears and is spoken aloud.

---

### Step 2 — DTMF Keypad
Press keys on the dialpad after starting a call:

| Key | Response |
|---|---|
| `1` | You selected PNR Status |
| `2` | You selected Ticket Booking |
| `3` | You selected Train Search |
| `4` | You selected Cancellation |
| `5` | You selected Register Complaint |
| `6` | Connecting to support agent |
| `0` | Repeats the main menu |

---

### Step 3 — Chat (Type These Exactly)

**Check PNR Status:**
```
Check my PNR 4521679834
```

**Book a Ticket:**
```
Book train 12951 from NDLS to MMCT on 15 June in third AC
```

**Search Trains:**
```
Search trains from NDLS to MMCT
```
After seeing the 3 results, type just the train number to book:
```
12951
```

**Cancel a Ticket:**
```
Cancel my ticket PNR 4521679834
```

**Register a Complaint:**
```
The coach is dirty register a complaint
```

**Talk to Agent:**
```
Talk to agent
```

---

### Test Data Reference

| Field | Value |
|---|---|
| PNR Number | `4521679834` |
| Train Number | `12951` — Mumbai Rajdhani Express |
| From Station | `NDLS` — New Delhi |
| To Station | `MMCT` — Mumbai Central |
| Journey Date | `15 June` |
| Travel Class | `Third AC` or `Sleeper` |
| Login Username | `admin` |
| Login Password | `irctc123` |

---

### Run the Test Suite

```bash
pip install httpx==0.23.3
python test.py
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Backend language |
| FastAPI | Web framework — all API endpoints |
| Uvicorn | ASGI server |
| Jinja2 | HTML template rendering |
| Pydantic | Request and response validation |
| `re` stdlib | Regex entity extraction — zero external AI |
| Web Speech API | Browser TTS and STT |
| HTML5 / CSS3 / JS | Frontend simulator |
| Render.com | Free cloud deployment |

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/call/start` | Start call — English welcome prompt |
| `POST` | `/call/menu` | Main menu keys 1–6 |
| `POST` | `/call/key` | DTMF key press handler |
| `POST` | `/call/pnr` | PNR status check |
| `POST` | `/call/booking` | Ticket booking |
| `POST` | `/call/trains` | Train search |
| `POST` | `/call/cancel` | Cancellation and refund |
| `POST` | `/call/complaint` | Register complaint |
| `POST` | `/call/end` | End call |
| `POST` | `/nlu/understand` | Full NLU pipeline |
| `POST` | `/nlu/debug-intent` | Test NLU on any sentence |
| `GET` | `/health` | Health check |



---





*Built with Python + FastAPI + Web Speech API · Infosys Springboard Internship*
