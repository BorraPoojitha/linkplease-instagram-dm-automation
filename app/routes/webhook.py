import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.rule import Rule
from app.models.event import Event
from app.models.processed_comment import ProcessedComment
from app.models.duplicate_log import DuplicateLog
from app.models.dm_job import DMJob
from app.services.signature import verify_webhook_signature
from app.services.matcher import matches_keyword

logger = logging.getLogger("linkplease.webhook")
router = APIRouter()


def parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.now(timezone.utc)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def process_webhook(
    raw_body: bytes = Depends(verify_webhook_signature),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return Response(content=json.dumps({"error": "invalid_json"}), status_code=400, media_type="application/json")

    event_id = payload.get("event_id")
    event_type = payload.get("event_type")
    sent_at_str = payload.get("sent_at")

    if not event_id or not event_type:
        return Response(content=json.dumps({"error": "missing_required_event_fields"}), status_code=400, media_type="application/json")

    data = payload.get("data", {})
    comment_id = data.get("comment_id")
    post_id = data.get("post_id")
    text = data.get("text")
    created_at_str = data.get("created_at")

    from_user = data.get("from") or {}
    user_id = from_user.get("user_id")
    username = from_user.get("username")

    sent_at_dt = parse_iso_datetime(sent_at_str)

    # 1. Persist event to enforce event_id uniqueness
    event_record = Event(
        event_id=event_id,
        event_type=event_type,
        comment_id=comment_id,
        post_id=post_id,
        user_id=user_id,
        username=username,
        comment_text=text,
        sent_at=sent_at_dt
    )

    try:
        db.add(event_record)
        await db.commit()
    except IntegrityError:
        # Duplicate event_id received! Ignore gracefully (return HTTP 200 quickly).
        # Requirement 3: Do NOT increment duplicates_blocked for duplicate event_ids.
        await db.rollback()
        logger.info(f"Duplicate event_id received: {event_id}. Event ignored.")
        return {"status": "ignored_duplicate_event", "event_id": event_id}

    # 2. Handle comment.deleted event
    if event_type == "comment.deleted":
        if comment_id:
            # Requirement 9: If related DM job is pending/processing/waiting_retry/accepted, cancel it.
            stmt = (
                update(DMJob)
                .where(
                    DMJob.comment_id == comment_id,
                    DMJob.status.in_(["pending", "processing", "waiting_retry", "accepted"])
                )
                .values(status="cancelled", updated_at=datetime.now(timezone.utc))
            )
            await db.execute(stmt)
            await db.commit()
            logger.info(f"Comment deleted event processed for comment_id {comment_id}. Active DM jobs cancelled.")
        return {"status": "comment_deleted_processed"}

    # 3. Handle comment.created event
    if event_type == "comment.created" and text and user_id and comment_id:
        # Fetch all active rules
        rules_stmt = select(Rule)
        rules_result = await db.execute(rules_stmt)
        rules = rules_result.scalars().all()

        for rule in rules:
            if matches_keyword(rule.keyword, text):
                claim_success = False
                try:
                    async with db.begin_nested():
                        pc = ProcessedComment(
                            rule_id=rule.id,
                            user_id=user_id,
                            first_comment_id=comment_id
                        )
                        db.add(pc)
                        await db.flush()
                    claim_success = True
                except IntegrityError:
                    claim_success = False

                if claim_success:
                    idempotency_key = f"ik_{rule.id}_{user_id}"
                    job = DMJob(
                        rule_id=rule.id,
                        user_id=user_id,
                        comment_id=comment_id,
                        message=rule.dm_message,
                        idempotency_key=idempotency_key,
                        status="pending"
                    )
                    db.add(job)
                    await db.commit()
                    logger.info(f"Rule match! Created DMJob for user {user_id}, rule {rule.id}")
                else:
                    dup_log = DuplicateLog(
                        rule_id=rule.id,
                        user_id=user_id,
                        comment_id=comment_id
                    )
                    db.add(dup_log)
                    await db.commit()
                    logger.info(f"Duplicate DM attempt blocked for user {user_id}, rule {rule.id}")

    return {"status": "ok", "event_id": event_id}
