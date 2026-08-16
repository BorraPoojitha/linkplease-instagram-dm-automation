# EXPLANATION.md — Technical Guide & Interview Study Notes

This document provides a simple, clear, line-by-line guide to explain the architecture, design choices, data flow, and code implementation of the LinkPlease backend service during an interview.

---

## 1. Project Overview & Concept

LinkPlease is an automated Instagram DM fulfillment system. When a user comments on a post with a specific keyword (e.g. `"PRICE"`), the system automatically queues and sends a personalized Direct Message (DM) containing details (e.g. price list link) using the PseudoGram API.

---

## 2. Request Flow: Webhook to DM

```
[User Comments] -> [PseudoGram Webhook] -> [POST /webhook]
                                                |
                                    (1) Validate HMAC Signature
                                    (2) Save Event & Check Unique event_id
                                    (3) Match Keyword with Rules
                                    (4) Atomic DB Claim (rule_id, user_id)
                                                |
                                    [Return 200 OK immediately (< 5s)]
                                                |
                                                v
                                  [Persistent DMJob in DB (pending)]
                                                |
                                                v
                                     [Background Worker Polls]
                                     [Acquire Rate Limit Slot]
                                     [POST /v1/dm/send (HTTP 202)]
                                                |
                                                v
                                     [DMJob Status -> accepted]
                                                |
                                                v
                                  [Reconciliation GET /v1/dm/{dm_id}]
                                                |
                                                v
                                     [DMJob Status -> delivered]
```

---

## 3. Key Concepts Explained

### 3.1 Why Webhook Returns Immediately (< 5s)
External DM dispatch involves network latency, remote rate limits, and retries. Performing remote API HTTP requests directly inside the POST `/webhook` route handler would block the request, cause timeout errors (> 5 seconds), and crash under load.
Instead, `/webhook` only validates the signature, performs atomic DB operations, queues a `DMJob` record in SQLite/PostgreSQL, and returns HTTP 200 immediately.

### 3.2 Duplicate Events vs Business Duplicates
- **Duplicate Event (`event_id`)**: Occurs when Instagram/PseudoGram sends the exact same webhook payload twice (e.g. due to network retries). We save `event_id` in the `events` table with a PRIMARY KEY. If a duplicate arrives, SQLite/PostgreSQL throws an `IntegrityError`, we catch it, rollback, and return `{"status": "ignored_duplicate_event"}`. We do **NOT** count this under `duplicates_blocked`.
- **Business Duplicate `(rule_id, user_id)`**: Occurs when the same user comments multiple times with text matching the same rule. The business requirement states: **A user must NEVER receive the same rule's DM twice.**

### 3.3 Atomic Database Claiming
To prevent race conditions when two webhooks arrive simultaneously for the same user, we use a database table `processed_comments` with a **Composite Primary Key `(rule_id, user_id)`**.
When a matching comment arrives, we attempt to insert `(rule_id, user_id)` into `processed_comments`.
- If the insert **succeeds**, this worker won the race. It creates a `DMJob`.
- If the insert **fails** (`IntegrityError`), another request already claimed this pair. We record a entry in `duplicate_logs` (incrementing `duplicates_blocked`) and skip DM creation.
Because database primary keys are enforced atomically at the SQL storage engine level, race conditions are mathematically impossible regardless of worker concurrency.

### 3.4 Stable Idempotency Key
For each logical DM job, we generate one deterministic, stable `idempotency_key`:
`idempotency_key = f"ik_{rule_id}_{user_id}"`
This key is stored in the `dm_jobs` table. If the HTTP request to `/v1/dm/send` fails with 500 or 429 and is retried 3 times, we pass the **EXACT SAME `Idempotency-Key` header** on every attempt. If PseudoGram received the first request before crashing, it recognizes the idempotency key and avoids duplicate DM delivery.

### 3.5 Accepted (202) vs Delivered (200)
- **HTTP 202 Accepted**: Means PseudoGram accepted the DM job into its internal processing queue. It returns a `dm_id`. The job is marked `accepted`. It is **NOT** counted as `sent` yet.
- **Delivery Status Reconciliation**: The background worker polls `GET /v1/dm/{dm_id}` (which does not count against send rate limits). Only when `/v1/dm/{dm_id}` returns `status: "delivered"` do we update the job status to `delivered` (incrementing `sent` in `/stats`).

### 3.6 Rate Limiting (10 req / 60s)
We implement a thread-safe `SlidingWindowRateLimiter` using a timestamp deque (`collections.deque`).
Before calling `POST /v1/dm/send`, the worker calls `rate_limiter.acquire_slot()`. If 10 requests have already occurred within the rolling 60-second window, the rate limiter returns the exact wait time needed. The worker postpones the job (`next_attempt_at = now() + wait_time`) without dropping it.

### 3.7 Comment Deletion
When a `comment.deleted` event arrives:
- If the associated `DMJob` is in `pending`, `processing`, `waiting_retry`, or `accepted` state: we set status to `cancelled`.
- If already `delivered`: we leave it as `delivered` (cannot un-send a delivered DM).

---

## 4. Dependencies & Tech Stack

| Dependency | Purpose | Why Chosen |
|---|---|---|
| **FastAPI** | Web framework | High performance, async native, auto OpenAPI docs, fast request processing |
| **Uvicorn** | ASGI web server | Lightning fast async server execution |
| **SQLAlchemy (Async)** | ORM & DB Abstraction | Portable between SQLite (`aiosqlite`) and PostgreSQL (`asyncpg`) without code changes |
| **aiosqlite** | Async SQLite driver | Non-blocking database execution for local dev/testing |
| **asyncpg** | Async PostgreSQL driver | High performance PostgreSQL driver for production |
| **Pydantic / pydantic-settings** | Data validation & env loading | Strongly typed config loading from `.env` |
| **httpx** | Async HTTP client | Clean async HTTP client for PseudoGram API calls |
| **pytest & pytest-asyncio** | Test suite | Automated test execution with async fixture support |

---

## 5. File-by-File Explanation

### `app/config.py`
Defines application settings (`PSEUDOGRAM_API_KEY`, `DATABASE_URL`, `MAX_RETRIES`, etc.) loaded from environment variables or `.env`.

### `app/database.py`
Sets up the SQLAlchemy async engine and session factory (`AsyncSessionLocal`). Enables WAL mode (`PRAGMA journal_mode=WAL;`) for SQLite to support concurrent database access.

### `app/models/`
- `rule.py`: Stores configured keywords and DM text.
- `event.py`: Stores received raw webhooks with unique `event_id`.
- `processed_comment.py`: Enforces `(rule_id, user_id)` primary key uniqueness.
- `duplicate_log.py`: Logs blocked duplicate DM attempts for persistent `/stats`.
- `dm_job.py`: Stores DM job queue state (`pending`, `processing`, `waiting_retry`, `accepted`, `delivered`, `failed`, `cancelled`).

### `app/services/`
- `signature.py`: Verifies HMAC-SHA256 signature using `PSEUDOGRAM_API_KEY` and `hmac.compare_digest`.
- `matcher.py`: Performs case-insensitive substring matching (`keyword.lower() in text.lower()`).
- `rate_limiter.py`: Sliding window rate limiter enforcing max 10 send requests / rolling 60s.
- `dm_client.py`: Client for PseudoGram API endpoints (`/v1/dm/send` and `/v1/dm/{dm_id}`).
- `worker.py`: Async background worker loop. Atomically claims jobs (`UPDATE ... WHERE status='pending'`), handles backoff retries, and reconciles accepted DMs.

### `app/routes/`
- `health.py`: `GET /health` endpoint returning `{"status": "ok"}`.
- `rules.py`: `POST /rules` endpoint returning HTTP 201.
- `webhook.py`: `POST /webhook` endpoint for validating signatures, event deduplication, and atomic job queuing.
- `stats.py`: `GET /stats` returning accurate metrics directly from database queries.
