"""
=============================================================================
PROJECT   : Conversational IVR Modernization Framework
MODULE    : Module 2 — Integration Layer Development
MILESTONE : Milestone 2 | My IRCTC Smart IVR System
APPROACH  : Web Simulator (Python FastAPI)
AUTHOR    : [Your Name] — Infosys Springboard Internship

ARCHITECTURE
------------
  [Web Browser Simulator]
          |
          v
  [FastAPI Integration Layer]  ← THIS FILE (my_ivr_backend.py)
          |
          |── GET  /                  → Serves IVR Web Simulator UI
          |── POST /call/start        → Welcome prompt in English
          |── POST /call/menu         → IVR Main Menu (keys 1–6)
          |── POST /call/key          → Key/DTMF input handler
          |── POST /call/pnr          → PNR Status lookup
          |── POST /call/booking      → Ticket Booking
          |── POST /call/trains       → Train Search
          |── POST /call/cancel       → Cancellation
          |── POST /call/complaint    → Complaint Registration
          |── POST /call/end          → End call + session cleanup
          |── GET  /session/{sid}     → Session state inspector
          |── GET  /health            → Health check (M4 deployment)
          v
  [ACS / BAP Conversational AI]  ← Milestone 3 plugs in here

=============================================================================
"""

# =============================================================================
# SECTION 1 — IMPORTS
# =============================================================================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

# =============================================================================
# SECTION 2 — FASTAPI APP CONFIGURATION
# =============================================================================
app = FastAPI(
    title       = "My IRCTC Smart IVR — Integration Layer",
    description = (
        "Module 2: Middleware API layer connecting legacy VXML IVR "
        "to the Conversational AI stack (ACS/BAP). "
        "Web Simulator approach ."
    ),
    version     = "1.0.0",
    contact     = {
        "name" : "Infosys Springboard Intern",
        "email": "intern@infosys.com",
    },
    license_info = {
        "name": "Infosys Springboard Project",
    },
)

# CORS — allow the browser simulator to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],   # M4: restrict to your domain in production
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# =============================================================================
# SECTION 3 — IN-MEMORY SESSION STORE
# M4 TODO: Replace with Redis → import redis; store = redis.Redis(host="localhost")
# =============================================================================
SESSIONS: dict = {}

# =============================================================================
# SECTION 4 — MENU CONFIGURATION
# Each key maps to: label, acs_event (for M3 ACS/BAP), and sub-prompt
# =============================================================================
MAIN_MENU = {
    "1": {
        "label"     : "PNR Status",
        "acs_event" : "ivr_pnr_flow",
        "prompt"    : "You selected PNR Status. Please enter your 10-digit PNR number.",
    },
    "2": {
        "label"     : "Ticket Booking",
        "acs_event" : "ivr_booking_flow",
        "prompt"    : "You selected Ticket Booking. Please enter your 5-digit train number.",
    },
    "3": {
        "label"     : "Train Search",
        "acs_event" : "ivr_search_flow",
        "prompt"    : "You selected Train Search. Please enter your source station code.",
    },
    "4": {
        "label"     : "Cancellation",
        "acs_event" : "ivr_cancel_flow",
        "prompt"    : "You selected Cancellation and Refund. Please enter your 10-digit PNR number.",
    },
    "5": {
        "label"     : "Register Complaint",
        "acs_event" : "ivr_complaint_flow",
        "prompt"    : "You selected Complaint Registration. Press 1 for Train Service, 2 for Catering, 3 for Cleanliness.",
    },
    "6": {
        "label"     : "Talk to Agent",
        "acs_event" : "ivr_agent_transfer",
        "prompt"    : "Connecting you to an IRCTC support agent. Please hold. Your estimated wait time is 3 minutes.",
    },
    "0": {
        "label"     : "Repeat Menu",
        "acs_event" : "ivr_repeat_menu",
        "prompt"    : "Repeating the menu.",
    },
}

# Booking class options
TRAVEL_CLASS = {
    "1": "Sleeper Class (SL)",
    "2": "Third AC (3A)",
    "3": "Second AC (2A)",
    "4": "First AC (1A)",
    "5": "Chair Car (CC)",
}

# Fare per class (base, for 1 passenger)
BASE_FARE = { "1": 450, "2": 1150, "3": 1800, "4": 3100, "5": 650 }

# =============================================================================
# SECTION 5 — PYDANTIC REQUEST MODELS
# These define exactly what JSON the frontend must send to each endpoint
# =============================================================================

class StartRequest(BaseModel):
    caller_id : str                          # Simulated phone number
    language  : Optional[str] = "EN"        # Always English in this version
    # M3 HOOK: ACS will pass acs_call_connection_id here
    acs_call_connection_id: Optional[str] = None

class MenuRequest(BaseModel):
    session_id: str                          # Must be an active session

class KeyRequest(BaseModel):
    session_id  : str
    key_pressed : str                        # The digit the user pressed
    current_flow: str                        # Which menu/sub-menu is active
    # M3 HOOK: ACS NLU result comes here instead of a digit
    acs_nlu_result: Optional[dict] = None

class PNRRequest(BaseModel):
    session_id : str
    pnr_number : str                         # Must be exactly 10 digits

class BookingRequest(BaseModel):
    session_id      : str
    train_number    : str
    journey_date    : str                    # Format: DDMMYYYY
    from_station    : str
    to_station      : str
    travel_class    : str                    # Key from TRAVEL_CLASS dict
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
    session_id       : str
    complaint_type   : str                   # "1" train, "2" catering, "3" cleanliness
    complaint_details: Optional[str] = "No details provided"

class EndCallRequest(BaseModel):
    session_id: str

# M3: ACS/BAP bridge request model
class ACSBridgeRequest(BaseModel):
    """
    VXML-to-ACS bridge connector.
    M3 TODO: Replace stub body with real Azure ACS SDK:
        from azure.communication.callautomation import CallAutomationClient
        client = CallAutomationClient.from_connection_string(ACS_CONN_STR)
        conn   = client.get_call_connection(payload.acs_call_connection_id)
        conn.play_media(TextSource(text=payload.tts_text, voice_name="en-IN-NeerjaNeural"))
    """
    session_id            : str
    acs_call_connection_id: str
    vxml_event            : str              # "filled" | "noinput" | "nomatch" | "disconnect"
    tts_text              : Optional[str]  = None
    collect_digits        : Optional[bool] = False
    max_digits            : Optional[int]  = 1

# =============================================================================
# SECTION 6 — HELPER FUNCTIONS
# =============================================================================

def create_session(caller_id: str, language: str, acs_id) -> dict:
    """Create a brand-new session and store it."""
    sid = str(uuid.uuid4())
    session = {
        "session_id"             : sid,
        "caller_id"              : caller_id,
        "language"               : language,
        "acs_call_connection_id" : acs_id,
        "current_flow"           : "welcome",
        "booking_data"           : {},       # Accumulates multi-step booking inputs
        "call_started_at"        : datetime.utcnow().isoformat(),
        "call_ended_at"          : None,
        "event_log"              : [],       # Full trail of what happened
    }
    SESSIONS[sid] = session
    return session

def fetch_session(session_id: str) -> dict:
    """Retrieve session or raise 404."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new call.")
    return session

def log_event(session: dict, event_name: str, details: dict):
    """Append a timestamped event to the session log."""
    session["event_log"].append({
        "timestamp"  : datetime.utcnow().isoformat(),
        "event"      : event_name,
        **details,
    })

def build_response(prompt: str, data: dict = None, acs_event: str = "none", status: str = "success") -> dict:
    """Standard response wrapper — every endpoint returns this shape."""
    return {
        "status"    : status,
        "timestamp" : datetime.utcnow().isoformat(),
        "prompt"    : prompt,        # TTS text — what would be spoken to the caller
        "acs_event" : acs_event,     # M3: maps to ACS bot dialog trigger
        "data"      : data or {},
    }

def get_greeting() -> str:
    """Return a time-aware greeting in IST."""
    hour = (datetime.utcnow().hour + 5) % 24  # UTC → IST
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"

def build_menu_prompt() -> str:
    """Generate the main menu voice prompt string."""
    return (
        "Main Menu. "
        "Press 1 for PNR Status. "
        "Press 2 for Ticket Booking. "
        "Press 3 for Train Search. "
        "Press 4 for Cancellation and Refund. "
        "Press 5 to Register a Complaint. "
        "Press 6 to Talk to an Agent. "
        "Press 0 to Repeat this Menu."
    )

# =============================================================================
# SECTION 7 — SERVE FRONTEND
# =============================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_ui():
    """Serve the Web Simulator HTML page."""
    with open("irctc_ui.html", "r", encoding="utf-8") as f:
        return f.read()

# =============================================================================
# SECTION 8 — ENDPOINT 1: START CALL / WELCOME PROMPT
# Requirement: Welcome prompt in English only
# =============================================================================

@app.post("/call/start", summary="Start Call — English Welcome Prompt")
def start_call(payload: StartRequest):
    """
    Entry point for every IVR call.
    Creates a new session and returns the English welcome message.
    M3 HOOK: acs_call_connection_id stored so ACS SDK can play TTS on real call.
    """
    session = create_session(payload.caller_id, payload.language, payload.acs_call_connection_id)
    log_event(session, "call_started", {"caller_id": payload.caller_id})

    greeting = get_greeting()
    welcome_prompt = (
        f"{greeting}. Welcome to IRCTC Smart IVR. "
        "Your trusted railway assistance system. "
        "This call is in English. "
        "Please listen carefully to the following options."
    )

    return build_response(
        prompt    = welcome_prompt,
        data      = {
            "session_id": session["session_id"],
            "caller_id" : payload.caller_id,
            "language"  : "English",
            "next_step" : "Call /call/menu to hear the main menu",
            # M3 HOOK: ACS reads next_step to trigger start_recognizing_media()
        },
        acs_event = "welcome_delivered",
    )

# =============================================================================
# SECTION 9 — ENDPOINT 2: MAIN MENU
# Requirement: Menus 1 to 6 — PNR, Booking, Search, Cancel, Complaint, Agent
# =============================================================================

@app.post("/call/menu", summary="IVR Main Menu — Keys 1 to 6")
def main_menu(payload: MenuRequest):
    """
    Reads out the main menu options to the caller.
    Returns the menu structure so the UI can display it and ACS can present choices.
    """
    session = fetch_session(payload.session_id)
    session["current_flow"] = "main_menu"
    log_event(session, "menu_presented", {"flow": "main_menu"})

    menu_prompt = build_menu_prompt()

    return build_response(
        prompt    = menu_prompt,
        data      = {
            "session_id"  : payload.session_id,
            "menu_options": {k: v["label"] for k, v in MAIN_MENU.items()},
            "current_flow": "main_menu",
            "next_step"   : "Call /call/key with session_id, key_pressed, and current_flow=main_menu",
        },
        acs_event = "menu_presented",
    )

# =============================================================================
# SECTION 10 — ENDPOINT 3: KEY / DTMF HANDLER
# Requirement: Key handling — press key → get output/reaction with message
# =============================================================================

@app.post("/call/key", summary="Key Press Handler — DTMF Input")
def handle_key(payload: KeyRequest):
    """
    Universal key/DTMF handler. Routes the caller to the right sub-flow
    based on which key was pressed and which flow is currently active.

    Flows handled:
      - main_menu     : keys 1–6, 0
      - class_select  : keys 1–5 (travel class)
      - complaint_type: keys 1–3 (complaint category)

    M3 HOOK: Replace key matching with BAP NLU intent (acs_nlu_result field).
    """
    session = fetch_session(payload.session_id)
    key     = payload.key_pressed.strip()
    flow    = payload.current_flow

    log_event(session, "key_pressed", {"key": key, "flow": flow})

    # ── FLOW: Main Menu ──────────────────────────────────────────────────────
    if flow == "main_menu":

        if key not in MAIN_MENU:
            return build_response(
                prompt    = f"Sorry, {key} is not a valid option. " + build_menu_prompt(),
                data      = {"session_id": payload.session_id, "key_pressed": key, "valid_keys": list(MAIN_MENU.keys())},
                acs_event = "invalid_key",
                status    = "invalid",
            )

        selected = MAIN_MENU[key]
        session["current_flow"] = selected["acs_event"]

        # Key 0 — repeat menu
        if key == "0":
            session["current_flow"] = "main_menu"
            return build_response(
                prompt    = build_menu_prompt(),
                data      = {"session_id": payload.session_id},
                acs_event = "menu_repeated",
            )

        # Key 6 — agent transfer
        if key == "6":
            return build_response(
                prompt    = selected["prompt"],
                data      = {"session_id": payload.session_id, "transfer_queue": "irctc_general_support", "estimated_wait": "3 minutes"},
                acs_event = "agent_transfer",
                status    = "transfer",
            )

        # Keys 1–5 — service flows
        return build_response(
            prompt    = selected["prompt"],
            data      = {
                "session_id"  : payload.session_id,
                "key_pressed" : key,
                "service"     : selected["label"],
                "current_flow": selected["acs_event"],
                "next_step"   : f"Call the /call/{['','pnr','booking','trains','cancel','complaint'][int(key)]} endpoint",
            },
            acs_event = selected["acs_event"],
        )

    # ── FLOW: Travel Class Selection ─────────────────────────────────────────
    elif flow == "class_select":

        if key not in TRAVEL_CLASS:
            return build_response(
                prompt    = "Invalid class. Press 1 for Sleeper, 2 for Third AC, 3 for Second AC, 4 for First AC, 5 for Chair Car.",
                data      = {"session_id": payload.session_id},
                acs_event = "invalid_class",
                status    = "invalid",
            )

        session["booking_data"]["travel_class"] = key
        chosen_class = TRAVEL_CLASS[key]
        return build_response(
            prompt    = f"You selected {chosen_class}. Now please use the Ticket Booking panel to confirm your journey details.",
            data      = {"session_id": payload.session_id, "travel_class": chosen_class, "class_code": key},
            acs_event = "class_selected",
        )

    # ── FLOW: Complaint Type Selection ───────────────────────────────────────
    elif flow == "complaint_type":

        complaint_map = {"1": "Train Service", "2": "Catering", "3": "Cleanliness"}
        if key not in complaint_map:
            return build_response(
                prompt    = "Invalid option. Press 1 for Train Service, 2 for Catering, 3 for Cleanliness.",
                data      = {"session_id": payload.session_id},
                acs_event = "invalid_complaint_type",
                status    = "invalid",
            )

        c_type = complaint_map[key]
        session["booking_data"]["complaint_type"] = key
        return build_response(
            prompt    = f"You selected {c_type} complaint. Please use the Complaint panel to submit your complaint details.",
            data      = {"session_id": payload.session_id, "complaint_category": c_type},
            acs_event = "complaint_type_selected",
        )

    # ── Unknown flow ─────────────────────────────────────────────────────────
    return build_response(
        prompt    = "I did not understand that. Please press 0 to hear the menu again.",
        data      = {"session_id": payload.session_id, "flow_received": flow},
        acs_event = "unknown_flow",
        status    = "error",
    )

# =============================================================================
# SECTION 11 — ENDPOINT 4: PNR STATUS
# =============================================================================

@app.post("/call/pnr", summary="PNR Status Check")
def check_pnr(payload: PNRRequest):
    """
    Validates and looks up PNR status.
    Returns mock data structured exactly as a real IRCTC API would return.
    M3 TODO: Replace mock with → requests.get("https://api.irctc.co.in/pnr/{pnr}")
    """
    session = fetch_session(payload.session_id)

    # Validation
    if not payload.pnr_number.isdigit() or len(payload.pnr_number) != 10:
        return build_response(
            prompt    = "The PNR number you entered is not valid. A PNR must be exactly 10 digits. Please try again.",
            data      = {"session_id": payload.session_id, "pnr_entered": payload.pnr_number},
            acs_event = "invalid_pnr",
            status    = "invalid",
        )

    log_event(session, "pnr_checked", {"pnr": payload.pnr_number})

    # Mock PNR response (M3: replace with real API call)
    pnr_data = {
        "pnr_number"   : payload.pnr_number,
        "train_number" : "12951",
        "train_name"   : "Mumbai Rajdhani Express",
        "from_station" : "New Delhi (NDLS)",
        "to_station"   : "Mumbai Central (MMCT)",
        "journey_date" : "15-Jun-2025",
        "travel_class" : "Third AC (3A)",
        "booking_status": "CONFIRMED",
        "coach"        : "B-4",
        "seat_number"  : "32 — Lower Berth",
        "platform"     : "Platform 2",
        "departure"    : "16:55",
        "arrival"      : "08:35 (+1 day)",
        "passenger"    : "Adult — 1",
    }

    prompt = (
        f"PNR {payload.pnr_number} status: CONFIRMED. "
        f"Train {pnr_data['train_number']}, {pnr_data['train_name']}. "
        f"From {pnr_data['from_station']} to {pnr_data['to_station']}. "
        f"Coach {pnr_data['coach']}, Seat {pnr_data['seat_number']}. "
        f"Departure at {pnr_data['departure']} from {pnr_data['platform']}. "
        "Have a safe and pleasant journey."
    )

    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "pnr_details": pnr_data},
        acs_event = "pnr_status_delivered",
    )

# =============================================================================
# SECTION 12 — ENDPOINT 5: TICKET BOOKING
# =============================================================================

@app.post("/call/booking", summary="Ticket Booking")
def book_ticket(payload: BookingRequest):
    """
    Creates a ticket booking with the provided details.
    M3 TODO: Replace mock with real IRCTC booking API call.
    """
    session = fetch_session(payload.session_id)

    # Validate train number
    if not payload.train_number.isdigit() or len(payload.train_number) != 5:
        return build_response(
            prompt    = "Invalid train number. Please enter a 5-digit train number.",
            data      = {"session_id": payload.session_id},
            acs_event = "invalid_train",
            status    = "invalid",
        )

    log_event(session, "booking_created", {"train": payload.train_number, "class": payload.travel_class})

    # Calculate fare
    fare_per_person = BASE_FARE.get(payload.travel_class, 450)
    total_fare      = fare_per_person * payload.passenger_count
    booking_id      = f"IVR{uuid.uuid4().hex[:8].upper()}"
    travel_class    = TRAVEL_CLASS.get(payload.travel_class, "Sleeper Class (SL)")

    booking_data = {
        "booking_id"    : booking_id,
        "train_number"  : payload.train_number,
        "journey_date"  : payload.journey_date,
        "from_station"  : payload.from_station.upper(),
        "to_station"    : payload.to_station.upper(),
        "travel_class"  : travel_class,
        "passengers"    : payload.passenger_count,
        "total_fare"    : f"Rs. {total_fare}",
        "status"        : "PENDING PAYMENT",
        "payment_link"  : f"https://irctc.co.in/payment/{booking_id}",
        "expires_in"    : "15 minutes",
    }

    prompt = (
        f"Booking reference {booking_id} has been created. "
        f"Train {payload.train_number}, {travel_class}. "
        f"Total fare is Rupees {total_fare} for {payload.passenger_count} passenger. "
        "A payment link has been sent to your registered mobile number. "
        "Please complete payment within 15 minutes to confirm your booking."
    )

    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "booking": booking_data},
        acs_event = "booking_initiated",
    )

# =============================================================================
# SECTION 13 — ENDPOINT 6: TRAIN SEARCH
# =============================================================================

@app.post("/call/trains", summary="Train Search Between Stations")
def search_trains(payload: TrainSearchRequest):
    """
    Search for trains between two stations.
    M3 TODO: Replace mock with real IRCTC train search API.
    """
    session = fetch_session(payload.session_id)
    log_event(session, "train_search", {"from": payload.from_station, "to": payload.to_station})

    # Mock train list
    trains = [
        {"number": "12951", "name": "Mumbai Rajdhani",    "departs": "16:55", "arrives": "08:35+1", "duration": "15h 40m", "classes": "1A,2A,3A"},
        {"number": "12909", "name": "Garib Rath Express", "departs": "15:35", "arrives": "07:15+1", "duration": "15h 40m", "classes": "3A,CC"},
        {"number": "12927", "name": "Paschim Express",    "departs": "11:05", "arrives": "07:30+1", "duration": "20h 25m", "classes": "SL,3A,2A"},
    ]

    prompt = (
        f"Found 3 trains from {payload.from_station.upper()} to {payload.to_station.upper()}. "
        "Train 1: 12951 Mumbai Rajdhani, departs 4:55 PM, arrives 8:35 AM next day. "
        "Train 2: 12909 Garib Rath Express, departs 3:35 PM, arrives 7:15 AM next day. "
        "Train 3: 12927 Paschim Express, departs 11:05 AM, arrives 7:30 AM next day. "
        "Press 2 and enter a train number to book."
    )

    return build_response(
        prompt    = prompt,
        data      = {
            "session_id"  : payload.session_id,
            "from_station": payload.from_station.upper(),
            "to_station"  : payload.to_station.upper(),
            "trains_found": 3,
            "trains"      : trains,
        },
        acs_event = "train_list_delivered",
    )

# =============================================================================
# SECTION 14 — ENDPOINT 7: CANCELLATION
# =============================================================================

@app.post("/call/cancel", summary="Ticket Cancellation and Refund")
def cancel_ticket(payload: CancelRequest):
    """
    Cancels a ticket and calculates refund.
    M3 TODO: Replace mock with real IRCTC cancellation API.
    """
    session = fetch_session(payload.session_id)

    if not payload.pnr_number.isdigit() or len(payload.pnr_number) != 10:
        return build_response(
            prompt    = "Invalid PNR number. Please enter a valid 10-digit PNR.",
            data      = {"session_id": payload.session_id},
            acs_event = "invalid_pnr",
            status    = "invalid",
        )

    log_event(session, "cancellation_requested", {"pnr": payload.pnr_number})

    refund_id = f"REF{uuid.uuid4().hex[:6].upper()}"
    cancel_data = {
        "pnr_number"        : payload.pnr_number,
        "cancellation_status": "CANCELLED",
        "refund_amount"     : "Rs. 985",
        "refund_id"         : refund_id,
        "refund_to"         : "Original payment method",
        "processing_time"   : "5 to 7 working days",
        "tdr_filed"         : False,
    }

    prompt = (
        f"Ticket with PNR {payload.pnr_number} has been successfully cancelled. "
        f"Your refund of Rupees 985 will be credited to your original payment method "
        "within 5 to 7 working days. "
        f"Your refund reference number is {refund_id}. "
        "Thank you for using IRCTC."
    )

    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "cancellation": cancel_data},
        acs_event = "cancellation_done",
    )

# =============================================================================
# SECTION 15 — ENDPOINT 8: COMPLAINT REGISTRATION
# =============================================================================

@app.post("/call/complaint", summary="Register a Complaint")
def register_complaint(payload: ComplaintRequest):
    """
    Registers a passenger complaint and generates a ticket number.
    M3 TODO: Connect to IRCTC Rail Madad portal API.
    """
    session = fetch_session(payload.session_id)
    log_event(session, "complaint_registered", {"type": payload.complaint_type})

    complaint_labels = {"1": "Train Service", "2": "Catering", "3": "Cleanliness"}
    c_label     = complaint_labels.get(payload.complaint_type, "General")
    ticket_no   = f"CMP{uuid.uuid4().hex[:7].upper()}"

    complaint_data = {
        "complaint_ticket" : ticket_no,
        "category"         : c_label,
        "details"          : payload.complaint_details,
        "status"           : "REGISTERED",
        "resolution_time"  : "48 hours",
        "track_at"         : f"https://railmadad.indianrailways.gov.in/track/{ticket_no}",
    }

    prompt = (
        f"Your {c_label} complaint has been registered successfully. "
        f"Your complaint ticket number is {ticket_no}. "
        "You will receive a resolution within 48 hours. "
        "You can track your complaint at Rail Madad portal. "
        "Thank you for helping us improve our services."
    )

    return build_response(
        prompt    = prompt,
        data      = {"session_id": payload.session_id, "complaint": complaint_data},
        acs_event = "complaint_filed",
    )

# =============================================================================
# SECTION 16 — ENDPOINT 9: END CALL
# =============================================================================

@app.post("/call/end", summary="End Call — Session Cleanup")
def end_call(payload: EndCallRequest):
    """
    Ends the call gracefully. Marks session end time.
    Session data is retained for audit. M4: Archive to DB before deleting.
    """
    session = fetch_session(payload.session_id)
    session["call_ended_at"]  = datetime.utcnow().isoformat()
    session["current_flow"]   = "ended"
    log_event(session, "call_ended", {})

    duration_msg = "Call ended."
    prompt = (
        "Thank you for calling IRCTC Smart IVR. "
        "We hope we were able to assist you. "
        "For more services, visit www.irctc.co.in. "
        "Have a great day. Goodbye."
    )

    return build_response(
        prompt    = prompt,
        data      = {
            "session_id"    : payload.session_id,
            "call_started"  : session["call_started_at"],
            "call_ended"    : session["call_ended_at"],
            "total_events"  : len(session["event_log"]),
        },
        acs_event = "call_ended",
    )

# =============================================================================
# SECTION 17 — ACS/BAP BRIDGE STUB
# M3 TODO: Replace body with real Azure ACS SDK
# =============================================================================

@app.post("/acs/bridge", summary="ACS/BAP Connector Bridge — Milestone 3 Stub")
def acs_bridge(payload: ACSBridgeRequest):
    """
    VXML-to-ACS/BAP bridge connector stub.
    Currently returns what the real ACS SDK would receive.
    Milestone 3: replace stub body with CallAutomationClient.start_recognizing_media()
    """
    session = fetch_session(payload.session_id)

    # Map VXML events → ACS directives
    directive_map = {
        "filled"    : "USER_INPUT_RECEIVED",
        "noinput"   : "REQUEST_REPROMPT",
        "nomatch"   : "REQUEST_CLARIFICATION",
        "disconnect": "END_SESSION",
    }
    directive = directive_map.get(payload.vxml_event, "UNKNOWN_EVENT")
    log_event(session, "acs_bridge_called", {"vxml_event": payload.vxml_event, "directive": directive})

    bridge_payload = {
        "platform"             : "ACS",
        "directive"            : directive,
        "acs_call_connection_id": payload.acs_call_connection_id,
        "tts_text"             : payload.tts_text,
        "voice_name"           : "en-IN-NeerjaNeural",
        "collect_digits"       : payload.collect_digits,
        "max_digits"           : payload.max_digits,
        "language"             : session.get("language", "EN"),
        "session_context"      : session.get("booking_data", {}),
    }

    return build_response(
        prompt    = f"VXML event '{payload.vxml_event}' mapped to ACS directive '{directive}'.",
        data      = {
            "bridge_payload": bridge_payload,
            "m3_todo"       : "Replace this stub with conn.start_recognizing_media(bridge_payload)",
        },
        acs_event = directive,
    )

# =============================================================================
# SECTION 18 — SESSION INFO + HEALTH CHECK
# =============================================================================

@app.get("/session/{session_id}", summary="Inspect Session State")
def get_session_info(session_id: str):
    """Returns the full session object — useful for debugging and M3 AI layer."""
    return build_response(
        prompt    = "Session data retrieved.",
        data      = fetch_session(session_id),
        acs_event = "session_info",
    )

@app.get("/health", summary="Health Check — M4 Deployment Monitoring")
def health_check():
    """
    Lightweight health endpoint.
    M4: Hook into deployment monitoring (Azure App Insights, etc.)
    """
    return build_response(
        prompt    = "IRCTC Smart IVR Integration Layer is running.",
        data      = {
            "app_name"       : "My IRCTC Smart IVR",
            "version"        : "1.0.0",
            "milestone"      : "M2 — Integration Layer",
            "status"         : "healthy",
            "active_sessions": len(SESSIONS),
            "endpoints"      : [
                "POST /call/start",
                "POST /call/menu",
                "POST /call/key",
                "POST /call/pnr",
                "POST /call/booking",
                "POST /call/trains",
                "POST /call/cancel",
                "POST /call/complaint",
                "POST /call/end",
            ],
        },
        acs_event = "health_ok",
    )

# =============================================================================
# SECTION 19 — RUN SERVER
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("irctc_backend:app", host="0.0.0.0", port=8000, reload=True)