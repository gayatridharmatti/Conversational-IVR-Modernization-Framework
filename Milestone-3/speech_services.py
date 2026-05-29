"""
=============================================================================
FILE        : speech_services.py
PROJECT     : IRCTC Smart IVR — Conversational IVR Modernization Framework
MODULE      : Module 3 — Conversational AI Interface Development
DESCRIPTION : Speech Services — Text-to-Speech (TTS) + Speech-to-Text (STT)
              Provides:
                - TTS_CONFIG     : default voice settings for browser TTS
                - get_tts_config(): returns TTS payload for a given text
                - validate_stt() : validates and normalises STT transcript

              HOW TTS WORKS (Web Speech API — browser-side):
                Backend returns tts_config dict in every response.
                Browser runs:
                  const utt  = new SpeechSynthesisUtterance(tts_config.text)
                  utt.lang   = tts_config.lang      // "en-IN"
                  utt.rate   = tts_config.rate       // 0.92
                  utt.pitch  = tts_config.pitch      // 1.0
                  utt.volume = tts_config.volume     // 1.0
                  window.speechSynthesis.speak(utt)

              HOW STT WORKS (Web Speech API — browser-side):
                Browser runs SpeechRecognition → gets transcript text
                Sends transcript to POST /nlu/stt-result
                Backend pipes it through /nlu/understand

              MILESTONE 4 UPGRADE:
                Replace browser TTS with Azure Neural TTS:
                  from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer
                  config = SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
                  config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
=============================================================================
"""

from datetime import datetime

# =============================================================================
# TTS DEFAULT CONFIGURATION
# These settings are sent in every API response so the browser can speak
# =============================================================================
TTS_CONFIG = {
    "lang": "en-IN",  # Indian English locale
    "rate": 0.92,  # Slightly slower for IVR clarity
    "pitch": 1.0,  # Natural pitch
    "volume": 1.0,  # Full volume
    "voice": "en-IN-NeerjaNeural",  # Preferred Azure Neural voice (M4 upgrade)
}

# STT configuration returned to browser
STT_CONFIG = {
    "lang": "en-IN",  # Recognition language
    "continuous": False,  # Stop after first utterance
    "interimResults": True,  # Show live transcript while speaking
    "maxAlternatives": 1,  # Return best result only
}


# =============================================================================
# TTS HELPER FUNCTIONS
# =============================================================================

def get_tts_config(text: str, lang: str = "en-IN",
                   rate: float = 0.92, pitch: float = 1.0,
                   volume: float = 1.0) -> dict:
    """
    Returns the TTS configuration dict for a given text.
    Included in every API response under the 'tts_config' key.

    Args:
        text   : The text string to be spoken aloud
        lang   : BCP-47 language tag (default: en-IN for Indian English)
        rate   : Speech rate (0.1 – 10, default 0.92)
        pitch  : Voice pitch (0 – 2, default 1.0)
        volume : Volume level (0 – 1, default 1.0)

    Returns:
        dict with all TTS parameters ready for SpeechSynthesisUtterance
    """
    return {
        "text": text,
        "lang": lang,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "voice": TTS_CONFIG["voice"],
    }


def build_tts_response(text: str) -> dict:
    """
    Builds the full TTS speak response returned by POST /nlu/tts-speak.

    Returns:
        {
            "status"    : "success",
            "timestamp" : "...",
            "tts_action": "speak",
            "tts_config": { text, lang, rate, pitch, volume },
            "note"      : "Pass to SpeechSynthesisUtterance"
        }
    """
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "tts_action": "speak",
        "tts_config": get_tts_config(text),
        "note": (
            "Pass tts_config to browser SpeechSynthesisUtterance: "
            "const utt = new SpeechSynthesisUtterance(tts_config.text); "
            "utt.lang = tts_config.lang; window.speechSynthesis.speak(utt);"
        ),
    }


# =============================================================================
# STT HELPER FUNCTIONS
# =============================================================================

def get_stt_config() -> dict:
    """
    Returns the STT configuration dict for the browser SpeechRecognition API.
    Sent to the frontend on session start so it knows how to configure the mic.
    """
    return STT_CONFIG.copy()


def validate_stt_transcript(transcript: str, confidence: float = 1.0) -> dict:
    """
    Validates and normalises an incoming STT transcript.

    Checks:
        - Transcript is not empty
        - Transcript is not just whitespace
        - Confidence is above minimum threshold (0.3)

    Returns:
        {
            "valid"     : True | False,
            "transcript": "cleaned transcript text",
            "confidence": 0.87,
            "reason"    : "ok" | "empty" | "low_confidence" | "whitespace_only"
        }
    """
    MIN_CONFIDENCE = 0.30

    if not transcript or not transcript.strip():
        return {
            "valid": False,
            "transcript": "",
            "confidence": confidence,
            "reason": "empty",
        }

    if confidence < MIN_CONFIDENCE:
        return {
            "valid": False,
            "transcript": transcript.strip(),
            "confidence": confidence,
            "reason": "low_confidence",
        }

    # Normalise: strip extra spaces, collapse multiple spaces
    cleaned = " ".join(transcript.strip().split())

    return {
        "valid": True,
        "transcript": cleaned,
        "confidence": confidence,
        "reason": "ok",
    }


# =============================================================================
# SPEECH SERVICE STATUS
# =============================================================================

def get_speech_service_info() -> dict:
    """
    Returns information about the speech services configuration.
    Used by the /health endpoint to report speech service status.
    """
    return {
        "tts": {
            "provider": "Browser Web Speech API (SpeechSynthesis)",
            "language": TTS_CONFIG["lang"],
            "voice": TTS_CONFIG["voice"],
            "rate": TTS_CONFIG["rate"],
            "m4_upgrade": "Azure Cognitive Services Neural TTS",
        },
        "stt": {
            "provider": "Browser Web Speech API (SpeechRecognition)",
            "language": STT_CONFIG["lang"],
            "continuous": STT_CONFIG["continuous"],
            "m4_upgrade": "Azure Cognitive Services Speech-to-Text",
        },
    }
