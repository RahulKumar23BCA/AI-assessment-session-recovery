# AI Assessment — Session State Consistency & Recovery Module

> **Project: AI Assessment System** — Sub‑task by the Session Recovery team  
> Guarantees consistent session recovery for candidate assessments even if the server crashes, network fails, or browser disconnects.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Session Data Model](#session-data-model)
- [State Flow](#state-flow)
- [API Endpoints](#api-endpoints)
- [Setup & Installation](#setup--installation)
- [Running Locally](#running-locally)
- [Environment / Configuration](#environment--configuration)
- [Integration Guide](#integration-guide)
- [Testing the Flow in Swagger](#testing-the-flow-in-swagger)
- [Project Structure](#project-structure)
- [Future Improvements](#future-improvements)
- [Author](#author)

---

## Overview

This service is responsible for:

| Feature | Description |
|--------|-------------|
| **Persistent Session Storage** | Every checkpoint is stored in a relational DB (SQLite in dev, pluggable to PostgreSQL in prod). |
| **Checkpoint‑Based Recovery** | Frontend can send full session snapshots (question index, answers, time remaining). |
| **Auto‑Resume Mechanism** | On reconnect, frontend calls `/api/session/resume/{session_id}` to restore the last saved state. |
| **Idempotent Updates** | Same `session_id` can be checkpointed multiple times; the latest state always overwrites the old one. |
| **Simple Health Check** | `/ping` endpoint to verify that the module is running. |

This module is designed to be embedded into a larger AI Assessment platform as the **session state engine**.

---

## Architecture

```text
┌───────────────────────────────────────────────┐
│                Frontend (Exam UI)            │
│  - Renders questions                         │
│  - Sends checkpoint payloads                 │
│  - On crash/reload, calls /resume            │
└───────────────────────────┬───────────────────┘
                            │  HTTP (REST / JSON)
┌───────────────────────────▼───────────────────┐
│           FastAPI Session Service            │
│   (this repository)                         │
│                                             │
│  main.py                                    │
│  ┌────────────────────────────────────────┐  │
│  │   /ping                                │  │
│  │   /api/session/checkpoint              │  │
│  │   /api/session/resume/{session_id}     │  │
│  └────────────────────────────────────────┘  │
│             │                         │      │
│             ▼                         ▼      │
│  services/checkpoint_service.py   services/recovery_service.py
│  - save_session                   - get_session_by_id          │
└─────────────┬───────────────────────────┬──────────────────────┘
              │                           │
        SQLAlchemy ORM              Pydantic Schemas
              │                           │
┌─────────────▼───────────────────────────▼──────────────┐
│                     Database                          │
│                    (SQLite dev)                       │
│                                                       │
│  Table: sessions                                      │
│   - session_id (PK)                                   │
│   - candidate_id                                      │
│   - current_question                                  │
│   - answers (JSON)                                    │
│   - time_remaining (seconds)                          │
│   - status ("in_progress", "completed", ...)          │
└───────────────────────────────────────────────────────┘
```

---

## Session Data Model

### Database Model (SQLAlchemy)

```python
class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, nullable=False)
    current_question = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False, default={})
    time_remaining = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
```

**Field semantics:**

- `session_id` – Unique identifier for a test session. Used as the key by all APIs.  
- `candidate_id` – Who is taking the test (user id, email, registration number).  
- `current_question` – Index / number of the question where the candidate currently is.  
- `answers` (JSON) – All answers given so far, e.g. `{ "q1": "B", "q2": "C", "q3": "A" }`.  
- `time_remaining` – How many seconds are left in the exam when the checkpoint was saved.  
- `status` – High‑level state of this session: `"in_progress"`, `"completed"`, `"expired"`, `"paused"`, etc.

---

## State Flow

This module doesn’t enforce a complex state machine but supports a simple lifecycle based on the `status` field:

```text
NEW  ──(first checkpoint)────▶  IN_PROGRESS  ──▶  COMPLETED
                                  │
                                  └──────────▶  EXPIRED / ABORTED
```

Frontend is responsible for choosing the `status` value; the module simply persists whatever it receives.

Typical flows:

- Normal: `in_progress` → `completed`  
- Timed out: `in_progress` → `expired`  
- Interrupted: `in_progress` → (crash) → resume → `in_progress` → `completed`

---

## API Endpoints

Base URL (dev): `http://127.0.0.1:8000`  

Interactive Swagger docs: `http://127.0.0.1:8000/docs`

### 1. Health Check

**GET `/ping`**

- Purpose: Quick check that the service is running.  
- Response:

```json
{
  "status": "ok"
}
```

---

### 2. Save / Update Session Checkpoint

**POST `/api/session/checkpoint`**

- Description: Creates a new session row or updates an existing one using the same `session_id`.

- Request body (`CheckpointRequest`):

```json
{
  "session_id": "sess_demo_1",
  "candidate_id": "cand_001",
  "current_question": 3,
  "answers": {
    "q1": "B",
    "q2": "C",
    "q3": "A"
  },
  "time_remaining": 720,
  "status": "in_progress"
}
```

- Behavior:
  - If `session_id` does **not** exist → inserts a new row.  
  - If `session_id` **already exists** → updates that row with new values.

- Response (`ResumeResponse` – the stored state):

```json
{
  "session_id": "sess_demo_1",
  "candidate_id": "cand_001",
  "current_question": 3,
  "answers": {
    "q1": "B",
    "q2": "C",
    "q3": "A"
  },
  "time_remaining": 720,
  "status": "in_progress"
}
```

---

### 3. Resume Session

**GET `/api/session/resume/{session_id}`**

- Description: Returns the latest saved snapshot for a specific session, used when candidate reconnects.  

- Path parameter:
  - `session_id` (string) – id of the session to restore.

- Successful Response (`ResumeResponse`):

```json
{
  "session_id": "sess_demo_1",
  "candidate_id": "cand_001",
  "current_question": 5,
  "answers": {
    "q1": "B",
    "q2": "C",
    "q3": "A",
    "q4": "D",
    "q5": "B"
  },
  "time_remaining": 600,
  "status": "in_progress"
}
```

- Error Response (when not found):

```json
{
  "detail": "Session not found"
}
```

---

## Setup & Installation

### Prerequisites

- Python **3.11+**  
- VS Code or any editor  
- (Dev) SQLite – built into Python  

---

## Running Locally

From project root:

```bash
cd "C:\Intern Project\session_recovery_system"

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\activate

# Install dependencies (only once)
python -m pip install fastapi uvicorn sqlalchemy pydantic
```

### Start the server

```bash
python -m uvicorn main:app --reload --port 8000
```

Expected log snippet:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Open Swagger UI

In your browser:

```text
http://127.0.0.1:8000/docs
```

From here you can call all endpoints interactively.

---

## Environment / Configuration

Current development configuration (`database.py`):

```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
```

To use PostgreSQL or another DB in production, change `SQLALCHEMY_DATABASE_URL`, for example:

```python
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

No other code changes are required; SQLAlchemy handles the rest.

---

## Integration Guide

> For the team integrating this module into the main AI Assessment system.

### Typical Flow

```text
1. Candidate starts assessment
   → Frontend generates/receives session_id and sends first checkpoint.

2. During assessment (per question or every N seconds)
   → Frontend calls POST /api/session/checkpoint with current state.

3. Assessment crash / disconnect
   → Candidate closes tab, loses network, or backend restarts.

4. Candidate returns / refreshes
   → Frontend reads stored session_id
   → Calls GET /api/session/resume/{session_id}
   → Restores UI from returned state.
```

### Minimal Frontend Pseudocode

```javascript
// Save checkpoint
async function saveCheckpoint() {
  const sessionId = localStorage.getItem('session_id') || generateSessionId();
  localStorage.setItem('session_id', sessionId);

  await fetch('http://127.0.0.1:8000/api/session/checkpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      candidate_id: candidateId,
      current_question: currentQuestion,
      answers: answers,
      time_remaining: timeRemaining,
      status: 'in_progress'
    })
  });
}

// Resume on page load
async function resumeIfNeeded() {
  const sessionId = localStorage.getItem('session_id');
  if (!sessionId) return;

  const res = await fetch(`http://127.0.0.1:8000/api/session/resume/${sessionId}`);
  if (!res.ok) return;

  const session = await res.json();
  // Use session.current_question, session.answers, session.time_remaining
  restoreFromSession(session);
}
```

This module does **not** handle authentication; it should be placed behind your existing auth layer or API gateway.

---

## Testing the Flow in Swagger

1. Start server and open `http://127.0.0.1:8000/docs`.
2. **Health**  
   - Expand `GET /ping` → **Try it out** → **Execute** → expect `{"status": "ok"}`.
3. **First checkpoint**  
   - Expand `POST /api/session/checkpoint` → **Try it out**.  
   - Paste:

     ```json
     {
       "session_id": "sess_demo_1",
       "candidate_id": "cand_001",
       "current_question": 2,
       "answers": {"q1": "B", "q2": "C"},
       "time_remaining": 900,
       "status": "in_progress"
     }
     ```

   - Execute → expect 200 with same JSON.
4. **Resume**  
   - Expand `GET /api/session/resume/{session_id}` → **Try it out**.  
   - `session_id = sess_demo_1` → Execute → expect same state.
5. **Update**  
   - Again `POST /checkpoint` with `current_question = 5`, more answers, less time.  
   - Then `GET /resume/sess_demo_1` → new state is returned.

This proves crash recovery behavior.

---

## Project Structure

```text
session_recovery_system/
├── main.py                  # FastAPI app, middleware, router include
├── database.py              # SQLAlchemy engine, SessionLocal, Base
├── models.py                # Session model (sessions table)
├── test.db                  # SQLite database (dev)
├── routes/
│   ├── __init__.py
│   └── session_recovery.py  # API router: /checkpoint and /resume
├── schemas/
│   ├── __init__.py
│   └── session_recovery.py  # Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── checkpoint_service.py # save_session logic (create/update)
│   └── recovery_service.py   # get_session_by_id logic
└── requirements.txt
```

---

## Future Improvements

- Replace SQLite with PostgreSQL in production.  
- Add authentication/authorization around the endpoints.  
- Add richer `status` handling and validation (e.g. allowed transitions only).  
- Add structured logging and metrics (request durations, error rates).  
- Implement soft‑delete or archival for old sessions.

---

## Author

**Session Recovery Module — AI Assessment System**  
Sub‑task: *Session State Consistency & Recovery*