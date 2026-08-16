# LinkPlease — Automated Instagram DM Fulfillment Service & SaaS Dashboard

LinkPlease is a high-reliability, asynchronous backend microservice and modern SaaS dashboard built with **Python 3.12+**, **FastAPI**, **React 18**, and **SQLAlchemy**. It ingests Instagram-style comment webhook events, matches text against configured keyword rules, atomically deduplicates requests, queues persistent DM jobs, enforces rolling rate limits, executes bounded retries with exponential backoff, and reconciles delivery status with external APIs.

---

## Architecture Overview

```
                                  +-----------------------+
                                  |   PseudoGram Webhook  |
                                  +-----------------------+
                                              |
                                              | POST /webhook (HMAC verified)
                                              v
+------------------+              +-----------------------+              +-----------------------+
|   GET /stats     | <----------- |   FastAPI App Server  | -----------> | React SaaS Dashboard  |
|   GET /health    |              +-----------------------+              | http://localhost:8000 |
|   POST /rules    |                          |                          +-----------------------+
+------------------+                          | Atomic DB Claim
                                              v
                                  +-----------------------+
                                  | SQLite / PostgreSQL   |
                                  | - events              |
                                  | - rules               |
                                  | - processed_comments  |
                                  | - duplicate_logs      |
                                  | - dm_jobs             |
                                  +-----------------------+
                                              |
                                              | Polls ready jobs
                                              v
                                  +-----------------------+
                                  |   Background Worker   |
                                  | (Sliding Window RL)   |
                                  +-----------------------+
                                              |
                                              | POST /v1/dm/send (Idempotent)
                                              | GET  /v1/dm/{dm_id} (Reconciliation)
                                              v
                                  +-----------------------+
                                  |   PseudoGram API      |
                                  +-----------------------+
```

---

## Technology Stack

- **Backend Framework**: FastAPI (Async) & Uvicorn
- **Frontend Dashboard**: React 18 + Vite + Lucide Icons + CSS Custom Properties Design System
- **ORM & Database**: SQLAlchemy 2.0 (Async) supporting **SQLite** (WAL mode) and **PostgreSQL** (`asyncpg`)
- **Data Validation & Env**: Pydantic v2 & `pydantic-settings`
- **HTTP Client**: `httpx`
- **Testing**: `pytest` & `pytest-asyncio`

---

## Interactive Endpoints & UI

When running `python run.py`:
- 🌐 **SaaS Dashboard UI**: `http://localhost:8000/`
- 🌐 **Interactive Swagger API Docs**: `http://localhost:8000/docs`
- 🌐 **Health Endpoint**: `http://localhost:8000/health`
- 🌐 **Stats Endpoint**: `http://localhost:8000/stats`

---

## API Endpoints

### Mandatory Contracts (Unchanged)
- `POST /webhook`: Receives comment events (< 5s return). HMAC-SHA256 signature protected.
- `POST /rules`: Creates new rule (`HTTP 201`).
- `GET /stats`: Returns persistent stats (`sent`, `failed`, `queued`, `duplicates_blocked`).
- `GET /health`: Returns `{"status": "ok"}`.

### Safe Read Endpoints (Added for UI)
- `GET /rules`: Lists all created rules.
- `GET /jobs`: Lists all DM jobs and delivery status.
- `GET /events`: Lists received webhook audit events.

---

## Local Setup & Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build Frontend (already pre-built in frontend/dist)
cd frontend
npm install
npm run build
cd ..

# 3. Run Application
python run.py
```

---

## Testing & Load Simulation

```bash
# Run 100% passing automated test suite
python -m pytest -v

# Run 500-event load simulation
python test_simulation.py
```

---

## Deployment (Render / Docker / Railway)

- **Render Blueprint**: Configured in `render.yaml`. Connect your GitHub repo to Render; it automatically provisions PostgreSQL and runs `python run.py`.
- **Docker Container**: Configured in `Dockerfile`. Build with `docker build -t linkplease .` and run with `docker run -p 8000:8000 linkplease`.
