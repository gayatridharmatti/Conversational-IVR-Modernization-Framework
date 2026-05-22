# 🚆 IRCTC Smart IVR — Conversational IVR Modernization Framework

> **Milestone 2 — Integration Layer Development**
> Infosys Springboard Internship Project

---

## 📌 Project Overview

This project is part of the **Conversational IVR Modernization Framework** built during the Infosys Springboard internship. The goal is to modernize a legacy VXML-based IVR (Interactive Voice Response) system by building a modern middleware/API integration layer using **Python** and **FastAPI**.

Instead of using paid phone infrastructure, this project uses a completely **free Web Simulator approach** — the entire IVR experience runs in a browser, with a phone-style UI that communicates with the FastAPI backend in real time.

---

## 🎯 Milestone 2 Objective

> *Build a middleware/API layer to connect legacy IVRs to the Conversational AI stack.*

| Requirement | Status |
|---|---|
| Design and implement API connectors for VXML ↔ ACS/BAP communication | ✅ Done |
| Ensure real-time data handling and system compatibility | ✅ Done |
| Validate integration layer with sample transaction and flow testing | ✅ Done |
| FastAPI configuration at the start of the project | ✅ Done |
| Welcome prompt in English only | ✅ Done |
| IVR Main Menu with keys 1–6 | ✅ Done |
| Key/DTMF press handler with output message | ✅ Done |
| Live JSON response visible in the UI | ✅ Done |

---

## 🗂️ Project Structure

```
IRCTC-SMART-IVR/
│
├── irctc_backend.py     ← FastAPI server — all business logic + 12 endpoints
├── irctc_ui.html        ← Browser-based IVR phone simulator (HTML/CSS/JS)
└── README.md            ← This file
```

> Both files must be in the **same folder**. The backend serves the HTML file directly at `http://localhost:8000`.

---

## 🛠️ Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Core programming language |
| FastAPI | 0.110+ | Web framework — creates all API endpoints |
| Uvicorn | 0.29+ | ASGI server — runs the FastAPI application |
| Pydantic | 2.x | Request/response data validation |
| HTML5 / CSS3 | — | Browser-based IVR phone simulator UI |
| Vanilla JavaScript | ES2020+ | Frontend API calls, dialpad interaction, JSON display |
| UUID (stdlib) | — | Unique session IDs and booking references |
| Datetime (stdlib) | — | Timestamps and IST greeting calculation |

> **No paid services. No Twilio. No external APIs. Runs 100% locally for free.**

---

## ⚙️ FastAPI Configuration

The app is configured at the very top of `irctc_backend.py` (Section 2):

```python
app = FastAPI(
    title       = "My IRCTC Smart IVR — Integration Layer",
    description = "Module 2: Middleware API layer connecting legacy VXML IVR to the Conversational AI stack (ACS/BAP).",
    version     = "1.0.0",
    contact     = {"name": "Infosys Springboard Intern", "email": "intern@infosys.com"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)
```

FastAPI's **interactive API docs** are automatically available at:
- Swagger UI → `http://localhost:8000/docs`
- ReDoc → `http://localhost:8000/redoc`

---

## 🔌 API Endpoints

All endpoints follow a **consistent JSON response shape**:

```json
{
  "status":    "success | error | invalid | transfer",
  "timestamp": "2025-06-01T10:30:00.000000",
  "prompt":    "The voice text that would be spoken to the caller",
  "acs_event": "ivr_pnr_flow",
  "data":      { }
}
```

> The `prompt` field = what a real TTS engine would read aloud.
> The `acs_event` field = hook for ACS/BAP bot triggers in Milestone 3.

---

### `GET /`
Serves the **Web Simulator HTML page** to the browser. No parameters needed.

---

### `POST /call/start` — Welcome Prompt *(English Only)*

Creates a new IVR session and returns the English welcome message with a time-based greeting (Good Morning / Good Afternoon / Good Evening).

**Request Body:**
```json
{
  "caller_id": "+919876543210",
  "language": "EN"
}
```

**Sample Response:**
```json
{
  "status": "success",
  "prompt": "Good Morning. Welcome to IRCTC Smart IVR. Your trusted railway assistance system. This call is in English.",
  "acs_event": "welcome_delivered",
  "data": {
    "session_id": "a1b2c3d4-...",
    "language": "English",
    "next_step": "Call /call/menu to hear the main menu"
  }
}
```

---

### `POST /call/menu` — IVR Main Menu *(Keys 1–6)*

Returns the full main menu prompt. The UI calls this automatically after `/call/start`.

**Request Body:**
```json
{ "session_id": "your-session-id" }
```

**Menu Options:**

| Key | Service |
|---|---|
| **1** | PNR Status |
| **2** | Ticket Booking |
| **3** | Train Search |
| **4** | Cancellation & Refund |
| **5** | Register Complaint |
| **6** | Talk to Agent |
| **0** | Repeat Menu |

---

### `POST /call/key` — Key Press / DTMF Handler

The core routing engine. Accepts any key press and returns the appropriate response based on the **current flow state**.

**Request Body:**
```json
{
  "session_id":   "your-session-id",
  "key_pressed":  "1",
  "current_flow": "main_menu"
}
```

**How routing works:**

```
current_flow = "main_menu"
    key "1"  →  prompt: "You selected PNR Status..."   acs_event: ivr_pnr_flow
    key "2"  →  prompt: "You selected Ticket Booking..." acs_event: ivr_booking_flow
    key "3"  →  prompt: "You selected Train Search..."   acs_event: ivr_search_flow
    key "4"  →  prompt: "You selected Cancellation..."   acs_event: ivr_cancel_flow
    key "5"  →  prompt: "You selected Complaint..."      acs_event: ivr_complaint_flow
    key "6"  →  prompt: "Connecting to agent..."         status: transfer
    key "0"  →  repeats the main menu
    invalid  →  prompt: "Sorry, X is not valid..."       status: invalid

current_flow = "class_select"
    key "1"–"5"  →  stores class in session, confirms selection

current_flow = "complaint_type"
    key "1"–"3"  →  stores complaint category, prompts for details
```

---

### `POST /call/pnr` — PNR Status Check

Validates a 10-digit PNR and returns booking details.

**Request Body:**
```json
{
  "session_id": "your-session-id",
  "pnr_number": "4521679834"
}
```

**Validation:** PNR must be exactly 10 digits. Returns `status: invalid` otherwise.

**Sample Response `data`:**
```json
{
  "pnr_number":    "4521679834",
  "train_number":  "12951",
  "train_name":    "Mumbai Rajdhani Express",
  "from_station":  "New Delhi (NDLS)",
  "to_station":    "Mumbai Central (MMCT)",
  "journey_date":  "15-Jun-2025",
  "travel_class":  "Third AC (3A)",
  "booking_status":"CONFIRMED",
  "coach":         "B-4",
  "seat_number":   "32 — Lower Berth",
  "platform":      "Platform 2",
  "departure":     "16:55",
  "arrival":       "08:35 (+1 day)"
}
```

---

### `POST /call/booking` — Ticket Booking

Creates a ticket booking and generates a unique Booking ID.

**Request Body:**
```json
{
  "session_id":      "your-session-id",
  "train_number":    "12951",
  "journey_date":    "15062025",
  "from_station":    "NDLS",
  "to_station":      "MMCT",
  "travel_class":    "2",
  "passenger_count": 1
}
```

**Travel Class Codes:**

| Code | Class | Base Fare |
|---|---|---|
| 1 | Sleeper (SL) | ₹450 |
| 2 | Third AC (3A) | ₹1,150 |
| 3 | Second AC (2A) | ₹1,800 |
| 4 | First AC (1A) | ₹3,100 |
| 5 | Chair Car (CC) | ₹650 |

**Sample Response `data`:**
```json
{
  "booking_id":   "IVRA3F2C91B",
  "status":       "PENDING PAYMENT",
  "total_fare":   "Rs. 1150",
  "payment_link": "https://irctc.co.in/payment/IVRA3F2C91B",
  "expires_in":   "15 minutes"
}
```

---

### `POST /call/trains` — Train Search

Searches for available trains between two stations.

**Request Body:**
```json
{
  "session_id":   "your-session-id",
  "from_station": "NDLS",
  "to_station":   "MMCT"
}
```

Returns a list of 3 trains with number, name, departure, arrival, duration, and available classes.

---

### `POST /call/cancel` — Cancellation & Refund

Cancels a ticket by PNR and returns refund details.

**Request Body:**
```json
{
  "session_id": "your-session-id",
  "pnr_number": "4521679834"
}
```

**Sample Response `data`:**
```json
{
  "cancellation_status": "CANCELLED",
  "refund_amount":       "Rs. 985",
  "refund_id":           "REFA1B2C3",
  "processing_time":     "5 to 7 working days"
}
```

---

### `POST /call/complaint` — Register Complaint

Registers a passenger complaint and generates a Rail Madad ticket number.

**Request Body:**
```json
{
  "session_id":        "your-session-id",
  "complaint_type":    "1",
  "complaint_details": "Train was running 2 hours late"
}
```

**Complaint Types:** `1` = Train Service, `2` = Catering, `3` = Cleanliness

---

### `POST /call/end` — End Call

Ends the session gracefully and returns a summary.

**Request Body:**
```json
{ "session_id": "your-session-id" }
```

---

### `POST /acs/bridge` — ACS/BAP Connector *(Milestone 3 Stub)*

Maps VXML events to ACS directives. This is the integration hook for Milestone 3.

| VXML Event | ACS Directive |
|---|---|
| `filled` | `USER_INPUT_RECEIVED` |
| `noinput` | `REQUEST_REPROMPT` |
| `nomatch` | `REQUEST_CLARIFICATION` |
| `disconnect` | `END_SESSION` |

> **Milestone 3 TODO:** Replace stub body with `CallAutomationClient` from Azure ACS SDK.

---

### `GET /session/{session_id}` — Session Inspector

Returns the complete session state including booking data, current flow, and full event log. Useful for debugging.

---

### `GET /health` — Health Check *(Milestone 4 Ready)*

Returns server status and active session count.

```json
{
  "status":          "healthy",
  "app_name":        "My IRCTC Smart IVR",
  "version":         "1.0.0",
  "milestone":       "M2 — Integration Layer",
  "active_sessions": 2
}
```

---

## 🖥️ Web Simulator UI

The `irctc_ui.html` file is a complete single-page browser application — no React, no npm, no build step required. It is served directly by the backend.

**Layout — 3 Panels:**

```
┌──────────────────┬──────────────────────────────┬─────────────────┐
│  IVR SIMULATOR   │      IRCTC SERVICES           │  CALL LOG       │
│                  │                               │                 │
│  📱 Call Screen  │  [PNR] [Booking] [Search]     │  10:30 AM       │
│                  │  [Cancel] [Complaint] [Menu]  │  CALL STARTED   │
│  ┌─────────────┐ │                               │                 │
│  │ Session ID  │ │  🔊 IVR Voice Prompt          │  10:30 AM       │
│  └─────────────┘ │  "Good Morning. Welcome to..."│  KEY [1]        │
│                  │                               │                 │
│  [1][2][3]       │  ┌──────────────────────────┐ │  10:30 AM       │
│  [4][5][6]       │  │  { JSON Response }        │ │  PNR CHECKED   │
│  [7][8][9]       │  │  "status": "success"      │ │                 │
│  [*][0][#]       │  │  "prompt": "PNR 452..."   │ │                 │
│                  │  └──────────────────────────┘ │                 │
│  [END CALL]      │                               │                 │
└──────────────────┴──────────────────────────────┴─────────────────┘
```

**Key JavaScript Functions:**

| Function | What It Does |
|---|---|
| `startCall()` | Calls `/call/start` then `/call/menu` automatically, enables dialpad |
| `pressKey(digit)` | Calls `/call/key` with the pressed digit and current flow state |
| `quickAction(type)` | Directly calls a service endpoint (pnr / booking / trains / cancel / complaint) |
| `endCall()` | Calls `/call/end`, resets UI and clears session |
| `showJSON(data)` | Renders syntax-highlighted JSON in the response panel |
| `setScreen(text)` | Animates text onto the phone screen character by character |
| `addLog(type, label, msg)` | Appends a timestamped entry to the call activity log |

---

## 🚀 How to Run

### Prerequisites
- Python 3.10 or higher
- PyCharm (or any terminal)

### Step 1 — Install dependencies

```bash
pip install fastapi uvicorn
```

### Step 2 — Run the server

```bash
python irctc_backend.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 3 — Open the simulator

Open your browser and go to:
```
http://localhost:8000
```

### Step 4 — Test the IVR

1. Click **▶ START CALL** — welcome prompt appears on the phone screen
2. Press **1** on the dialpad — "You selected PNR Status..."
3. Click the **PNR Status** service card — JSON response appears with booking details
4. Press **2** → click **Ticket Booking** card → booking ID and fare shown
5. Press **3** → click **Train Search** card → list of trains shown
6. Press **4** → click **Cancellation** card → refund details shown
7. Press **5** → click **Complaint** card → complaint ticket number shown
8. Click **✕ END CALL** — goodbye message, session summary shown

### Stop the server

```
CTRL + C
```

---

## 🔐 Session Management

Every call creates a unique session stored in a Python dictionary (`SESSIONS`). The session tracks:

```python
session = {
    "session_id":              "uuid4 string",
    "caller_id":               "+919876543210",
    "language":                "EN",
    "acs_call_connection_id":  None,        # Used in Milestone 3
    "current_flow":            "main_menu",
    "booking_data":            {},          # Accumulates multi-step inputs
    "call_started_at":         "ISO timestamp",
    "call_ended_at":           None,
    "event_log":               []           # Full trail of events
}
```

> **Milestone 4 upgrade:** Replace the in-memory `SESSIONS` dict with Redis:
> ```python
> import redis
> store = redis.Redis(host="localhost", port=6379)
> ```

---

## 🔭 System Architecture

```
┌─────────────────────────────────────┐
│      Web Browser (irctc_ui.html)    │
│   Phone UI + Dialpad + JSON Viewer  │
└──────────────┬──────────────────────┘
               │  HTTP (fetch API)
               ▼
┌─────────────────────────────────────┐
│    FastAPI Integration Layer        │
│       (irctc_backend.py)            │
│                                     │
│  GET  /              → Serves UI   │
│  POST /call/start    → Welcome     │
│  POST /call/menu     → Menu 1–6    │
│  POST /call/key      → DTMF route  │
│  POST /call/pnr      → PNR check   │
│  POST /call/booking  → Book ticket │
│  POST /call/trains   → Search      │
│  POST /call/cancel   → Cancel      │
│  POST /call/complaint→ Complaint   │
│  POST /call/end      → End session │
│  POST /acs/bridge    → M3 stub     │
│  GET  /health        → M4 monitor  │
└──────────────┬──────────────────────┘
               │  (Milestone 3)
               ▼
┌─────────────────────────────────────┐
│  ACS / BAP Conversational AI Stack  │
│  (Azure Communication Services)     │
│  CallAutomationClient — M3 TODO     │
└─────────────────────────────────────┘
               │  (Milestone 4)
               ▼
┌─────────────────────────────────────┐
│  Real IRCTC API + Redis + Deploy    │
└─────────────────────────────────────┘
```

---

## 🗺️ Milestone Roadmap

| Milestone | Weeks | Deliverable | Status |
|---|---|---|---|
| **M1** | 1–2 | System analysis, architecture documentation | ✅ Complete |
| **M2** | 3–4 | FastAPI integration layer + web simulator | ✅ **This project** |
| **M3** | 5–6 | ACS/BAP conversational AI flows | 🔲 Next — `/acs/bridge` stub ready |
| **M4** | 7–8 | Production deployment + Redis + real IRCTC APIs | 🔲 Future — `/health` endpoint ready |

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Could not import module "my_ivr_backend"` | Wrong module name in `uvicorn.run()` | Make sure the last line says `"irctc_backend:app"` |
| `FileNotFoundError: irctc_ui.html` | HTML file missing or wrong name | Put `irctc_ui.html` in the same folder as `irctc_backend.py` |
| `ModuleNotFoundError: No module named 'fastapi'` | FastAPI not installed | Run `pip install fastapi uvicorn` |
| `Address already in use` on port 8000 | Another process using port 8000 | Change `port=8000` to `port=8001` in the last line, then visit `localhost:8001` |
| `Session not found` in JSON | Forgot to start call before using service cards | Always click **START CALL** first |
| Browser shows `This site can't be reached` | Server not running | Run `python irctc_backend.py` in the terminal |


