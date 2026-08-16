import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, or_
import app.database as app_db
from app.models.dm_job import DMJob
from app.services.dm_client import dm_client
from app.services.rate_limiter import rate_limiter
from app.config import settings


logger = logging.getLogger("linkplease.worker")
logger.setLevel(logging.INFO)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BackgroundWorker:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Background worker started.")

    async def stop(self):
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("Background worker stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.process_jobs_batch()
                await self.reconcile_accepted_jobs()
            except Exception as exc:
                logger.error(f"Error in worker run loop: {exc}", exc_info=True)

            await asyncio.sleep(settings.WORKER_POLL_INTERVAL)

    async def process_jobs_batch(self):
        """Processes ready pending or retryable DM jobs atomically."""
        now = utc_now()
        async with app_db.AsyncSessionLocal() as session:
            # Select candidate job IDs ready for execution
            stmt = (
                select(DMJob.id)
                .where(
                    or_(DMJob.status == "pending", DMJob.status == "waiting_retry"),
                    DMJob.next_attempt_at <= now
                )
                .order_by(DMJob.next_attempt_at.asc())
                .limit(5)
            )
            result = await session.execute(stmt)
            job_ids = [row[0] for row in result.all()]

            for job_id in job_ids:
                # Atomic Claiming: Update status to 'processing' only if current status is pending/waiting_retry
                claim_stmt = (
                    update(DMJob)
                    .where(
                        DMJob.id == job_id,
                        or_(DMJob.status == "pending", DMJob.status == "waiting_retry")
                    )
                    .values(status="processing", updated_at=utc_now())
                )
                claim_result = await session.execute(claim_stmt)
                await session.commit()

                if claim_result.rowcount == 0:
                    # Another worker claimed this job
                    continue

                # Load job details
                job = await session.get(DMJob, job_id)
                if not job:
                    continue

                # Check sliding window rate limit
                wait_time = await rate_limiter.acquire_slot()
                if wait_time > 0:
                    # Rate limited by local limiter: requeue job for later
                    job.status = "waiting_retry"
                    job.next_attempt_at = utc_now() + timedelta(seconds=wait_time)
                    job.last_error = f"Local rate limit reached; waiting {wait_time:.2f}s"
                    await session.commit()
                    logger.info(f"Job {job_id} deferred by rate limiter for {wait_time:.2f}s")
                    continue

                # Execute DM send request with stable idempotency key
                status_code, data, retry_after = await dm_client.send_dm(
                    recipient_user_id=job.user_id,
                    message=job.message,
                    comment_id=job.comment_id,
                    idempotency_key=job.idempotency_key
                )

                job.attempts += 1
                job.updated_at = utc_now()

                if status_code == 202:
                    # Accepted
                    job.status = "accepted"
                    job.dm_id = data.get("dm_id") if isinstance(data, dict) else None
                    job.last_error = None
                    logger.info(f"Job {job_id} ACCEPTED with dm_id {job.dm_id}")

                elif status_code == 429:
                    # Rate limited by remote API
                    wait = retry_after if retry_after else 60
                    job.status = "waiting_retry"
                    job.next_attempt_at = utc_now() + timedelta(seconds=wait)
                    job.last_error = f"API 429 Rate Limited. Retry-After: {wait}s"
                    logger.warning(f"Job {job_id} rate limited by remote API. Retry-After: {wait}s")

                elif status_code == 400:
                    # Invalid request -> Permanently Fail
                    job.status = "failed"
                    detail = data.get("detail", "Invalid Request") if isinstance(data, dict) else str(data)
                    job.last_error = f"API 400 Invalid Request: {detail}"
                    logger.error(f"Job {job_id} permanently failed (400): {detail}")

                else:
                    # 500 or connection error -> Exponential backoff retry
                    if job.attempts >= job.max_attempts:
                        job.status = "failed"
                        job.last_error = f"Max retries ({job.max_attempts}) exceeded. Last HTTP status: {status_code}"
                        logger.error(f"Job {job_id} permanently failed after max retries")
                    else:
                        backoff = min(300, (2 ** job.attempts) + random.uniform(0.1, 1.0))
                        job.status = "waiting_retry"
                        job.next_attempt_at = utc_now() + timedelta(seconds=backoff)
                        job.last_error = f"HTTP {status_code} Error. Retrying in {backoff:.2f}s"
                        logger.warning(f"Job {job_id} failed with HTTP {status_code}, retrying in {backoff:.2f}s")

                await session.commit()

    async def reconcile_accepted_jobs(self):
        """Reconciles accepted DM jobs by polling GET /v1/dm/{dm_id}."""
        async with app_db.AsyncSessionLocal() as session:
            stmt = (
                select(DMJob)
                .where(DMJob.status == "accepted", DMJob.dm_id.isnot(None))
                .limit(10)
            )
            result = await session.execute(stmt)
            accepted_jobs = result.scalars().all()

            for job in accepted_jobs:
                status_code, data = await dm_client.check_dm_status(job.dm_id)
                if status_code == 200 and isinstance(data, dict):
                    dm_status = data.get("status")
                    if dm_status == "delivered":
                        job.status = "delivered"
                        job.updated_at = utc_now()
                        logger.info(f"Job {job.id} (dm_id: {job.dm_id}) reconciled as DELIVERED")
                    elif dm_status == "failed":
                        job.attempts += 1
                        if job.attempts >= job.max_attempts:
                            job.status = "failed"
                            job.last_error = "Remote DM status reported FAILED"
                        else:
                            backoff = min(300, (2 ** job.attempts) + random.uniform(0.1, 1.0))
                            job.status = "waiting_retry"
                            job.next_attempt_at = utc_now() + timedelta(seconds=backoff)
                            job.last_error = f"Remote DM failed, retrying in {backoff:.2f}s"
                        job.updated_at = utc_now()
                        logger.warning(f"Job {job.id} (dm_id: {job.dm_id}) reconciled as FAILED")

                await session.commit()


worker = BackgroundWorker()
