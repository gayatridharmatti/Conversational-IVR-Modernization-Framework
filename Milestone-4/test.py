"""
=============================================================================
FILE        : test.py
PROJECT     : IRCTC Smart IVR — Conversational IVR Modernization Framework
DESCRIPTION : 4 types of testing — 2 tests each (8 tests total)

HOW TO RUN:
    Step 1: pip install httpx==0.23.3
    Step 2: python test.py
=============================================================================
"""

import sys
import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)

from nlu_engine      import classify_intent, extract_entities
from dialog_manager  import build_menu_prompt
from speech_services import validate_stt_transcript

VALID_PNR   = "4521679834"
VALID_TRAIN = "12951"
FROM_STN    = "NDLS"
TO_STN      = "MMCT"
CALLER_ID   = "+919876543210"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def header(title):
    print(f"\n{BOLD}{CYAN}{'='*55}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*55}{RESET}")

def start_session():
    res = client.post("/call/start",
                      json={"caller_id": CALLER_ID, "language": "EN"})
    return res.json()["data"]["session_id"]


# =============================================================================
# 1. UNIT TESTS — tests individual Python functions in isolation
# =============================================================================
class UnitTests(unittest.TestCase):

    def test_unit_1_intent_cancel_beats_pnr(self):
        """Unit Test 1: 'cancel my ticket pnr 4521679834' must return cancel_ticket"""
        result = classify_intent(f"cancel my ticket pnr {VALID_PNR}")
        self.assertEqual(result["intent"], "cancel_ticket",
            "cancel_ticket must win when 'cancel' is present — not pnr_status")

    def test_unit_2_entity_pnr_extracted(self):
        """Unit Test 2: extract_entities must pull 10-digit PNR using regex"""
        entities = extract_entities(f"Check my PNR {VALID_PNR}")
        self.assertIn("PNR_NUMBER", entities)
        self.assertEqual(entities["PNR_NUMBER"], VALID_PNR)


# =============================================================================
# 2. INTEGRATION TESTS — tests two modules working together
# =============================================================================
class IntegrationTests(unittest.TestCase):

    def test_integration_1_pnr_nlu_to_endpoint(self):
        """Integration Test 1: NLU extracts PNR → /call/pnr returns CONFIRMED"""
        text     = f"check my pnr {VALID_PNR}"
        intent   = classify_intent(text)
        entities = extract_entities(text)
        self.assertEqual(intent["intent"], "pnr_status")
        self.assertEqual(entities["PNR_NUMBER"], VALID_PNR)
        sid = start_session()
        res = client.post("/call/pnr",
                          json={"session_id": sid,
                                "pnr_number": entities["PNR_NUMBER"]})
        self.assertEqual(res.status_code, 200)
        self.assertIn("CONFIRMED", res.json()["prompt"])

    def test_integration_2_cancel_nlu_to_endpoint(self):
        """Integration Test 2: NLU cancel sentence → /call/cancel returns CANCELLED"""
        text     = f"cancel my ticket pnr {VALID_PNR}"
        intent   = classify_intent(text)
        entities = extract_entities(text)
        self.assertEqual(intent["intent"], "cancel_ticket")
        self.assertEqual(entities["PNR_NUMBER"], VALID_PNR)
        sid = start_session()
        res = client.post("/call/cancel",
                          json={"session_id": sid,
                                "pnr_number": entities["PNR_NUMBER"]})
        self.assertEqual(res.status_code, 200)
        self.assertIn("CANCELLED", res.json()["prompt"])


# =============================================================================
# 3. END TO END TESTS — full user journeys from start to finish
# =============================================================================
class EndToEndTests(unittest.TestCase):

    def test_e2e_1_full_pnr_journey(self):
        """E2E Test 1: START CALL → MENU → KEY 1 → PNR CHECK → END CALL"""
        r1 = client.post("/call/start",
                         json={"caller_id": CALLER_ID, "language": "EN"})
        self.assertEqual(r1.status_code, 200)
        sid = r1.json()["data"]["session_id"]

        r2 = client.post("/call/menu", json={"session_id": sid})
        self.assertEqual(r2.status_code, 200)
        self.assertIn("1", r2.json()["prompt"])

        r3 = client.post("/call/key",
                         json={"session_id"  : sid,
                               "key_pressed" : "1",
                               "current_flow": "main_menu"})
        self.assertEqual(r3.status_code, 200)
        self.assertIn("PNR", r3.json()["prompt"])

        r4 = client.post("/call/pnr",
                         json={"session_id": sid, "pnr_number": VALID_PNR})
        self.assertEqual(r4.status_code, 200)
        self.assertIn("CONFIRMED", r4.json()["prompt"])

        r5 = client.post("/call/end", json={"session_id": sid})
        self.assertEqual(r5.status_code, 200)
        self.assertIn("Thank you", r5.json()["prompt"])

    def test_e2e_2_full_cancel_journey(self):
        """E2E Test 2: START CALL → NLU cancel → CANCEL endpoint → END CALL"""
        r1 = client.post("/call/start",
                         json={"caller_id": CALLER_ID, "language": "EN"})
        self.assertEqual(r1.status_code, 200)
        sid = r1.json()["data"]["session_id"]

        r2 = client.post("/nlu/understand",
                         json={"session_id": sid,
                               "user_text" : f"cancel my ticket pnr {VALID_PNR}",
                               "input_mode": "text"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["data"]["nlu"]["intent"], "cancel_ticket")

        r3 = client.post("/call/cancel",
                         json={"session_id": sid, "pnr_number": VALID_PNR})
        self.assertEqual(r3.status_code, 200)
        self.assertIn("CANCELLED", r3.json()["prompt"])
        self.assertIn("refund_id", r3.json()["data"]["cancellation"])

        r4 = client.post("/call/end", json={"session_id": sid})
        self.assertEqual(r4.status_code, 200)


# =============================================================================
# 4. PERFORMANCE TESTS — response time must be under 300ms per endpoint
# =============================================================================
class PerformanceTests(unittest.TestCase):

    LIMIT_MS = 300

    def _time_it(self, label, func):
        start = time.perf_counter()
        res   = func()
        ms    = (time.perf_counter() - start) * 1000
        color = GREEN if ms < self.LIMIT_MS else RED
        icon  = "✅" if ms < self.LIMIT_MS else "❌"
        print(f"    {color}{icon}{RESET}  {label:<42} {ms:>7.1f} ms")
        self.assertLess(ms, self.LIMIT_MS,
            f"{label} took {ms:.1f}ms — limit is {self.LIMIT_MS}ms")
        return res

    def test_perf_1_all_call_endpoints(self):
        """Performance Test 1: all /call/* endpoints must respond under 300ms"""
        sid = start_session()
        print()
        self._time_it("GET  /health",
            lambda: client.get("/health"))
        self._time_it("POST /call/menu",
            lambda: client.post("/call/menu",
                                json={"session_id": sid}))
        self._time_it("POST /call/key  [key=1]",
            lambda: client.post("/call/key",
                                json={"session_id"  : sid,
                                      "key_pressed" : "1",
                                      "current_flow": "main_menu"}))
        self._time_it("POST /call/pnr",
            lambda: client.post("/call/pnr",
                                json={"session_id": sid,
                                      "pnr_number": VALID_PNR}))
        self._time_it("POST /call/booking",
            lambda: client.post("/call/booking",
                                json={"session_id"     : sid,
                                      "train_number"   : VALID_TRAIN,
                                      "journey_date"   : "15 June",
                                      "from_station"   : FROM_STN,
                                      "to_station"     : TO_STN,
                                      "travel_class"   : "2",
                                      "passenger_count": 1}))
        self._time_it("POST /call/trains",
            lambda: client.post("/call/trains",
                                json={"session_id"  : sid,
                                      "from_station": FROM_STN,
                                      "to_station"  : TO_STN}))
        self._time_it("POST /call/cancel",
            lambda: client.post("/call/cancel",
                                json={"session_id": sid,
                                      "pnr_number": VALID_PNR}))
        self._time_it("POST /call/end",
            lambda: client.post("/call/end",
                                json={"session_id": sid}))

    def test_perf_2_nlu_pipeline(self):
        """Performance Test 2: 5 different NLU queries must all respond under 300ms"""
        sid = start_session()
        print()
        queries = [
            (f"check my pnr {VALID_PNR}",                          "NLU: pnr check"),
            (f"cancel my ticket pnr {VALID_PNR}",                  "NLU: cancel"),
            (f"search trains from {FROM_STN} to {TO_STN}",         "NLU: train search"),
            (f"book train {VALID_TRAIN} from {FROM_STN} to {TO_STN}", "NLU: booking"),
            ("register complaint coach is dirty",                   "NLU: complaint"),
        ]
        for text, label in queries:
            self._time_it(label,
                lambda t=text: client.post("/nlu/understand",
                                           json={"session_id": sid,
                                                 "user_text" : t,
                                                 "input_mode": "text"}))


# =============================================================================
# RUNNER
# =============================================================================
def run_section(title, test_class):
    header(title)
    suite  = unittest.TestLoader().loadTestsFromTestCase(test_class)
    total  = suite.countTestCases()
    passed = 0
    for test in suite:
        doc = (getattr(test_class, test._testMethodName).__doc__ or
               test._testMethodName).strip().split("\n")[0]
        buf = unittest.TestResult()
        unittest.TestSuite([test]).run(buf)
        if buf.wasSuccessful():
            print(f"  {GREEN}✅ PASS{RESET}  {doc}")
            passed += 1
        else:
            errs = buf.failures + buf.errors
            msg  = errs[0][1].strip().split("\n")[-1][:90] if errs else ""
            print(f"  {RED}❌ FAIL{RESET}  {doc}")
            if msg:
                print(f"         {RED}→ {msg}{RESET}")
    color = GREEN if passed == total else RED
    print(f"\n  {BOLD}{color}Result: {passed}/{total} passed{RESET}")
    return passed, total


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    print(f"\n{BOLD}{'='*55}")
    print(f"  IRCTC Smart IVR — Test Suite  (2 tests per section)")
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M:%S')}")
    print(f"{'='*55}{RESET}")

    sections = [
        ("1. UNIT TESTS         — Individual function tests",  UnitTests),
        ("2. INTEGRATION TESTS  — Module chain tests",         IntegrationTests),
        ("3. END TO END TESTS   — Complete journey tests",     EndToEndTests),
        ("4. PERFORMANCE TESTS  — Response time tests",        PerformanceTests),
    ]

    key_map = {"unit": 0, "integration": 1, "e2e": 2, "performance": 3}

    if arg == "all":
        to_run = sections
    elif arg in key_map:
        to_run = [sections[key_map[arg]]]
    else:
        print(f"{RED}Use: unit | integration | e2e | performance | all{RESET}")
        sys.exit(1)

    tp, ta = 0, 0
    for title, cls in to_run:
        p, t = run_section(title, cls)
        tp += p; ta += t

    print(f"\n{BOLD}{'='*55}")
    color = GREEN if tp == ta else RED
    print(f"  {color}FINAL: {tp}/{ta} tests passed{RESET}{BOLD}")
    print(f"  {GREEN}🎉 All tests passed!{RESET}" if tp == ta
          else f"  {RED}⚠  {ta-tp} test(s) failed{RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")