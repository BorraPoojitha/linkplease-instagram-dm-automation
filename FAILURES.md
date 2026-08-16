# FAILURES.md — Known Failure Scenarios & Edge Cases

This document describes real, empirical failure scenarios and edge cases in the LinkPlease backend architecture. It outlines exact failure conditions, impact analysis, root causes, risks of DM loss/duplication, and recommended future improvements.

---

## Failure Scenario 1: Worker Crash Immediately After PseudoGram API Accepts Request (Before DB Update)

### 1. Exact Condition
The background worker executes `POST /v1/dm/send`, receives an HTTP `202 Accepted` response with `dm_id: "dm_123"`, but the server process or host node experiences an ungraceful crash (e.g., SIGKILL, OOM kill, power outage) before the worker can execute `job.status = "accepted"` and `await session.commit()`.

### 2. What Can Go Wrong
Upon server restart, the persistent `dm_jobs` table still contains the job with status `processing` or `pending`. The restarted worker re-fetches the job and attempts to re-send the request to `POST /v1/dm/send`.

### 3. Why It Happens
DB commits are atomic operations executed over network/IPC after HTTP response deserialization. There is an unavoidable window of microsecond-to-millisecond latency between network HTTP receipt and DB commit.

### 4. Data / DM Duplication Risk
- **DM Lost?** No.
- **DM Duplicated?** **No**, because our system uses a **stable `Idempotency-Key`** (`ik_{rule_id}_{user_id}`). When the restarted worker sends the second request with the same `Idempotency-Key`, PseudoGram's API recognizes the idempotent key and returns the original `dm_id` or accepts it idempotently without sending duplicate DMs to the user.

### 5. Future Improvement
Implement a startup recovery hook that inspects jobs stuck in `processing` status for longer than 60 seconds and verifies their status with PseudoGram before re-queueing.

---

## Failure Scenario 2: Remote API Status Reconciliation Delay / Stall

### 1. Exact Condition
The job moves to `accepted` state after receiving HTTP 202 from `POST /v1/dm/send`. However, the mock PseudoGram server takes an exceptionally long time (or indefinitely stalls) in updating `GET /v1/dm/{dm_id}` from `status: "queued"` to `status: "delivered"` or `status: "failed"`.

### 2. What Can Go Wrong
The job remains in `accepted` status for an extended period. `GET /stats` counts this job under `queued` rather than `sent` or `failed`.

### 3. Why It Happens
PseudoGram API handles DM delivery asynchronously internally. If PseudoGram's internal message queues experience backlog or processing delays, `/v1/dm/{dm_id}` continues returning `{"status": "queued"}`.

### 4. Data / DM Duplication Risk
- **DM Lost?** No (it is queued remotely).
- **DM Duplicated?** No.
- **Impact on Stats:** The job is correctly categorized as `queued` in `/stats` until PseudoGram confirms delivery or failure.

### 5. Future Improvement
Implement a configurable reconciliation TTL (Time-To-Live). If a job remains in `accepted` state for over 24 hours without remote state change, flag it for administrative review or trigger a manual status query fallback.

---

## Failure Scenario 3: Process Restart During Local Sliding Window Rate Limiting

### 1. Exact Condition
The application worker processes a burst of 10 requests in 10 seconds, filling the in-memory sliding window rate limiter. Immediately afterwards, the application process restarts.

### 2. What Can Go Wrong
The in-memory timestamps in `SlidingWindowRateLimiter` are reset to empty. If another burst of webhooks arrives immediately upon restart, the rate limiter allows up to 10 requests in the next 10 seconds. If the remote PseudoGram server's rolling window measures requests across the restart boundary, the remote API returns HTTP 429 Rate Limited.

### 3. Why It Happens
The sliding window rate limiter stores timestamps in an in-memory deque for ultra-fast, zero-overhead execution without database read locks.

### 4. Data / DM Duplication Risk
- **DM Lost?** No.
- **DM Duplicated?** No.
- **System Behavior:** When the remote API returns HTTP 429, our worker catches the `429` status, reads the `Retry-After` response header, and updates the job status to `waiting_retry` with `next_attempt_at = now() + Retry-After`. The retry mechanism handles the remote rate limit safely without dropping jobs.

### 5. Future Improvement
For multi-instance deployments, store rate limiting timestamps in a shared persistent Redis instance using a sliding window sorted set (`ZADD`/`ZREMRANGEBYSCORE`).

---

## Failure Scenario 4: Comment Deletion Event Arrives After External DM API Acceptance

### 1. Exact Condition
A user posts a comment `"PRICE"`. Webhook `comment.created` arrives, matching the rule and queuing a DM job. The worker claims the job, calls `POST /v1/dm/send`, and receives HTTP 202 (`accepted`). Immediately after, the user deletes their comment, triggering a `comment.deleted` webhook.

### 2. What Can Go Wrong
Our system receives `comment.deleted` while the job is in `accepted` status (awaiting delivery status reconciliation from `GET /v1/dm/{dm_id}`).

### 3. Why It Happens
Out-of-order or delayed webhook delivery from Instagram/PseudoGram can cause deletion events to arrive after DM dispatch has already been accepted by the delivery network.

### 4. Data / DM Duplication Risk
- **Behavior & Policy:** `POST /webhook` marks jobs in `accepted` state as `cancelled`. However, because the DM has already been accepted by PseudoGram, the remote platform may still deliver the DM to the user's inbox.
- **DM Lost / Duplicated?** The DM was already accepted for delivery by the external platform before deletion; our application marks it `cancelled` locally so it is not counted as `sent` in local stats.

### 5. Future Improvement
If PseudoGram provides a `DELETE /v1/dm/{dm_id}` cancellation endpoint in the future, issue an explicit cancellation call to the remote API when cancelling an `accepted` job.
