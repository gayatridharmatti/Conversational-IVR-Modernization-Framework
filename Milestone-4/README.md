# 🧪 Milestone 4 — Testing and Deployment
### IRCTC Smart IVR System · Module 4

---

## 🎯 Objective

Final validation and production deployment of the IRCTC Smart IVR system. This milestone covers all 4 types of software testing and the full deployment process on Render.com.

---

## 🧪 Testing — `test.py`

### How to Run

```bash
# Install test dependency
pip install httpx==0.23.3

# Run all 8 tests
python test.py

# Run one section at a time
python test.py unit
python test.py integration
python test.py e2e
python test.py performance
```

### Expected Output

```
=======================================================
  IRCTC Smart IVR — Test Suite  (2 tests per section)
  01 Jun 2025  10:30:00
=======================================================

  1. UNIT TESTS — Individual function tests
  ✅ PASS  Unit Test 1: cancel my ticket must return cancel_ticket
  ✅ PASS  Unit Test 2: extract_entities must pull 10-digit PNR

  Result: 2/2 passed

  4. PERFORMANCE TESTS — Response time tests
    ✅  GET  /health                        2.1 ms
    ✅  POST /call/pnr                      8.4 ms
    ✅  NLU: cancel                         6.2 ms

  FINAL: 8/8 tests passed
  🎉 All tests passed!
```

---

## 1️⃣ Unit Testing

Tests individual Python functions in complete isolation. No HTTP calls — pure function input/output.

**Test 1 — Intent Cancel Override:**
```python
result = classify_intent("cancel my ticket pnr 4521679834")
assert result["intent"] == "cancel_ticket"
# Verifies cancel_ticket wins over pnr_status when "cancel" is present
```

**Test 2 — Entity PNR Extraction:**
```python
entities = extract_entities("Check my PNR 4521679834")
assert entities["PNR_NUMBER"] == "4521679834"
# Verifies regex pattern \b(\d{10})\b correctly extracts 10-digit PNR
```

**Why these two:**
- Test 1 covers the most critical NLU rule — the cancel override that was fixed after a real bug
- Test 2 covers the core entity extraction capability that every service depends on

---

## 2️⃣ Integration Testing

Tests two or more modules working together as a chain. Checks that output of one module correctly feeds into another.

**Test 1 — PNR: NLU → Endpoint:**
```
classify_intent("check my pnr 4521679834")  → intent: pnr_status ✅
extract_entities("check my pnr 4521679834") → PNR_NUMBER: 4521679834 ✅
POST /call/pnr with extracted PNR           → response contains "CONFIRMED" ✅
```

**Test 2 — Cancel: NLU → Endpoint:**
```
classify_intent("cancel my ticket pnr 4521679834") → intent: cancel_ticket ✅
extract_entities(...)                               → PNR_NUMBER: 4521679834 ✅
POST /call/cancel with extracted PNR               → response contains "CANCELLED" ✅
```

**Why these two:**
- Verifies the full NLU pipeline works end-to-end through the module chain
- Test 2 specifically validates the cancel override bug fix works in integration context

---

## 3️⃣ End to End Testing

Tests complete user journeys from the very first step to the last. No mocking — real endpoints, real logic, real responses. Simulates exactly what the browser does.

**Test 1 — Full PNR Journey:**

| Step | Action | Expected |
|---|---|---|
| 1 | `POST /call/start` | Status 200, session_id returned |
| 2 | `POST /call/menu` | Status 200, prompt contains "1" |
| 3 | `POST /call/key` key=1 | Status 200, prompt contains "PNR" |
| 4 | `POST /call/pnr` | Status 200, prompt contains "CONFIRMED" |
| 5 | `POST /call/end` | Status 200, prompt contains "Thank you" |

**Test 2 — Full Cancel Journey:**

| Step | Action | Expected |
|---|---|---|
| 1 | `POST /call/start` | Session created |
| 2 | `POST /nlu/understand` "cancel my ticket pnr 4521679834" | intent = cancel_ticket |
| 3 | `POST /call/cancel` | prompt contains "CANCELLED", refund_id present |
| 4 | `POST /call/end` | Session closed cleanly |

---

## 4️⃣ Performance Testing

Measures how fast every endpoint responds. All must complete under **300ms**.

**Test 1 — All call endpoints timed:**

| Endpoint | Expected |
|---|---|
| `GET /health` | < 300ms |
| `POST /call/menu` | < 300ms |
| `POST /call/key` | < 300ms |
| `POST /call/pnr` | < 300ms |
| `POST /call/booking` | < 300ms |
| `POST /call/trains` | < 300ms |
| `POST /call/cancel` | < 300ms |
| `POST /call/end` | < 300ms |

**Test 2 — NLU pipeline timed (5 queries):**

| Query | Expected |
|---|---|
| `check my pnr 4521679834` | < 300ms |
| `cancel my ticket pnr 4521679834` | < 300ms |
| `search trains from NDLS to MMCT` | < 300ms |
| `book train 12951 from NDLS to MMCT` | < 300ms |
| `register complaint coach is dirty` | < 300ms |

**Why 300ms:** Standard acceptable response time for a real-time IVR system. Users expect instant feedback when speaking or typing.

---

## 🚀 Deployment on Render.com

### Platform Choice

**Render.com** was chosen for deployment because:
- ✅ 100% free — no credit card required
- ✅ Supports Python/FastAPI natively
- ✅ Deploys directly from GitHub
- ✅ Auto-redeploys on every push
- ✅ Provides HTTPS URL automatically
- ✅ Python 3.11 supported

---

### Deployment Files

**`render.yaml`** — tells Render how to build and start the app:
```yaml
services:
  - type: web
    name: irctc-smart-ivr
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

**`.python-version`** — pins Python version:
```
3.11.0
```

**Key fix in `main.py`** — absolute paths for static files and templates:
```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
```
This ensures Render finds the folders regardless of working directory.

---

### Deployment Steps

**Step 1 — Push code to GitHub**
```bash
git add .
git commit -m "Milestone 4 — testing and deployment"
git push
```

**Step 2 — Create Render Web Service**
1. Go to [render.com](https://render.com) → sign in with GitHub
2. Click **New +** → **Web Service**
3. Connect your GitHub repository

**Step 3 — Configure Settings**

| Field | Value |
|---|---|
| Name | `irctc-smart-ivr` |
| Region | `Singapore` |
| Root Directory | `Milestone-3` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | `Free` |

**Step 4 — Deploy**
Click **Create Web Service** → wait 2–3 minutes → live URL appears.

---

### Successful Build Log

```
==> Running build command 'pip install -r requirements.txt'
Successfully installed fastapi-0.110.0 uvicorn-0.29.0 jinja2-3.1.3 ...
==> Build successful 🎉
==> Deploying...
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:XXXXX
```

---

### Live Application

**URL:** [https://irctc-smart-ivr.onrender.com](https://irctc-smart-ivr.onrender.com)

**Login:** `admin` / `irctc123`

> ⚠️ Free tier note: App sleeps after 15 minutes of inactivity. First visit after sleep takes 30–60 seconds to wake up — this is normal behaviour for the free tier.

---

## 🐛 Issues Encountered During Deployment

| Error | Root Cause | Fix Applied |
|---|---|---|
| `python-multipart==0.09.0 not found` | Wrong version number (typo) | Changed to `0.0.9` |
| `pydantic-core build failed` | Render defaulted to Python 3.14, pydantic wheels don't exist | Pinned Python 3.11 in `render.yaml` + `.python-version` |
| `Could not import module "main"` | `main.py` not in repo root — was in subfolder | Set Root Directory in Render settings to `Milestone-3` |
| `Directory 'static' does not exist` | `main.py` used relative paths, Render runs from different directory | Fixed to use `os.path.abspath(__file__)` based absolute paths |
| `static/` folder missing on GitHub | Files uploaded flat via GitHub UI — lost folder structure | Re-uploaded using proper folder structure |

---



*Infosys Springboard Internship · Milestone 4 · Testing and Deployment*
