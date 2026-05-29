"""
=============================================================================
FILE        : dialog_manager.py
PROJECT     : IRCTC Smart IVR — Conversational IVR Modernization Framework
MODULE      : Module 3 — Conversational AI Interface Development
DESCRIPTION : Dialogue Manager — maps NLU intent + entities → action/response
              Takes classified intent and extracted entities, decides:
                - What prompt to speak back (TTS text)
                - Which M2 endpoint to call (if any)
                - What data is still missing (follow-up questions)
                - What ACS/BAP event to fire (Milestone 4 hook)
=============================================================================
"""

from datetime import datetime


# =============================================================================
# HELPER — greeting based on IST time
# =============================================================================
def get_greeting() -> str:
    hour = (datetime.utcnow().hour + 5) % 24
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def handle_train_selection(train_number: str, session: dict) -> dict:
    """
    Called when user types just a train number after seeing search results.
    Uses the saved from_station / to_station from session booking_data.
    Directly calls /call/booking with defaults.
    """
    sid  = session["session_id"]
    data = session.get("booking_data", {})
    from_stn = data.get("from_station", "NDLS")
    to_stn   = data.get("to_station",   "MMCT")
    date     = data.get("journey_date", "15 June")

    # Clear the awaiting flag
    session["booking_data"]["awaiting_train_selection"] = False

    return {
        "prompt"   : (
            f"Great choice! Booking your ticket on train {train_number} "
            f"from {from_stn} to {to_stn}. Please wait."
        ),
        "action"   : "call_endpoint",
        "endpoint" : "/call/booking",
        "payload"  : {
            "session_id"     : sid,
            "train_number"   : train_number,
            "journey_date"   : date,
            "from_station"   : from_stn,
            "to_station"     : to_stn,
            "travel_class"   : "2",   # default Third AC
            "passenger_count": 1,
        },
        "missing"  : [],
        "follow_up": None,
        "acs_event": "ivr_booking_flow",
    }


def build_menu_prompt() -> str:
    return (
        "Main Menu. "
        "Press 1 or say PNR Status. "
        "Press 2 or say Ticket Booking. "
        "Press 3 or say Train Search. "
        "Press 4 or say Cancel Ticket. "
        "Press 5 or say Register Complaint. "
        "Press 6 or say Talk to Agent. "
        "Press 0 or say Repeat to hear this again."
    )


# =============================================================================
# DIALOGUE MANAGER
# =============================================================================
def dialogue_manager(intent: str, entities: dict, session: dict) -> dict:
    """
    Core dialogue manager.

    Inputs:
        intent   — classified intent string from nlu_engine.classify_intent()
        entities — extracted entity dict from nlu_engine.extract_entities()
        session  — active session dict (for session_id and booking_data)

    Returns a dialogue dict:
        {
            "prompt"    : str,   — TTS text to speak back to user
            "action"    : str,   — "call_endpoint" | "collect_entity" |
                                   "respond" | "transfer" | "end_call" | "clarify"
            "endpoint"  : str,   — M2 endpoint path or None
            "payload"   : dict,  — request body for the endpoint
            "missing"   : list,  — entity names still needed
            "follow_up" : str,   — next question to ask user
            "acs_event" : str,   — ACS/BAP trigger name (Milestone 4 hook)
        }
    """
    sid = session["session_id"]

    # ── GREETING ─────────────────────────────────────────────────────────────
    if intent == "greeting":
        return {
            "prompt"   : (
                f"{get_greeting()}! Welcome to IRCTC Smart IVR. "
                "How can I help you today? You can say: "
                "Check PNR Status, Book a Ticket, Search Trains, "
                "Cancel Ticket, or Register a Complaint."
            ),
            "action"   : "respond",
            "endpoint" : None,
            "payload"  : {},
            "missing"  : [],
            "follow_up": None,
            "acs_event": "greeting_response",
        }

    # ── GOODBYE ───────────────────────────────────────────────────────────────
    if intent == "goodbye":
        return {
            "prompt"   : (
                "Thank you for using IRCTC Smart IVR. "
                "Have a safe journey. Goodbye!"
            ),
            "action"   : "end_call",
            "endpoint" : "/call/end",
            "payload"  : {"session_id": sid},
            "missing"  : [],
            "follow_up": None,
            "acs_event": "call_ended",
        }

    # ── REPEAT MENU ───────────────────────────────────────────────────────────
    if intent == "repeat":
        return {
            "prompt"   : build_menu_prompt(),
            "action"   : "respond",
            "endpoint" : None,
            "payload"  : {},
            "missing"  : [],
            "follow_up": None,
            "acs_event": "menu_repeated",
        }

    # ── PNR STATUS ────────────────────────────────────────────────────────────
    if intent == "pnr_status":
        if "PNR_NUMBER" in entities:
            return {
                "prompt"   : f"Checking PNR status for {entities['PNR_NUMBER']}. Please wait.",
                "action"   : "call_endpoint",
                "endpoint" : "/call/pnr",
                "payload"  : {
                    "session_id": sid,
                    "pnr_number": entities["PNR_NUMBER"],
                },
                "missing"  : [],
                "follow_up": None,
                "acs_event": "ivr_pnr_flow",
            }
        return {
            "prompt"   : "I can check your PNR status. Please say or type your 10-digit PNR number.",
            "action"   : "collect_entity",
            "endpoint" : "/call/pnr",
            "payload"  : {},
            "missing"  : ["PNR_NUMBER"],
            "follow_up": "Please say your 10-digit PNR number.",
            "acs_event": "ivr_pnr_flow",
        }

    # ── TICKET BOOKING ────────────────────────────────────────────────────────
    if intent == "book_ticket":
        missing = []
        payload = {
            "session_id"     : sid,
            "passenger_count": entities.get("PASSENGER_COUNT", 1),
            "travel_class"   : entities.get("TRAVEL_CLASS", "2"),  # default Third AC
        }

        if "TRAIN_NUMBER" in entities:
            payload["train_number"] = entities["TRAIN_NUMBER"]
        else:
            missing.append("TRAIN_NUMBER")

        if "FROM_STATION" in entities:
            payload["from_station"] = entities["FROM_STATION"]
        else:
            missing.append("FROM_STATION")

        if "TO_STATION" in entities:
            payload["to_station"] = entities["TO_STATION"]
        else:
            missing.append("TO_STATION")

        if "DATE" in entities:
            payload["journey_date"] = entities["DATE"]
        else:
            missing.append("DATE")

        # All entities present — proceed to booking
        if not missing:
            return {
                "prompt"   : (
                    f"Booking your ticket on train {payload['train_number']} "
                    f"from {payload['from_station']} to {payload['to_station']}. "
                    "Please wait."
                ),
                "action"   : "call_endpoint",
                "endpoint" : "/call/booking",
                "payload"  : payload,
                "missing"  : [],
                "follow_up": None,
                "acs_event": "ivr_booking_flow",
            }

        # Ask for first missing entity
        follow_up_map = {
            "TRAIN_NUMBER": "What is the 5-digit train number?",
            "FROM_STATION": "What is your departure station code? For example, NDLS for New Delhi.",
            "TO_STATION"  : "What is your destination station code? For example, MMCT for Mumbai.",
            "DATE"        : "What is your journey date? For example, 15 June.",
        }
        next_q = follow_up_map.get(missing[0], "Please provide more details.")
        return {
            "prompt"   : f"I can book a ticket for you. {next_q}",
            "action"   : "collect_entity",
            "endpoint" : "/call/booking",
            "payload"  : payload,
            "missing"  : missing,
            "follow_up": next_q,
            "acs_event": "ivr_booking_flow",
        }

    # ── TRAIN SEARCH ──────────────────────────────────────────────────────────
    if intent == "search_trains":
        if "FROM_STATION" in entities and "TO_STATION" in entities:
            # Save search context in session so next input can book directly
            session["booking_data"]["awaiting_train_selection"] = True
            session["booking_data"]["from_station"] = entities["FROM_STATION"]
            session["booking_data"]["to_station"]   = entities["TO_STATION"]
            if "DATE" in entities:
                session["booking_data"]["journey_date"] = entities["DATE"]
            return {
                "prompt"   : (
                    f"Searching trains from {entities['FROM_STATION']} "
                    f"to {entities['TO_STATION']}. Please wait."
                ),
                "action"   : "call_endpoint",
                "endpoint" : "/call/trains",
                "payload"  : {
                    "session_id"  : sid,
                    "from_station": entities["FROM_STATION"],
                    "to_station"  : entities["TO_STATION"],
                    "journey_date": entities.get("DATE"),
                },
                "missing"  : [],
                "follow_up": None,
                "acs_event": "ivr_search_flow",
            }
        if "FROM_STATION" in entities:
            return {
                "prompt"   : f"Trains from {entities['FROM_STATION']}. Where do you want to go?",
                "action"   : "collect_entity",
                "endpoint" : "/call/trains",
                "payload"  : {"session_id": sid, "from_station": entities["FROM_STATION"]},
                "missing"  : ["TO_STATION"],
                "follow_up": "What is your destination station?",
                "acs_event": "ivr_search_flow",
            }
        return {
            "prompt"   : "I can search trains for you. What is your departure station?",
            "action"   : "collect_entity",
            "endpoint" : "/call/trains",
            "payload"  : {"session_id": sid},
            "missing"  : ["FROM_STATION", "TO_STATION"],
            "follow_up": "What is your departure station code?",
            "acs_event": "ivr_search_flow",
        }

    # ── CANCEL TICKET ─────────────────────────────────────────────────────────
    if intent == "cancel_ticket":
        if "PNR_NUMBER" in entities:
            pnr = entities["PNR_NUMBER"]
            return {
                "prompt"   : (
                    f"Processing cancellation for PNR {pnr}. "
                    "Fetching your booking details. Please wait."
                ),
                "action"   : "call_endpoint",
                "endpoint" : "/call/cancel",
                "payload"  : {
                    "session_id": sid,
                    "pnr_number": pnr,
                },
                "missing"  : [],
                "follow_up": None,
                "acs_event": "ivr_cancel_flow",
            }
        # No PNR — ask for it
        return {
            "prompt"   : (
                "I can cancel your ticket. "
                "Please type or say your 10-digit PNR number."
            ),
            "action"   : "collect_entity",
            "endpoint" : "/call/cancel",
            "payload"  : {},
            "missing"  : ["PNR_NUMBER"],
            "follow_up": "Please say your 10-digit PNR number.",
            "acs_event": "ivr_cancel_flow",
        }

    # ── COMPLAINT ─────────────────────────────────────────────────────────────
    if intent == "complaint":
        c_type = entities.get("COMPLAINT_TYPE", "1")
        return {
            "prompt"   : (
                "I will register your complaint right away. "
                "Your complaint has been noted and will be resolved within 48 hours."
            ),
            "action"   : "call_endpoint",
            "endpoint" : "/call/complaint",
            "payload"  : {
                "session_id"      : sid,
                "complaint_type"  : c_type,
                "complaint_details": "Reported via voice or text input",
            },
            "missing"  : [],
            "follow_up": None,
            "acs_event": "ivr_complaint_flow",
        }

    # ── TRAIN STATUS ──────────────────────────────────────────────────────────
    if intent == "train_status":
        return {
            "prompt"   : (
                "For live train tracking, you can search trains using option 3, "
                "or check the IRCTC Rail Connect app for real-time status."
            ),
            "action"   : "respond",
            "endpoint" : None,
            "payload"  : {},
            "missing"  : [],
            "follow_up": None,
            "acs_event": "ivr_search_flow",
        }

    # ── TALK TO AGENT ─────────────────────────────────────────────────────────
    if intent == "talk_to_agent":
        return {
            "prompt"   : (
                "Connecting you to an IRCTC support agent. "
                "Please hold. Estimated wait time is 3 minutes."
            ),
            "action"   : "transfer",
            "endpoint" : None,
            "payload"  : {"transfer_queue": "irctc_general_support"},
            "missing"  : [],
            "follow_up": None,
            "acs_event": "ivr_agent_transfer",
        }

    # ── UNKNOWN / FALLBACK ────────────────────────────────────────────────────
    return {
        "prompt"   : (
            "I'm sorry, I didn't quite understand that. "
            "You can say things like: Check PNR Status, Book a Ticket, "
            "Search Trains, Cancel my Booking, or Register a Complaint. "
            "How can I help you?"
        ),
        "action"   : "clarify",
        "endpoint" : None,
        "payload"  : {},
        "missing"  : [],
        "follow_up": "How can I help you?",
        "acs_event": "nlu_fallback",
    }