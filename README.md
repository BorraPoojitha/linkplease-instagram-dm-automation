# LinkPlease — Automated Instagram DM Fulfillment Service & SaaS Dashboard

LinkPlease is a high-reliability, asynchronous backend microservice and modern SaaS dashboard built with **Python 3.12+**, **FastAPI**, **React 18**, and **SQLAlchemy**. It ingests Instagram-style comment webhook events, matches text against configured keyword rules, atomically deduplicates requests, queues persistent DM jobs, enforces rolling rate limits, executes bounded retries with exponential backoff, and reconciles delivery status with external APIs.

---

## 🌐 Live Production Deployments

| Component | Provider | Live URL |
|---|---|---|
| 🖥️ **React SaaS Dashboard** | **Vercel** | [https://linkplease-instagram-dm-automation.vercel.app](https://linkplease-instagram-dm-automation.vercel.app) |
| ⚙️ **FastAPI Backend & DB Worker** | **Render** | [https://linkplease-ttp8.onrender.com](https://linkplease-ttp8.onrender.com) |
| 📖 **Interactive Swagger API Specs** | **Render** | [https://linkplease-ttp8.onrender.com/docs](https://linkplease-ttp8.onrender.com/docs) |
| 📦 **Source Code Repository** | **GitHub** | [https://github.com/BorraPoojitha/linkplease-instagram-dm-automation](https://github.com/BorraPoojitha/linkplease-instagram-dm-automation) |

---

## Architecture Overview

```
+-------------------------------------------------------------------------+
|                  Vercel Global CDN (Frontend Dashboard)                |
|           https://linkplease-instagram-dm-automation.vercel.app        |
+-------------------------------------------------------------------------+
                                    |
                                    | REST API Calls (CORS Enabled)
                                    v
+-------------------------------------------------------------------------+
|                    Render Cloud (Backend Service)                       |
|                   https://linkplease-ttp8.onrender.com                  |
|                                                                         |
|   +-----------------------+              +--------------------------+   |
|   |  POST /webhook        | ------------>|  SQL Database (SQLite/PG) |   |
|   |  POST /rules          |              |  - rules                 |   |
|   |  GET  /stats          |              |  - events                |   |
|   |  GET  /health         |              |  - processed_comments    |   |
|   +-----------------------+              |  - dm_jobs               |   |
|                                          +--------------------------+   |
|                                                       |                 |
|                                                       v                 |
|                                          +--------------------------+   |
|                                          |   Background Worker      |   |
|                                          |  (Sliding Window RL 10/s) |   |
|                                          +--------------------------+   |
+-------------------------------------------------------------------------+
                                                        |
                                                        | POST /v1/dm/send (Idempotent)
                                                        | GET  /v1/dm/{dm_id} (Reconcile)
                                                        v
                                           +--------------------------+
                                           |   PseudoGram External API|
                                           +--------------------------+
```

---

## Technology Stack

- **Frontend Dashboard**: React 18 + Vite + Lucide Icons + CSS Custom Properties SaaS design system (Hosted on Vercel)
- **Backend Framework**: FastAPI (Async) & Uvicorn (Hosted on Render)
- **ORM & Database**: SQLAlchemy 2.0 (Async) supporting **SQLite** (WAL mode) and **PostgreSQL** (`asyncpg`)
- **Data Validation & Env**: Pydantic v2 & `pydantic-settings`
- **HTTP Client**: `httpx`
- **Testing**: `pytest` & `pytest-asyncio`

---

## Key Features & Strategies

### 1. Webhook Fast Response (< 5 Seconds)
`/webhook` validates the HMAC signature, persists raw event bytes to ensure `event_id` uniqueness, performs atomic keyword matching, queues a persistent job in `dm_jobs`, and returns `HTTP 200` immediately.

### 2. Signature Verification
Incoming webhooks require header `X-PseudoGram-Signature: sha256=<hex>`. Verification uses raw request bytes, `PSEUDOGRAM_API_KEY`, and constant-time string comparison (`hmac.compare_digest`).

### 3. Duplicate Prevention & Idempotency
- **Event Idempotency**: `event_id` is enforced as UNIQUE primary key in `events`. Duplicate webhook events are ignored gracefully without incrementing `duplicates_blocked`.
- **Business Idempotency**: `(rule_id, user_id)` is enforced via a Composite Primary Key in `processed_comments`. On duplicate claim attempt (`IntegrityError`), a record is stored in `duplicate_logs` (incrementing `duplicates_blocked` in `/stats`) and no DM job is created.
- **Stable Idempotency Key**: Each job generates a persistent key `idempotency_key = f"ik_{rule_id}_{user_id}"` passed in `Idempotency-Key` header on all retries.

### 4. Sliding Window Rate Limiting
The worker uses an in-memory `SlidingWindowRateLimiter` allowing **at most 10 `POST /v1/dm/send` requests per rolling 60 seconds**. Outbound status queries (`GET /v1/dm/{dm_id}`) do **NOT** count against this rate limit.

### 5. Retries & Backoff
- **HTTP 500 / Network Error**: Exponential backoff with random jitter (`2^attempts + jitter`).
- **HTTP 429 Rate Limited**: Reads `Retry-After` header and reschedules job after specified delay.
- **HTTP 400 Invalid Request**: Marks job `failed` permanently without retry.
- **Max Retries**: Bounded by `MAX_RETRIES` environment variable (default: 5).

---

## Local Setup & Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run automated tests (100% passing)
python -m pytest -v

# 3. Run application locally
python run.py
```

---

## Documentation Artifacts
For technical interview preparation, review:
- [EXPLANATION.md](file:///c:/Users/borra/OneDrive/Desktop/LINKPLEASE/EXPLANATION.md)
- [FAILURES.md](file:///c:/Users/borra/OneDrive/Desktop/LINKPLEASE/FAILURES.md)
