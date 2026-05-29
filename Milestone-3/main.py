"""
=============================================================================
FILE        : main.py
PROJECT     : IRCTC Smart IVR — Conversational IVR Modernization Framework
MODULE      : Module 3 — Conversational AI Interface Development
DESCRIPTION : FastAPI Application Entry Point
              - App configuration + CORS middleware
              - Session store (in-memory dict)
              - All M2 call endpoints (/call/*)
              - All M3 NLU endpoints (/nlu/*)
              - Serves login + dashboard HTML templates
              - Health check endpoint

RUN:
    python main.py
    → http://localhost:8000          (Login page)
    → http://localhost:8000/dashboard (IVR Dashboard)
    → http://localhost:8000/docs      (Swagger API docs)
=============================================================================
"""

# =============================================================================
# SECTION 1 — IMPORTS
# =============================================================================
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

# Local modules
from nlu_engine      import classify_intent, extract_entities, INTENT_CONFIG
from dialog_manager  import dialogue_manager, build_menu_prompt, get_greeting, handle_train_selection
from speech_services import get_tts_config, build_tts_response, validate_stt_transcript, get_speech_service_info

# =============================================================================
# SECTION 2 — FASTAPI APP CONFIGURATION
# =============================================================================
app = FastAPI(
    title       = "IRCTC Smart IVR — Conversational AI Layer",
    description = (
        "Module 3: Conversational AI Interface Development. "
        "Integrates NLU (intent recognition + entity extraction), "
        "Text-to-Speech, Speech-to-Text, rule-based matching, "
        "and regex-based entity parsing on top of the M2 Integration Layer."
    ),
    version     = "2.0.0",
    contact     = {
        "name" : "Infosys Springboard Intern",
        "email": "intern@infosys.com",
    },
)

# CORS — allow browser simulator to call this API from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],   # M4: restrict to your deployed domain
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# Static files (CSS, JS, assets)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates (login.html, dashboard.html)
templates = Jinja2Templates(directory="templates")

# =============================================================================
# SECTION 3 — SESSION STORE
# M4 TODO: Replace with Redis → import redis; store = redis.Redis(host="localhost")
# =============================================================================
SESSIONS: dict = {}

# =============================================================================
# SECTION 4 — MENU + FARE CONFIGURATION
# =============================================================================
MAIN_MENU = {
    "1": {"label": "PNR Status",         "acs_event": "ivr_pnr_flow"},
    "2": {"label": "Ticket Booking",     "acs_event": "ivr_booking_flow"},
    "3": {"label": "Train Search",       "acs_event": "ivr_search_flow"},
    "4": {"label": "Cancellation",       "acs_event": "ivr_cancel_flow"},
    "5": {"label": "Register Complaint", "acs_event": "ivr_complaint_flow"},
    "6": {"label": "Talk to Agent",      "acs_event": "ivr_agent_transfer"},
    "0": {"label": "Repeat Menu",        "acs_event": "ivr_repeat_menu"},
}

TRAVEL_CLASS = {
    "1": "Sleeper Class (SL)",
    "2": "Third AC (3A)",
    "3": "Second AC (2A)",
    "4": "First AC (1A)",
    "5": "Chair Car (CC)",
}

BASE_FARE = {"1": 450, "2": 1150, "3": 1800, "4": 3100, "5": 650}

# =============================================================================
# SECTION 5 — PYDANTIC REQUEST MODELS
# =============================================================================

# ── M2 Models ────────────────────────────────────────────────────────────────
class StartRequest(BaseModel):
    caller_id              : str
    language               : Optional[str] = "EN"
    acs_call_connection_id : Optional[str] = None

class MenuRequest(BaseModel):
    session_id: str

class KeyRequest(BaseModel):
    session_id    : str
    key_pressed   : str
    current_flow  : str
    acs_nlu_result: Optional[dict] = None

class PNRRequest(BaseModel):
    session_id : str
    pnr_number : str

class BookingRequest(BaseModel):
    session_id      : str
    train_number    : str
    journey_date    : str
    from_station    : str
    to_station      : str
    travel_class    : str
    passenger_count : Optional[int] = 1

class TrainSearchRequest(BaseModel):
    session_id   : str
    from_station : str
    to_station   : str
    journey_date : Optional[str] = None

class CancelRequest(BaseModel):
    session_id : str
    pnr_number : str

class ComplaintRequest(BaseModel):
    session_id        : str
    complaint_type    : str
    complaint_details : Optional[str] = "No details provided"

class EndCallRequest(BaseModel):
    session_id: str

# ── M3 Models ─────────────────────────────────────────────────────────────────
class NLURequest(BaseModel):
    session_id : str
    user_text  : str
    input_mode : Optional[str] = "text"   # "text" | "speech"

class TTSRequest(BaseModel):
    text   : str
    lang   : Optional[str]   = "en-IN"
    rate   : Optional[float] = 0.92
    pitch  : Optional[float] = 1.0
    volume : Optional[float] = 1.0

class STTResultRequest(BaseModel):
    session_id  : str
    transcript  : str
    confidence  : Optional[float] = 1.0
    lang        : Optional[str]   = "en-IN"

class IntentDebugRequest(BaseModel):
    text: str

# ── Login model ───────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

# =============================================================================
# SECTION 6 — SESSION HELPERS
# =============================================================================

def create_session(caller_id: str, language: str, acs_id) -> dict:
    sid = str(uuid.uuid4())
    session = {
        "session_id"            : sid,
        "caller_id"             : caller_id,
        "language"              : language,
        "acs_call_connection_id": acs_id,
        "current_flow"          : "welcome",
        "booking_data"          : {},
        "conversation_history"  : [],
        "last_intent"           : None,
        "call_started_at"       : datetime.utcnow().isoformat(),
        "call_ended_at"         : None,
        "event_log"             : [],
    }
    SESSIONS[sid] = session
    return session

def fetch_session(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please start a new call."
        )
    return session

def log_event(session: dict, event_name: str, details: dict):
    session["event_log"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "event"    : event_name,
        **details,
    })

def build_response(prompt: str, data: dict = None,
                   acs_event: str = "none", status: str = "success") -> dict:
    """Standard response wrapper — every endpoint returns this shape."""
    return {
        "status"    : status,
        "timestamp" : datetime.utcnow().isoformat(),
        "prompt"    : prompt,
        "acs_event" : acs_event,
        "tts_config": get_tts_config(prompt),
        "data"      : data or {},
    }

# =============================================================================
# SECTION 7 — PAGE ROUTES (Login + Dashboard)
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the IVR dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/auth/login", summary="Login — validate credentials")
async def login(payload: LoginRequest):
    """
    Simple credential check.
    M4: Replace with real auth (JWT / OAuth2).
    Demo credentials: admin / irctc123
    """
    DEMO_USERS = {
        "admin"  : "irctc123",
        "intern" : "infosys2025",
    }
    if DEMO_USERS.get(payload.username) == payload.password:
        return {
            "status"  : "success",
            "message" : f"Welcome, {payload.username}!",
            "redirect": "/dashboard",
            "user"    : payload.username,
        }
    raise HTTPException(status_code=401, detail="Invalid username or password.")

# =============================================================================
# SECTION 8 — M2 CALL ENDPOINTS  (Integration Layer — unchanged)
# =============================================================================

@app.post("/call/start", summary="[M2] Start Call — Welcome Prompt")
def start_call(payload: StartRequest):
    """Creates a session and returns the English welcome prompt."""
    session  = create_session(payload.caller_id, payload.language, payload.acs_call_connection_id)
    greeting = get_greeting()
    prompt   = (
        f"{greeting}. Welcome to IRCTC Smart IVR. "
        "You can press keys or speak naturally. "
        "Say PNR Status, Book Ticket, Search Trains, Cancel Ticket, or Complaint. "
        "Or press 1 to 6 on the keypad."
    )
    log_event(session, "call_started", {"caller_id": payload.caller_id})
    return build_response(
        prompt    = prompt,
        data      = {
            "session_id": session["session_id"],
            "caller_id" : payload.caller_id,
            "language"  : "English",
        },
        acs_event = "welcome_delivered",
    )

@app.post("/call/menu", summary="[M2] IVR Main Menu — Keys 1–6")
def main_menu(payload: MenuRequest):
    """Returns the full main menu voice prompt."""
    session = fetch_session(payload.session_id)
    session["current_flow"] = "main_menu"
    log_event(session, "menu_presented", {})
    prompt = build_menu_prompt()
    return build_response(
        prompt    = prompt,
        data      = {
            "session_id"  : payload.session_id,
            "menu_options": {k: v["label"] for k, v in MAIN_MENU.items()},
        },
        acs_event = "menu_presented",
    )

@app.post("/call/key", summary="[M2] Key Press / DTMF Handler")
def handle_key(payload: KeyRequest):
    """Routes DTMF key presses to the correct service flow."""
    session = fetch_session(payload.session_id)
    key     = payload.key_pressed.strip()
    flow    = payload.current_flow
    log_event(session, "key_pressed", {"key": key, "flow": flow})

    if flow == "main_menu":
        if key not in MAIN_MENU:
            return build_response(
                prompt    = f"Sorry, {key} is not a valid option. " + build_menu_prompt(),
                data      = {"key_pressed": key},
                acs_event = "invalid_key",
                status    = "invalid",
            )
        selected = MAIN_MENU[key]
        session["current_flow"] = selected["acs_event"]

        if key == "0":
            session["current_flow"] = "main_menu"
            return build_response(prompt=build_menu_prompt(), acs_event="menu_repeated")

        if key == "6":
            return build_response(
                prompt    = "Connecting you to an IRCTC support agent. Please hold.",
                data      = {"transfer_queue": "irctc_general_support"},
                acs_event = "agent_transfer",
                status    = "transfer",
            )
        return build_response(
            prompt    = f"You selected {selected['label']}. Please continue.",
            data      = {"key_pressed": key, "service": selected["label"]},
            acs_event = selected["acs_event"],
        )

    elif flow == "class_select":
        if key not in TRAVEL_CLASS:
            return build_response(
                prompt    = "Invalid selection. Press 1 for Sleeper, 2 for Third AC, 3 for Second AC, 4 for First AC, 5 for Chair Car.",
                acs_event = "invalid_class",
                status    = "invalid",
            )
        session["booking_data"]["travel_class"] = key
        return build_response(
            prompt    = f"You selected {TRAVEL_CLASS[key]}.",
            data      = {"travel_class": TRAVEL_CLASS[key]},
            acs_event = "class_selected",
        )

    elif flow == "complaint_type":
        complaint_map = {"1": "Train Service", "2": "Catering", "3": "Cleanliness"}
        if key not in complaint_map:
            return build_response(
                prompt    = "Press 1 for Train Service, 2 for Catering, 3 for Cleanliness.",
                acs_event = "invalid_complaint_type",
                status    = "invalid",
            )
        session["booking_data"]["complaint_type"] = key
        return build_response(
            prompt    = f"You selected {complaint_map[key]} complaint. Please proceed.",
            data      = {"complaint_category": complaint_map[key]},
            acs_event = "complaint_type_selected",
        )

    return build_response(
        prompt    = "I did not understand that. Press 0 to hear the menu.",
        acs_event = "unknown_flow",
        status    = "error",
    )

@app.post("/call/pnr", summary="[M2] PNR Status Check")
def check_pnr(payload: PNRRequest):
    """Validates 10-digit PNR and returns mock booking details."""
    session = fetch_session(payload.session_id)
    if not payload.pnr_number.isdigit() or len(payload.pnr_number) != 10:
        return build_response(
            prompt    = "Invalid PNR. A PNR must be exactly 10 digits. Please try again.",
            acs_event = "invalid_pnr",
            status    = "invalid",
        )
    log_event(session, "pnr_checked", {"pnr": payload.pnr_number})
    pnr_data = {
        "pnr_number"    : payload.pnr_number,
        "train_number"  : "12951",
        "train_name"    : "Mumbai Rajdhani Express",
        "from_station"  : "New Delhi (NDLS)",
        "to_station"    : "Mumbai Central (MMCT)",
        "journey_date"  : "15-Jun-2025",
        "travel_class"  : "Third AC (3A)",
        "booking_status": "CONFIRMED",
        "coach"         : "B-4",
        "seat_number"   : "32 — Lower Berth",
        "platform"      : "Platform 2",
        "departure"     : "16:55",
        "arrival"       : "08:35 (+1 day)",
    }
    prompt = (
        f"PNR {payload.pnr_number} status: CONFIRMED. "
        "Train 12951 Mumbai Rajdhani Express. "
        "Coach B-4, Seat 32, Lower Berth. "
        "Departure 4:55 PM from Platform 2. Have a safe journey!"
    )
    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "pnr_details": pnr_data},
        acs_event = "pnr_status_delivered",
    )

@app.post("/call/booking", summary="[M2] Ticket Booking")
def book_ticket(payload: BookingRequest):
    """Creates a ticket booking and returns Booking ID with fare."""
    session = fetch_session(payload.session_id)
    if not payload.train_number.isdigit() or len(payload.train_number) != 5:
        return build_response(
            prompt    = "Invalid train number. Please enter a 5-digit train number.",
            acs_event = "invalid_train",
            status    = "invalid",
        )
    log_event(session, "booking_created", {"train": payload.train_number})
    fare_per = BASE_FARE.get(payload.travel_class, 450)
    total    = fare_per * payload.passenger_count
    bid      = f"IVR{uuid.uuid4().hex[:8].upper()}"
    t_class  = TRAVEL_CLASS.get(payload.travel_class, "Sleeper Class (SL)")
    booking  = {
        "booking_id"  : bid,
        "train_number": payload.train_number,
        "from_station": payload.from_station.upper(),
        "to_station"  : payload.to_station.upper(),
        "travel_class": t_class,
        "passengers"  : payload.passenger_count,
        "total_fare"  : f"Rs. {total}",
        "status"      : "PENDING PAYMENT",
        "payment_link": f"https://irctc.co.in/payment/{bid}",
        "expires_in"  : "15 minutes",
    }
    prompt = (
        f"Booking {bid} created successfully. "
        f"Train {payload.train_number}, {t_class}. "
        f"Total fare Rupees {total} for {payload.passenger_count} passenger. "
        "Payment link sent to your registered mobile. Complete payment within 15 minutes."
    )
    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "booking": booking},
        acs_event = "booking_initiated",
    )

@app.post("/call/trains", summary="[M2] Train Search")
def search_trains(payload: TrainSearchRequest):
    """Searches available trains between two stations."""
    session = fetch_session(payload.session_id)
    log_event(session, "train_search", {"from": payload.from_station, "to": payload.to_station})
    trains = [
        {"number": "12951", "name": "Mumbai Rajdhani",    "departs": "16:55", "arrives": "08:35+1", "classes": "1A,2A,3A"},
        {"number": "12909", "name": "Garib Rath Express", "departs": "15:35", "arrives": "07:15+1", "classes": "3A,CC"},
        {"number": "12927", "name": "Paschim Express",    "departs": "11:05", "arrives": "07:30+1", "classes": "SL,3A,2A"},
    ]
    prompt = (
        f"Found 3 trains from {payload.from_station.upper()} to {payload.to_station.upper()}. "
        "Train 1: 12951 Mumbai Rajdhani, departs 4:55 PM, arrives 8:35 AM next day. "
        "Train 2: 12909 Garib Rath Express, departs 3:35 PM, arrives 7:15 AM next day. "
        "Train 3: 12927 Paschim Express, departs 11:05 AM, arrives 7:30 AM next day. "
        "Please type the train number you want to book. For example, type 12951."
    )
    return build_response(
        prompt    = prompt,
        data      = {
            "session_id"  : payload.session_id,
            "from_station": payload.from_station.upper(),
            "to_station"  : payload.to_station.upper(),
            "trains"      : trains,
        },
        acs_event = "train_list_delivered",
    )

@app.post("/call/cancel", summary="[M2] Cancellation and Refund")
def cancel_ticket(payload: CancelRequest):
    """Cancels a ticket by PNR and returns cancellation details with train info."""
    session = fetch_session(payload.session_id)
    if not payload.pnr_number.isdigit() or len(payload.pnr_number) != 10:
        return build_response(
            prompt    = "Invalid PNR. Please enter a 10-digit PNR number.",
            acs_event = "invalid_pnr",
            status    = "invalid",
        )
    log_event(session, "cancellation_requested", {"pnr": payload.pnr_number})
    rid    = f"REF{uuid.uuid4().hex[:6].upper()}"
    cancel = {
        "pnr_number"         : payload.pnr_number,
        "train_number"       : "12951",
        "train_name"         : "Mumbai Rajdhani Express",
        "from_station"       : "New Delhi (NDLS)",
        "to_station"         : "Mumbai Central (MMCT)",
        "journey_date"       : "15-Jun-2025",
        "travel_class"       : "Third AC (3A)",
        "coach"              : "B-4",
        "seat_number"        : "32 — Lower Berth",
        "passenger"          : "Adult — 1",
        "booking_status"     : "CANCELLED",
        "refund_amount"      : "Rs. 985",
        "refund_id"          : rid,
        "refund_to"          : "Original payment method",
        "processing_time"    : "5 to 7 working days",
    }
    prompt = (
        f"Cancellation confirmed for PNR {payload.pnr_number}. "
        "Train 12951 Mumbai Rajdhani Express, "
        "from New Delhi to Mumbai Central. "
        "Coach B-4, Seat 32, Lower Berth. "
        f"Booking Status: CANCELLED. "
        f"Refund of Rupees 985 will be credited to your original payment method "
        f"within 5 to 7 working days. "
        f"Your refund reference number is {rid}."
    )
    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "cancellation": cancel},
        acs_event = "cancellation_done",
    )

@app.post("/call/complaint", summary="[M2] Register Complaint")
def register_complaint(payload: ComplaintRequest):
    """Registers a complaint and returns a Rail Madad ticket number."""
    session = fetch_session(payload.session_id)
    log_event(session, "complaint_registered", {"type": payload.complaint_type})
    labels = {"1": "Train Service", "2": "Catering", "3": "Cleanliness"}
    label  = labels.get(payload.complaint_type, "General")
    tno    = f"CMP{uuid.uuid4().hex[:7].upper()}"
    c_data = {
        "complaint_ticket" : tno,
        "category"         : label,
        "details"          : payload.complaint_details,
        "status"           : "REGISTERED",
        "resolution_time"  : "48 hours",
        "track_at"         : f"https://railmadad.indianrailways.gov.in/track/{tno}",
    }
    prompt = (
        f"Your {label} complaint has been registered successfully. "
        f"Complaint ticket number is {tno}. "
        "You will receive a resolution within 48 hours. "
        "Thank you for helping us improve our services."
    )
    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "complaint": c_data},
        acs_event = "complaint_filed",
    )

@app.post("/call/end", summary="[M2] End Call — Session Cleanup")
def end_call(payload: EndCallRequest):
    """Ends the call gracefully and returns session summary."""
    session = fetch_session(payload.session_id)
    session["call_ended_at"] = datetime.utcnow().isoformat()
    session["current_flow"]  = "ended"
    log_event(session, "call_ended", {})
    prompt = (
        "Thank you for calling IRCTC Smart IVR. "
        "We hope we were able to assist you. "
        "For more services visit www.irctc.co.in. "
        "Have a great day. Goodbye."
    )
    return build_response(
        prompt    = prompt,
        data      = {
            "session_id"  : payload.session_id,
            "call_started": session["call_started_at"],
            "call_ended"  : session["call_ended_at"],
            "total_events": len(session["event_log"]),
        },
        acs_event = "call_ended",
    )

# =============================================================================
# SECTION 9 — M3 NLU ENDPOINTS
# =============================================================================

@app.post("/nlu/understand", summary="[M3] NLU Pipeline — Intent + Entity + Dialogue")
def nlu_understand(payload: NLURequest):
    """
    Main NLU endpoint. Full pipeline:
      1. Intent classification  (nlu_engine.classify_intent)
      2. Entity extraction      (nlu_engine.extract_entities)
      3. Dialogue management    (dialog_manager.dialogue_manager)
    """
    session = fetch_session(payload.session_id)
    text    = payload.user_text.strip()

    if not text:
        return build_response(
            prompt    = "I didn't catch that. Could you please say that again?",
            acs_event = "nlu_empty_input",
            status    = "invalid",
        )

    # ── TRAIN SELECTION INTERCEPT ─────────────────────────────────────────────
    # If user just typed a 5-digit train number after seeing search results,
    # skip full NLU and go straight to booking with saved session context.
    import re as _re
    awaiting = session.get("booking_data", {}).get("awaiting_train_selection", False)
    if awaiting and _re.fullmatch(r'\d{5}', text.strip()):
        dialogue = handle_train_selection(text.strip(), session)
        session["conversation_history"].append({
            "turn"      : len(session["conversation_history"]) + 1,
            "timestamp" : datetime.utcnow().isoformat(),
            "user_text" : text,
            "input_mode": payload.input_mode,
            "intent"    : "train_selection",
            "confidence": 1.0,
            "entities"  : {"TRAIN_NUMBER": text.strip()},
            "response"  : dialogue["prompt"],
        })
        log_event(session, "train_selected", {"train_number": text.strip()})
        return build_response(
            prompt    = dialogue["prompt"],
            data      = {
                "session_id": payload.session_id,
                "user_text" : text,
                "input_mode": payload.input_mode,
                "nlu": {
                    "intent"    : "train_selection",
                    "confidence": 1.0,
                    "method"    : "train_selection_intercept",
                    "matched_on": [text.strip()],
                    "all_scores": {},
                },
                "entities": {"TRAIN_NUMBER": text.strip()},
                "dialogue": {
                    "action"   : dialogue["action"],
                    "endpoint" : dialogue["endpoint"],
                    "payload"  : dialogue["payload"],
                    "missing"  : [],
                    "follow_up": None,
                },
            },
            acs_event = dialogue["acs_event"],
        )
    # ─────────────────────────────────────────────────────────────────────────

    # Step 1 — Classify intent
    intent_result = classify_intent(text)

    # Step 2 — Extract entities
    entities = extract_entities(text)

    # Step 3 — Dialogue decision
    dialogue = dialogue_manager(intent_result["intent"], entities, session)

    # Step 4 — Update session history
    session["last_intent"] = intent_result["intent"]
    session["conversation_history"].append({
        "turn"      : len(session["conversation_history"]) + 1,
        "timestamp" : datetime.utcnow().isoformat(),
        "user_text" : text,
        "input_mode": payload.input_mode,
        "intent"    : intent_result["intent"],
        "confidence": intent_result["confidence"],
        "entities"  : entities,
        "response"  : dialogue["prompt"],
    })
    log_event(session, "nlu_processed", {
        "text"    : text,
        "intent"  : intent_result["intent"],
        "entities": entities,
    })

    return build_response(
        prompt    = dialogue["prompt"],
        data      = {
            "session_id": payload.session_id,
            "user_text" : text,
            "input_mode": payload.input_mode,
            "nlu": {
                "intent"    : intent_result["intent"],
                "confidence": intent_result["confidence"],
                "method"    : intent_result["method"],
                "matched_on": intent_result["matched_on"],
                "all_scores": intent_result.get("all_scores", {}),
            },
            "entities": entities,
            "dialogue": {
                "action"   : dialogue["action"],
                "endpoint" : dialogue["endpoint"],
                "payload"  : dialogue["payload"],
                "missing"  : dialogue["missing"],
                "follow_up": dialogue["follow_up"],
            },
        },
        acs_event = dialogue["acs_event"],
    )

@app.post("/nlu/stt-result", summary="[M3] Receive STT Transcript from Browser")
def receive_stt_result(payload: STTResultRequest):
    """Validates STT transcript and pipes through NLU pipeline."""
    session    = fetch_session(payload.session_id)
    validation = validate_stt_transcript(payload.transcript, payload.confidence)

    if not validation["valid"]:
        return build_response(
            prompt    = "I could not hear that clearly. Please try speaking again.",
            acs_event = "stt_invalid",
            status    = "invalid",
        )

    log_event(session, "stt_received", {
        "transcript": payload.transcript,
        "confidence": payload.confidence,
    })

    # Pipe through NLU
    return nlu_understand(NLURequest(
        session_id = payload.session_id,
        user_text  = validation["transcript"],
        input_mode = "speech",
    ))

@app.post("/nlu/tts-speak", summary="[M3] TTS — Get Config for Browser SpeechSynthesis")
def tts_speak(payload: TTSRequest):
    """Returns TTS configuration for the browser Web Speech API."""
    return build_tts_response(payload.text)

@app.post("/nlu/debug-intent", summary="[M3] Debug — Test NLU on Any Text")
def debug_intent(payload: IntentDebugRequest):
    """Runs the full NLU pipeline on any text without needing a session."""
    intent_result = classify_intent(payload.text)
    entities      = extract_entities(payload.text)
    return {
        "status"         : "debug",
        "timestamp"      : datetime.utcnow().isoformat(),
        "input"          : payload.text,
        "nlu_result"     : intent_result,
        "entities"       : entities,
        "intent_examples": {i: c["examples"] for i, c in INTENT_CONFIG.items()},
    }

@app.get("/nlu/history/{session_id}", summary="[M3] Conversation History")
def get_conversation_history(session_id: str):
    """Returns the full conversation history for a session."""
    session = fetch_session(session_id)
    return build_response(
        prompt = "Conversation history retrieved.",
        data   = {
            "session_id"          : session_id,
            "total_turns"         : len(session["conversation_history"]),
            "last_intent"         : session.get("last_intent"),
            "conversation_history": session["conversation_history"],
        },
        acs_event = "history_retrieved",
    )

# =============================================================================
# SECTION 10 — UTILITY ENDPOINTS
# =============================================================================

@app.get("/session/{session_id}", summary="Session State Inspector")
def get_session_info(session_id: str):
    return build_response(
        prompt    = "Session data retrieved.",
        data      = fetch_session(session_id),
        acs_event = "session_info",
    )

@app.get("/health", summary="Health Check — M4 Deployment Ready")
def health_check():
    return build_response(
        prompt = "IRCTC Smart IVR Conversational AI Layer is running.",
        data   = {
            "app_name"       : "IRCTC Smart IVR",
            "version"        : "2.0.0",
            "milestone"      : "M3 — Conversational AI Interface",
            "status"         : "healthy",
            "active_sessions": len(SESSIONS),
            "speech_services": get_speech_service_info(),
            "endpoints_m2"   : ["/call/start", "/call/menu", "/call/key",
                                 "/call/pnr", "/call/booking", "/call/trains",
                                 "/call/cancel", "/call/complaint", "/call/end"],
            "endpoints_m3"   : ["/nlu/understand", "/nlu/stt-result",
                                 "/nlu/tts-speak", "/nlu/debug-intent",
                                 "/nlu/history/{id}"],
        },
        acs_event = "health_ok",
    )

# =============================================================================
# SECTION 11 — RUN SERVER
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
