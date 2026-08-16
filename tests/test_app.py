import json
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from unittest.mock import AsyncMock, patch
from tests.conftest import generate_signature
from app.models.rule import Rule
from app.models.event import Event
from app.models.processed_comment import ProcessedComment
from app.models.duplicate_log import DuplicateLog
from app.models.dm_job import DMJob
from app.services.matcher import matches_keyword
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.worker import worker


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_rule(client):
    payload = {"keyword": "PRICE", "dm_message": "Here is the price list: $99"}
    response = await client.post("/rules", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "rule_id" in data
    assert data["keyword"] == "PRICE"
    assert data["dm_message"] == "Here is the price list: $99"


@pytest.mark.asyncio
async def test_keyword_matching():
    keyword = "PRICE"
    assert matches_keyword(keyword, "PRICE please")
    assert matches_keyword(keyword, "price?")
    assert matches_keyword(keyword, "What is the price?")
    assert matches_keyword(keyword, "Can I get the PRICE list?")
    assert not matches_keyword(keyword, "How much does it cost?")


@pytest.mark.asyncio
async def test_webhook_signature_validation(client):
    payload = {
        "event_id": "evt_test_sig_1",
        "event_type": "comment.created",
        "data": {"comment_id": "cmt_1", "text": "hello"}
    }
    body = json.dumps(payload).encode("utf-8")

    # Invalid signature -> HTTP 401
    headers_invalid = {"X-PseudoGram-Signature": "sha256=invalid"}
    res_invalid = await client.post("/webhook", content=body, headers=headers_invalid)
    assert res_invalid.status_code == 401

    # Valid signature with sha256= prefix -> HTTP 200
    valid_sig = generate_signature(body)
    headers_valid = {"X-PseudoGram-Signature": valid_sig}
    res_valid = await client.post("/webhook", content=body, headers=headers_valid)
    assert res_valid.status_code == 200

    # Valid signature without sha256= prefix -> HTTP 200
    raw_hex = valid_sig.replace("sha256=", "")
    res_raw = await client.post("/webhook", content=body, headers={"X-PseudoGram-Signature": raw_hex})
    # Wait, event_id is duplicated here, but signature check happens first
    assert res_raw.status_code == 200


@pytest.mark.asyncio
async def test_duplicate_event_id_ignored(client, db_session):
    payload = {
        "event_id": "evt_duplicate_1",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22.481Z",
        "data": {
            "comment_id": "cmt_dup_1",
            "post_id": "post_1",
            "text": "Check price",
            "from": {"user_id": "usr_dup_1", "username": "user1"}
        }
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"X-PseudoGram-Signature": generate_signature(body)}

    # Send event first time
    res1 = await client.post("/webhook", content=body, headers=headers)
    assert res1.status_code == 200

    # Send event second time (duplicate event_id)
    res2 = await client.post("/webhook", content=body, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored_duplicate_event"

    # Verify duplicate event did NOT increment duplicates_blocked
    dups_res = await db_session.execute(select(DuplicateLog))
    dups = dups_res.scalars().all()
    assert len(dups) == 0


@pytest.mark.asyncio
async def test_duplicate_user_rule_deduplication(client, db_session):
    # 1. Create a rule
    rule_res = await client.post("/rules", json={"keyword": "PRICE", "dm_message": "Price list link"})
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["rule_id"]

    # 2. First comment by user_100
    payload1 = {
        "event_id": "evt_user100_comment1",
        "event_type": "comment.created",
        "data": {
            "comment_id": "cmt_101",
            "post_id": "post_1",
            "text": "PRICE please",
            "from": {"user_id": "usr_100", "username": "user100"}
        }
    }
    body1 = json.dumps(payload1).encode("utf-8")
    res1 = await client.post("/webhook", content=body1, headers={"X-PseudoGram-Signature": generate_signature(body1)})
    assert res1.status_code == 200

    # Verify 1 DMJob created with stable Idempotency-Key
    jobs_res1 = await db_session.execute(select(DMJob).where(DMJob.user_id == "usr_100"))
    jobs1 = jobs_res1.scalars().all()
    assert len(jobs1) == 1
    assert jobs1[0].rule_id == rule_id
    assert jobs1[0].idempotency_key == f"ik_{rule_id}_usr_100"

    # 3. Second comment by user_100 matching SAME rule
    payload2 = {
        "event_id": "evt_user100_comment2",
        "event_type": "comment.created",
        "data": {
            "comment_id": "cmt_102",
            "post_id": "post_1",
            "text": "What is the price?",
            "from": {"user_id": "usr_100", "username": "user100"}
        }
    }
    body2 = json.dumps(payload2).encode("utf-8")
    res2 = await client.post("/webhook", content=body2, headers={"X-PseudoGram-Signature": generate_signature(body2)})
    assert res2.status_code == 200

    # Verify no additional DMJob was created, and DuplicateLog was recorded
    jobs_res2 = await db_session.execute(select(DMJob).where(DMJob.user_id == "usr_100"))
    jobs2 = jobs_res2.scalars().all()
    assert len(jobs2) == 1

    dups_res = await db_session.execute(select(DuplicateLog).where(DuplicateLog.user_id == "usr_100"))
    dups = dups_res.scalars().all()
    assert len(dups) == 1


@pytest.mark.asyncio
async def test_multiple_matching_rules(client, db_session):
    # Create two rules
    r1 = await client.post("/rules", json={"keyword": "PRICE", "dm_message": "Price list"})
    r2 = await client.post("/rules", json={"keyword": "INFO", "dm_message": "Info guide"})
    
    payload = {
        "event_id": "evt_multi_rules_1",
        "event_type": "comment.created",
        "data": {
            "comment_id": "cmt_multi_1",
            "text": "Send PRICE and INFO please",
            "from": {"user_id": "usr_multi_1", "username": "multi"}
        }
    }
    body = json.dumps(payload).encode("utf-8")
    res = await client.post("/webhook", content=body, headers={"X-PseudoGram-Signature": generate_signature(body)})
    assert res.status_code == 200

    # Should create 2 DM jobs for the user (1 per rule)
    jobs_res = await db_session.execute(select(DMJob).where(DMJob.user_id == "usr_multi_1"))
    jobs = jobs_res.scalars().all()
    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_concurrent_webhook_duplicate_protection(client, db_session):
    # Create rule
    await client.post("/rules", json={"keyword": "DISCOUNT", "dm_message": "Here is 20% off"})

    payload1 = {
        "event_id": "evt_conc_1",
        "event_type": "comment.created",
        "data": {"comment_id": "cmt_c1", "text": "DISCOUNT please", "from": {"user_id": "usr_conc_1"}}
    }
    payload2 = {
        "event_id": "evt_conc_2",
        "event_type": "comment.created",
        "data": {"comment_id": "cmt_c2", "text": "Can I get DISCOUNT?", "from": {"user_id": "usr_conc_1"}}
    }

    body1 = json.dumps(payload1).encode("utf-8")
    body2 = json.dumps(payload2).encode("utf-8")

    # Send both webhooks concurrently
    await asyncio.gather(
        client.post("/webhook", content=body1, headers={"X-PseudoGram-Signature": generate_signature(body1)}),
        client.post("/webhook", content=body2, headers={"X-PseudoGram-Signature": generate_signature(body2)})
    )

    # Exactly 1 DMJob created
    jobs_res = await db_session.execute(select(DMJob).where(DMJob.user_id == "usr_conc_1"))
    jobs = jobs_res.scalars().all()
    assert len(jobs) == 1

    # Exactly 1 duplicate logged
    dups_res = await db_session.execute(select(DuplicateLog).where(DuplicateLog.user_id == "usr_conc_1"))
    dups = dups_res.scalars().all()
    assert len(dups) == 1


@pytest.mark.asyncio
async def test_worker_202_accepted_and_reconciliation(db_session):
    # Manually create a pending job
    job = DMJob(
        rule_id="rule_1",
        user_id="usr_rec_1",
        comment_id="cmt_rec_1",
        message="Hello",
        idempotency_key="ik_rule1_usr_rec_1",
        status="pending"
    )
    db_session.add(job)
    await db_session.commit()

    # Mock send_dm response (HTTP 202)
    with patch("app.services.worker.dm_client.send_dm", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (202, {"dm_id": "dm_accepted_99", "status": "queued"}, None)

        await worker.process_jobs_batch()

        await db_session.refresh(job)
        assert job.status == "accepted"
        assert job.dm_id == "dm_accepted_99"

    # Mock check_dm_status response (HTTP 200 delivered)
    with patch("app.services.worker.dm_client.check_dm_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = (200, {"dm_id": "dm_accepted_99", "status": "delivered"})

        await worker.reconcile_accepted_jobs()

        await db_session.refresh(job)
        assert job.status == "delivered"


@pytest.mark.asyncio
async def test_worker_500_retry_and_max_attempts_exceeded(db_session):
    job = DMJob(
        rule_id="rule_500",
        user_id="usr_500",
        comment_id="cmt_500",
        message="Retry msg",
        idempotency_key="ik_500",
        status="pending",
        attempts=4,
        max_attempts=5
    )
    db_session.add(job)
    await db_session.commit()

    # 5th attempt fails with HTTP 500 -> Max attempts reached -> permanent fail
    with patch("app.services.worker.dm_client.send_dm", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (500, {"error": "internal_error"}, None)

        await worker.process_jobs_batch()

        await db_session.refresh(job)
        assert job.status == "failed"
        assert job.attempts == 5
        assert "Max retries" in job.last_error


@pytest.mark.asyncio
async def test_worker_400_invalid_request_no_retry(db_session):
    job = DMJob(
        rule_id="rule_400",
        user_id="usr_400",
        comment_id="cmt_400",
        message="Bad msg",
        idempotency_key="ik_400",
        status="pending"
    )
    db_session.add(job)
    await db_session.commit()

    with patch("app.services.worker.dm_client.send_dm", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (400, {"error": "invalid_request", "detail": "User blocked DMs"}, None)

        await worker.process_jobs_batch()

        await db_session.refresh(job)
        assert job.status == "failed"
        assert "Invalid Request" in job.last_error


@pytest.mark.asyncio
async def test_worker_429_rate_limited(db_session):
    job = DMJob(
        rule_id="rule_429",
        user_id="usr_429",
        comment_id="cmt_429",
        message="Rate test",
        idempotency_key="ik_429",
        status="pending"
    )
    db_session.add(job)
    await db_session.commit()

    with patch("app.services.worker.dm_client.send_dm", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (429, {"error": "rate_limited"}, 45)

        await worker.process_jobs_batch()

        await db_session.refresh(job)
        assert job.status == "waiting_retry"
        assert "Retry-After: 45s" in job.last_error


@pytest.mark.asyncio
async def test_comment_deleted_handling(client, db_session):
    # Create DM job with pending status
    job_pending = DMJob(
        rule_id="r1", user_id="u1", comment_id="cmt_del_1", message="Hi", idempotency_key="ik_del1", status="pending"
    )
    # Create DM job with delivered status
    job_delivered = DMJob(
        rule_id="r2", user_id="u2", comment_id="cmt_del_2", message="Hi", idempotency_key="ik_del2", status="delivered"
    )
    db_session.add(job_pending)
    db_session.add(job_delivered)
    await db_session.commit()

    # Send comment.deleted for cmt_del_1
    del_payload1 = {
        "event_id": "evt_del_1",
        "event_type": "comment.deleted",
        "data": {"comment_id": "cmt_del_1"}
    }
    body1 = json.dumps(del_payload1).encode("utf-8")
    await client.post("/webhook", content=body1, headers={"X-PseudoGram-Signature": generate_signature(body1)})

    # Send comment.deleted for cmt_del_2
    del_payload2 = {
        "event_id": "evt_del_2",
        "event_type": "comment.deleted",
        "data": {"comment_id": "cmt_del_2"}
    }
    body2 = json.dumps(del_payload2).encode("utf-8")
    await client.post("/webhook", content=body2, headers={"X-PseudoGram-Signature": generate_signature(body2)})

    await db_session.refresh(job_pending)
    await db_session.refresh(job_delivered)

    # Pending job should be cancelled
    assert job_pending.status == "cancelled"
    # Delivered job should remain delivered
    assert job_delivered.status == "delivered"


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1.0)
    # First 3 requests -> 0.0 wait
    assert await limiter.acquire_slot() == 0.0
    assert await limiter.acquire_slot() == 0.0
    assert await limiter.acquire_slot() == 0.0

    # 4th request -> must wait > 0
    wait = await limiter.acquire_slot()
    assert wait > 0.0

    # Wait for window to expire
    await asyncio.sleep(1.05)
    # Now slot is available again
    assert await limiter.acquire_slot() == 0.0


@pytest.mark.asyncio
async def test_stats_accuracy(client, db_session):
    # Add jobs in various states
    j1 = DMJob(rule_id="r1", user_id="u1", comment_id="c1", message="m", idempotency_key="ik1", status="delivered")
    j2 = DMJob(rule_id="r1", user_id="u2", comment_id="c2", message="m", idempotency_key="ik2", status="failed")
    j3 = DMJob(rule_id="r1", user_id="u3", comment_id="c3", message="m", idempotency_key="ik3", status="pending")
    j4 = DMJob(rule_id="r1", user_id="u4", comment_id="c4", message="m", idempotency_key="ik4", status="accepted")
    
    dup1 = DuplicateLog(rule_id="r1", user_id="u5", comment_id="c5")

    db_session.add_all([j1, j2, j3, j4, dup1])
    await db_session.commit()

    stats_res = await client.get("/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["sent"] == 1
    assert stats["failed"] == 1
    assert stats["queued"] == 2  # pending + accepted
    assert stats["duplicates_blocked"] == 1
