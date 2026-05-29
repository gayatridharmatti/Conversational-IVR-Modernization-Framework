"""
=============================================================================
FILE        : nlu_engine.py
PROJECT     : IRCTC Smart IVR — Conversational IVR Modernization Framework
MODULE      : Module 3 — Conversational AI Interface Development
DESCRIPTION : NLU Engine — Intent Recognizer + Entity Extractor
              Contains:
                - INTENT_CONFIG   : 9 intents with keywords, phrases, examples
                - ENTITY_PATTERNS : 7 compiled regex patterns
                - classify_intent(): rule-based intent classifier
                - extract_entities(): regex-based entity extractor
=============================================================================
"""

import re

# =============================================================================
# INTENT CONFIGURATION
# Each intent has:
#   keywords  → individual words that hint at this intent
#   phrases   → exact multi-word phrases → high confidence (0.95) if matched
#   examples  → shown in /nlu/debug-intent for documentation
# =============================================================================
INTENT_CONFIG = {

    "pnr_status": {
        "keywords": ["pnr", "status", "ticket", "booking", "confirm", "confirmed",
                     "berth", "seat", "coach", "reservation"],
        "phrases" : ["check pnr", "pnr status", "my booking", "check my ticket",
                     "is my ticket confirmed", "booking status", "check reservation",
                     "where is my seat", "what is my berth"],
        "examples": ["Check my PNR", "Is my ticket confirmed?", "What is my berth number?"],
    },

    "book_ticket": {
        "keywords": ["book", "booking", "reserve", "reservation", "ticket",
                     "journey", "travel", "buy", "purchase"],
        "phrases" : ["book ticket", "book a train", "i want to travel", "reserve seat",
                     "want to book", "need a ticket", "book train ticket",
                     "how to book", "train booking"],
        "examples": ["Book a ticket", "I want to travel to Mumbai", "Reserve a seat"],
    },

    "search_trains": {
        "keywords": ["train", "trains", "search", "find", "available", "running",
                     "route", "between", "from", "which train"],
        "phrases" : ["search trains", "find train", "trains from", "trains between",
                     "which trains go", "available trains", "trains to delhi",
                     "trains to mumbai", "show trains"],
        "examples": ["Search trains from Delhi to Mumbai", "Which trains are available?"],
    },

    "cancel_ticket": {
        "keywords": ["cancel", "cancellation", "refund", "money back", "cancelled",
                     "withdraw", "revoke", "cancelling"],
        "phrases" : ["cancel ticket", "cancel my booking", "want to cancel",
                     "need a refund", "get my money back", "cancel reservation",
                     "how to cancel", "cancel my ticket",
                     "cancel pnr", "cancel my ticket pnr",
                     "i want to cancel", "please cancel"],
        "examples": ["Cancel my ticket", "I need a refund", "Cancel my booking"],
    },

    "complaint": {
        "keywords": ["complaint", "complain", "problem", "issue", "dirty",
                     "food", "catering", "cleanliness", "bad service", "late",
                     "delay", "report"],
        "phrases" : ["register complaint", "file a complaint", "i want to complain",
                     "there is a problem", "train was dirty", "bad food",
                     "coach is dirty", "report a problem"],
        "examples": ["Register a complaint", "The coach is dirty", "Bad catering service"],
    },

    "train_status": {
        "keywords": ["live", "running", "where", "location", "track", "tracking",
                     "arrived", "delayed", "on time", "platform", "current"],
        "phrases" : ["where is my train", "live status", "track train",
                     "is train on time", "train running status", "current location",
                     "train arrived", "train delayed", "which platform"],
        "examples": ["Where is train 12951?", "Is the train on time?", "Track my train"],
    },

    "talk_to_agent": {
        "keywords": ["agent", "human", "person", "operator", "help",
                     "representative", "staff", "support", "customer care"],
        "phrases" : ["talk to agent", "speak to human", "connect to person",
                     "need help", "talk to someone", "customer support",
                     "human agent", "real person"],
        "examples": ["Talk to an agent", "Connect me to a human", "Need help"],
    },

    "greeting": {
        "keywords": ["hello", "hi", "hey", "good morning", "good afternoon",
                     "good evening", "namaste", "helo", "hii"],
        "phrases" : ["hello irctc", "hi there", "good morning", "namaste"],
        "examples": ["Hello", "Hi", "Good morning"],
    },

    "goodbye": {
        "keywords": ["bye", "goodbye", "exit", "quit", "end", "stop",
                     "disconnect", "hang up", "done", "finish", "no thanks"],
        "phrases" : ["end call", "hang up", "goodbye", "i am done", "no more help",
                     "that is all", "bye bye"],
        "examples": ["Goodbye", "End the call", "I'm done"],
    },

    "repeat": {
        "keywords": ["repeat", "again", "say again", "pardon", "what",
                     "didnt hear", "didn't hear", "once more", "come again"],
        "phrases" : ["say that again", "repeat please", "i didn't understand",
                     "what did you say", "can you repeat"],
        "examples": ["Can you repeat that?", "Say that again"],
    },
}

# =============================================================================
# REGEX ENTITY PATTERNS
# Each pattern extracts one type of structured entity from raw text
# =============================================================================
ENTITY_PATTERNS = {

    # PNR: exactly 10 consecutive digits
    "PNR_NUMBER": re.compile(
        r'\b(\d{10})\b'
    ),

    # Train number: exactly 5 digits
    "TRAIN_NUMBER": re.compile(
        r'\b(\d{5})\b'
    ),

    # Date: "15 June", "june 15", "15/06/2025", "15-06-2025", "tomorrow", "today"
    "DATE": re.compile(
        r'\b(\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?'
        r'|\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?'
        r'|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?'
        r'|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?'
        r'|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?'
        r'|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}'
        r'|today|tomorrow|day after tomorrow)\b',
        re.IGNORECASE
    ),

    # Travel class in natural language
    "TRAVEL_CLASS": re.compile(
        r'\b(sleeper|sl|third\s*ac|3a|3ac|second\s*ac|2a|2ac'
        r'|first\s*ac|1a|1ac|chair\s*car|cc|ac\s*chair)\b',
        re.IGNORECASE
    ),

    # Complaint type keywords
    "COMPLAINT_TYPE": re.compile(
        r'\b(food|catering|dirty|cleanliness|clean|service|delay|late|staff)\b',
        re.IGNORECASE
    ),

    # Passenger count: "2 tickets", "for 3 people", "two passengers"
    "PASSENGER_COUNT": re.compile(
        r'\b(one|two|three|four|five|[1-5])\s*(?:ticket|passenger|person|people|seat)s?\b',
        re.IGNORECASE
    ),
}

# Word → number map for passenger count
WORD_TO_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

# Travel class label → code
CLASS_LABEL_MAP = {
    "sleeper": "1", "sl": "1",
    "third ac": "2", "3a": "2", "3ac": "2",
    "second ac": "3", "2a": "3", "2ac": "3",
    "first ac": "4", "1a": "4", "1ac": "4",
    "chair car": "5", "cc": "5", "ac chair": "5",
}

# Complaint keyword → type code
COMPLAINT_TYPE_MAP = {
    "food": "2", "catering": "2",
    "dirty": "3", "cleanliness": "3", "clean": "3",
    "service": "1", "delay": "1", "late": "1", "staff": "1",
}

# Confidence threshold — scores below this are treated as unknown
CONFIDENCE_THRESHOLD = 0.15


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================
def classify_intent(text: str) -> dict:
    """
    Rule-based intent classifier.

    Pipeline:
      Step 1 — Normalize text (lowercase, strip punctuation)
      Step 2 — Exact phrase match       → confidence 0.95
      Step 3 — Keyword scoring          → confidence = hits/total + hits*0.08
      Step 4 — Pick highest score       → if > threshold, return; else unknown

    Returns:
        {
            "intent"    : "pnr_status",
            "confidence": 0.95,
            "method"    : "phrase_match" | "keyword_score" | "unknown",
            "matched_on": ["check pnr"],
            "all_scores": { ... }
        }
    """
    # Step 1 — Normalize
    normalized = text.lower().strip()
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    words      = set(normalized.split())

    # Step 2 — Exact phrase match
    for intent_name, cfg in INTENT_CONFIG.items():
        for phrase in cfg["phrases"]:
            if phrase in normalized:
                return {
                    "intent"    : intent_name,
                    "confidence": 0.95,
                    "method"    : "phrase_match",
                    "matched_on": [phrase],
                    "all_scores": {intent_name: 0.95},
                }

    # Step 2B — Cancel override
    # If the text contains "cancel" in any form, always classify as cancel_ticket
    # before keyword scoring can misfire towards pnr_status or book_ticket
    cancel_triggers = ["cancel", "cancellation", "cancelling", "refund",
                       "money back", "withdraw", "revoke"]
    if any(word in words or word in normalized for word in cancel_triggers):
        return {
            "intent"    : "cancel_ticket",
            "confidence": 0.90,
            "method"    : "cancel_override",
            "matched_on": [w for w in cancel_triggers if w in normalized],
            "all_scores": {"cancel_ticket": 0.90},
        }

    # Step 3 — Keyword scoring
    scores           = {}
    matched_keywords = {}
    for intent_name, cfg in INTENT_CONFIG.items():
        kw_list = cfg["keywords"]
        hits    = [kw for kw in kw_list if kw in normalized or kw in words]
        if hits:
            score                         = min(0.90, len(hits) / len(kw_list) + len(hits) * 0.08)
            scores[intent_name]           = round(score, 3)
            matched_keywords[intent_name] = hits

    # Step 4 — Pick best
    if scores:
        best_intent = max(scores, key=scores.get)
        best_score  = scores[best_intent]
        if best_score >= CONFIDENCE_THRESHOLD:
            return {
                "intent"    : best_intent,
                "confidence": best_score,
                "method"    : "keyword_score",
                "matched_on": matched_keywords.get(best_intent, []),
                "all_scores": scores,
            }

    # Fallback
    return {
        "intent"    : "unknown",
        "confidence": 0.0,
        "method"    : "unknown",
        "matched_on": [],
        "all_scores": scores,
    }


# =============================================================================
# ENTITY EXTRACTOR
# =============================================================================
def extract_entities(text: str) -> dict:
    """
    Regex-based named entity extractor.

    Extracts:
        PNR_NUMBER      — 10-digit number
        TRAIN_NUMBER    — 5-digit number
        DATE            — various date formats + today/tomorrow
        FROM_STATION    — station code after "from"
        TO_STATION      — station code after "to"
        TRAVEL_CLASS    — sleeper / 3a / second ac etc. (normalized to code)
        PASSENGER_COUNT — word/digit + ticket/passenger/person
        COMPLAINT_TYPE  — food/catering/dirty/cleanliness/delay

    Returns only keys that were actually found.
    """
    entities   = {}
    lower_text = text.lower()

    # PNR Number
    pnr_match = ENTITY_PATTERNS["PNR_NUMBER"].search(text)
    if pnr_match:
        entities["PNR_NUMBER"] = pnr_match.group(1)

    # Train Number (avoid grabbing first 5 digits of a PNR)
    train_match = ENTITY_PATTERNS["TRAIN_NUMBER"].search(text)
    if train_match:
        num = train_match.group(1)
        if "PNR_NUMBER" not in entities or num != entities["PNR_NUMBER"][:5]:
            entities["TRAIN_NUMBER"] = num

    # Date
    date_match = ENTITY_PATTERNS["DATE"].search(text)
    if date_match:
        entities["DATE"] = date_match.group(1)

    # From / To station codes
    from_match = re.search(r'\b(?:from|departure|origin)\s+([A-Za-z]{2,5})\b',  text, re.IGNORECASE)
    to_match   = re.search(r'\b(?:to|destination|arrive|arrival)\s+([A-Za-z]{2,5})\b', text, re.IGNORECASE)
    if from_match:
        entities["FROM_STATION"] = from_match.group(1).upper()
    if to_match:
        entities["TO_STATION"] = to_match.group(1).upper()

    # Travel class → normalize to code
    class_match = ENTITY_PATTERNS["TRAVEL_CLASS"].search(lower_text)
    if class_match:
        raw = re.sub(r'\s+', ' ', class_match.group(1).strip().lower())
        entities["TRAVEL_CLASS"] = CLASS_LABEL_MAP.get(raw, raw)

    # Passenger count → normalize to integer
    pax_match = ENTITY_PATTERNS["PASSENGER_COUNT"].search(lower_text)
    if pax_match:
        raw   = pax_match.group(1).lower()
        count = WORD_TO_NUM.get(raw) or (int(raw) if raw.isdigit() else None)
        if count:
            entities["PASSENGER_COUNT"] = count

    # Complaint type → normalize to code
    c_match = ENTITY_PATTERNS["COMPLAINT_TYPE"].search(lower_text)
    if c_match:
        entities["COMPLAINT_TYPE"] = COMPLAINT_TYPE_MAP.get(c_match.group(1).lower(), "1")

    return entities