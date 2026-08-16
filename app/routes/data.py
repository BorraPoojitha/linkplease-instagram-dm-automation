from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.models.dm_job import DMJob
from app.models.event import Event

router = APIRouter()


class JobOut(BaseModel):
    id: str
    rule_id: str
    user_id: str
    comment_id: str
    message: str
    status: str
    attempts: int
    dm_id: Optional[str] = None
    last_error: Optional[str] = None
    created_at: str
    updated_at: str


class EventOut(BaseModel):
    event_id: str
    event_type: str
    comment_id: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    comment_text: Optional[str] = None
    created_at: str


@router.get("/jobs", response_model=List[JobOut])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    stmt = select(DMJob).order_by(DMJob.created_at.desc()).limit(100)
    res = await db.execute(stmt)
    jobs = res.scalars().all()
    return [
        JobOut(
            id=j.id,
            rule_id=j.rule_id,
            user_id=j.user_id,
            comment_id=j.comment_id,
            message=j.message,
            status=j.status,
            attempts=j.attempts,
            dm_id=j.dm_id,
            last_error=j.last_error,
            created_at=j.created_at.isoformat() if j.created_at else "",
            updated_at=j.updated_at.isoformat() if j.updated_at else ""
        )
        for j in jobs
    ]


@router.get("/events", response_model=List[EventOut])
async def list_events(db: AsyncSession = Depends(get_db)):
    stmt = select(Event).order_by(Event.created_at.desc()).limit(100)
    res = await db.execute(stmt)
    events = res.scalars().all()
    return [
        EventOut(
            event_id=e.event_id,
            event_type=e.event_type,
            comment_id=e.comment_id,
            user_id=e.user_id,
            username=e.username,
            comment_text=e.comment_text,
            created_at=e.created_at.isoformat() if e.created_at else ""
        )
        for e in events
    ]
