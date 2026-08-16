from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.dm_job import DMJob
from app.models.duplicate_log import DuplicateLog
from app.schemas import StatsResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # 1. Count sent (delivered)
    sent_stmt = select(func.count()).select_from(DMJob).where(DMJob.status == "delivered")
    sent_res = await db.execute(sent_stmt)
    sent = sent_res.scalar_one_or_none() or 0

    # 2. Count failed
    failed_stmt = select(func.count()).select_from(DMJob).where(DMJob.status == "failed")
    failed_res = await db.execute(failed_stmt)
    failed = failed_res.scalar_one_or_none() or 0

    # 3. Count queued (pending, processing, waiting_retry, accepted)
    queued_stmt = select(func.count()).select_from(DMJob).where(
        DMJob.status.in_(["pending", "processing", "waiting_retry", "accepted"])
    )
    queued_res = await db.execute(queued_stmt)
    queued = queued_res.scalar_one_or_none() or 0

    # 4. Count duplicates_blocked
    dup_stmt = select(func.count()).select_from(DuplicateLog)
    dup_res = await db.execute(dup_stmt)
    duplicates_blocked = dup_res.scalar_one_or_none() or 0

    return StatsResponse(
        sent=sent,
        failed=failed,
        queued=queued,
        duplicates_blocked=duplicates_blocked
    )
