# 🚆 Milestone 3 — Conversational AI Interface Development
### IRCTC Smart IVR System · Module 3

---

## 🎯 Objective

Introduce natural language capabilities to the IVR system so users can speak or type freely instead of just pressing keys. This milestone adds NLU, TTS, STT, a dialogue manager, and a full conversational chat interface on top of the Milestone 2 integration layer.

---

## 📁 Files in This Milestone

| File | Purpose |
|---|---|
| `main.py` | FastAPI app — all endpoints, session store, serves UI |
| `nlu_engine.py` | NLU — intent classifier + entity extractor |
| `dialog_manager.py` | Dialogue manager — routes intent to action |
| `speech_services.py` | TTS and STT configuration helpers |
| `static/style.css` | All CSS — login page + dashboard styling |
| `static/script.js` | All JS — TTS, STT, chat, DTMF, NLU API calls |
| `templates/login.html` | Login page |
| `templates/dashboard.html` | Main IVR dashboard — 3 panels |
| `requirements.txt` | Python dependencies |

---

## 🧠 NLU Engine — `nlu_engine.py`

The brain of the conversational system. Takes raw user text and figures out what the user wants.

### Intent Classifier — `classify_intent(text)`

**How it works — 3 steps:**

**Step 1 — Normalize**
Converts text to lowercase, removes punctuation, collapses spaces.

**Step 2 — Exact Phrase Match** → confidence 0.95
If the text contains an exact known phrase like `"check pnr"` or `"cancel my ticket"` → instantly classified.

**Step 2B — Cancel Override Rule**
If the word `cancel`, `refund`, or `cancellation` appears anywhere → always returns `cancel_ticket`. This prevents the system from misclassifying cancel requests as PNR checks (because both contain the word "ticket").

**Step 3 — Keyword Scoring**
Counts how many keywords of each intent appear. Score formula:
```
score = (matched / total) + (hits × 0.08)
```
Intent with highest score above threshold (0.15) wins.

**9 Intents supported:**

| Intent | Triggered By |
|---|---|
| `pnr_status` | "check pnr", "is my ticket confirmed", "berth number" |
| `book_ticket` | "book", "reserve", "i want to travel" |
| `search_trains` | "search trains", "trains from", "available trains" |
| `cancel_ticket` | "cancel", "refund", "cancel my booking" |
| `complaint` | "dirty", "food", "complaint", "bad service" |
| `train_status` | "where is my train", "live status", "delayed" |
| `talk_to_agent` | "agent", "human", "customer support" |
| `greeting` | "hello", "hi", "namaste", "good morning" |
| `goodbye` | "bye", "end call", "done", "exit" |

---

### Entity Extractor — `extract_entities(text)`

Pulls structured data from raw text using **7 regex patterns**.

| Entity | Pattern | Example |
|---|---|---|
| `PNR_NUMBER` | `\b(\d{10})\b` | `4521679834` |
| `TRAIN_NUMBER` | `\b(\d{5})\b` | `12951` |
| `DATE` | multiple formats | `15 June`, `15-06-2025`, `tomorrow` |
| `FROM_STATION` | `from ([A-Z]{2,5})` | `from NDLS` → `NDLS` |
| `TO_STATION` | `to ([A-Z]{2,5})` | `to MMCT` → `MMCT` |
| `TRAVEL_CLASS` | keyword match | `third ac` → code `2` |
| `PASSENGER_COUNT` | word/digit + keyword | `2 tickets` → `2` |

**Travel class normalization:**

| User says | Code returned |
|---|---|
| sleeper, SL | `1` |
| third ac, 3A | `2` |
| second ac, 2A | `3` |
| first ac, 1A | `4` |
| chair car, CC | `5` |

---

## 🗣️ Dialogue Manager — `dialog_manager.py`

Receives the classified intent and extracted entities, then decides what to do next.

### `dialogue_manager(intent, entities, session)`

**Actions it can return:**

| Action | When | What happens |
|---|---|---|
| `call_endpoint` | All needed entities present | Frontend auto-calls M2 endpoint |
| `collect_entity` | Missing required info | Returns follow-up question |
| `respond` | Just needs a text reply | Returns prompt only |
| `transfer` | Agent intent | Routes to support queue |
| `end_call` | Goodbye intent | Closes session |
| `clarify` | Unknown intent | Asks user to rephrase |

**Example — Booking flow:**
```
User: "Book a ticket"
→ intent: book_ticket
→ entities: {} (none found)
→ action: collect_entity
→ missing: [TRAIN_NUMBER, FROM_STATION, TO_STATION, DATE]
→ follow_up: "What is the 5-digit train number?"

User: "Book train 12951 from NDLS to MMCT on 15 June in third AC"
→ intent: book_ticket
→ entities: TRAIN=12951, FROM=NDLS, TO=MMCT, DATE=15 June, CLASS=2
→ action: call_endpoint → /call/booking
→ result: Booking ID created, fare shown
```

**Train selection flow (after search):**
```
User: "Search trains from NDLS to MMCT"
→ System shows 3 trains
→ session: awaiting_train_selection = True

User: "12951"
→ System detects 5-digit number + awaiting flag
→ Skips NLU entirely
→ Auto-books train 12951 with saved from/to station
```

### Helper Functions

| Function | Returns |
|---|---|
| `get_greeting()` | Good Morning / Afternoon / Evening based on IST time |
| `build_menu_prompt()` | Full menu text string for TTS |
| `handle_train_selection()` | Booking payload when user selects train after search |

---

## 🔊 Speech Services — `speech_services.py`

Handles all configuration for Text-to-Speech and Speech-to-Text.

### Text-to-Speech (TTS)

Every API response includes a `tts_config` field. The browser uses it to speak the response aloud.

```python
TTS_CONFIG = {
    "lang"  : "en-IN",            # Indian English
    "rate"  : 0.92,               # Slightly slower for IVR clarity
    "pitch" : 1.0,
    "volume": 1.0,
    "voice" : "en-IN-NeerjaNeural"  # M4: upgrade to Azure Neural TTS
}
```

**Browser uses it like this (in script.js):**
```javascript
const utt    = new SpeechSynthesisUtterance(text)
utt.lang     = 'en-IN'
utt.rate     = 0.92
window.speechSynthesis.speak(utt)
```

### Speech-to-Text (STT)

User clicks mic → browser captures voice → transcript sent to `/nlu/stt-result` → validated → piped through NLU.

**Validation rules:**
- Empty transcript → rejected
- Confidence below 0.30 → rejected
- Valid → cleaned and sent to `/nlu/understand`

---

## 🎨 Frontend — `static/style.css`

Single CSS file for both pages using CSS custom properties (variables):

```css
:root {
  --bg:        #0f172a;   /* dark background */
  --surface:   #1e293b;   /* panel background */
  --teal:      #14b8a6;   /* primary accent */
  --violet:    #8b5cf6;   /* user message bubbles */
  --amber:     #f59e0b;   /* TTS indicator */
  --green:     #10b981;   /* success states */
  --red:       #ef4444;   /* mic recording / errors */
}
```

**Three-panel dashboard layout:**

```
┌─────────────┬──────────────────────┬──────────────┐
│ LEFT PANEL  │   CENTER PANEL       │ RIGHT PANEL  │
│             │                      │              │
│ IVR Phone   │ Chat Interface       │ Activity Log │
│ Simulator   │ + NLU Debug Panel    │              │
│             │                      │              │
│ Dialpad     │ Intent · Confidence  │ Timestamped  │
│ DTMF/Voice/ │ Entity chips · TTS   │ event log    │
│ Menu tabs   │ STT status           │ per call     │
└─────────────┴──────────────────────┴──────────────┘
```

---

## ⚡ Frontend — `static/script.js`

All frontend logic in one file. Key functions:

| Function | What It Does |
|---|---|
| `startCall()` | Calls `/call/start` + `/call/menu`, enables UI, speaks welcome |
| `pressKey(key)` | Sends DTMF key, always uses `main_menu` flow to prevent misrouting |
| `sendMessage(mode)` | Sends text to `/nlu/understand`, updates chat + NLU panel |
| `autoCallEndpoint()` | Auto-calls M2 endpoint after NLU fills all entities |
| `speak(text)` | TTS — speaks text using browser SpeechSynthesis |
| `toggleMic()` | STT — starts/stops browser SpeechRecognition |
| `appendBotMsg()` | Adds bot bubble with intent tag + entity chips |
| `updateNLUPanel()` | Updates intent, confidence bar, entity display |
| `setMode(m)` | Switches left panel between DTMF / VOICE / MENU tabs |
| `endCall()` | Closes session, resets all UI state |

**DTMF fix (important):** All keys 1–6 always send `current_flow: "main_menu"` regardless of internal state. This prevents the system from sending stale flow names that the backend doesn't understand.

---

## 🖥️ Dashboard — `templates/dashboard.html`

Three-panel layout rendered by Jinja2.

**Left Panel — IVR Phone Simulator:**
- Call screen (shows current prompt, clipped to 3 lines)
- Session ID + current flow display
- Mode toggle: DTMF / VOICE / MENU
  - DTMF → shows 12-key dialpad
  - VOICE → shows reference card with test data (PNR, train number, stations)
  - MENU → shows display-only menu list (keys 1–6 for reference)
- START CALL / END CALL buttons

**Center Panel — Chatbot Interface:**
- Suggestion chips for quick testing
- Message bubbles (bot = teal, user = violet)
- Intent tag + confidence bar inside bot messages
- Entity chips (colour coded by type)
- Chat input + mic button + TTS replay button + send button
- NLU debug panel (intent, confidence meter, entities, STT/TTS status)

**Right Panel — Activity Log:**
- Live timestamped log of every event
- Colour coded: call (teal), NLU (violet), STT (blue), TTS (amber), API (indigo), error (red)

---

## 🔌 M3 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/nlu/understand` | Full NLU pipeline — intent + entities + dialogue |
| `POST` | `/nlu/stt-result` | Receive STT transcript, validate, pipe to NLU |
| `POST` | `/nlu/tts-speak` | Return TTS config for browser SpeechSynthesis |
| `POST` | `/nlu/debug-intent` | Test NLU on any text (no session needed) |
| `GET` | `/nlu/history/{id}` | Full conversation history for a session |

---

## 💬 Quick Test

```bash
pip install -r requirements.txt
python main.py
# Open Chrome → http://localhost:8000
# Login: admin / irctc123
```

Type in chat:
```
Check my PNR 4521679834
Book train 12951 from NDLS to MMCT on 15 June in third AC
Cancel my ticket PNR 4521679834
```

---

*Infosys Springboard Internship · Milestone 3 · Conversational AI Interface*
