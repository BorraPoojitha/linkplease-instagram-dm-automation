from typing import AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, select, func
from app.config import settings

# Check if using SQLite or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

if is_sqlite:
    # Enable Write-Ahead Logging (WAL) mode for concurrent read/write performance in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.models.rule import Rule
    from app.models.event import Event
    from app.models.dm_job import DMJob
    from app.models.processed_comment import ProcessedComment

    async with AsyncSessionLocal() as session:
        # Seed default rules if missing
        rule_count = await session.scalar(select(func.count(Rule.id)))
        if rule_count == 0:
            default_rules = [
                Rule(id="rule_price", keyword="PRICE", dm_message="Here is our full pricing catalog: https://example.com/pricing. Use code WELCOME10 for 10% off!"),
                Rule(id="rule_link", keyword="LINK", dm_message="Access the link to our latest course here: https://example.com/course"),
                Rule(id="rule_discount", keyword="DISCOUNT", dm_message="Exclusive 25% discount code: SAVE25. Valid for the next 24 hours!"),
                Rule(id="rule_demo", keyword="DEMO", dm_message="Book your live 1-on-1 demo call here: https://example.com/demo"),
                Rule(id="rule_info", keyword="INFO", dm_message="Here are all product specifications and brochure: https://example.com/info"),
            ]
            session.add_all(default_rules)

        # Seed default events if missing
        event_count = await session.scalar(select(func.count(Event.id)))
        if event_count == 0:
            now = datetime.now(timezone.utc)
            sample_events = [
                Event(id="evt_auto_1", event_type="comment.created", raw_payload='{"text":"Send me the PRICE please"}', received_at=now),
                Event(id="evt_auto_2", event_type="comment.created", raw_payload='{"text":"I need the LINK"}', received_at=now),
                Event(id="evt_auto_3", event_type="comment.created", raw_payload='{"text":"Any DISCOUNT code?"}', received_at=now),
                Event(id="evt_auto_4", event_type="comment.created", raw_payload='{"text":"Book a DEMO"}', received_at=now),
                Event(id="evt_auto_5", event_type="comment.created", raw_payload='{"text":"DM me INFO"}', received_at=now),
            ]
            session.add_all(sample_events)

        # Seed default jobs if missing
        job_count = await session.scalar(select(func.count(DMJob.id)))
        if job_count == 0:
            now = datetime.now(timezone.utc)
            sample_processed = [
                ProcessedComment(rule_id="rule_price", user_id="usr_alice_1", comment_id="cmt_1", processed_at=now),
                ProcessedComment(rule_id="rule_link", user_id="usr_bob_2", comment_id="cmt_2", processed_at=now),
                ProcessedComment(rule_id="rule_discount", user_id="usr_charlie_3", comment_id="cmt_3", processed_at=now),
            ]
            session.add_all(sample_processed)

            sample_jobs = [
                DMJob(id="job_auto_1", rule_id="rule_price", user_id="usr_alice_1", comment_id="cmt_1", message="Here is our full pricing catalog: https://example.com/pricing. Use code WELCOME10 for 10% off!", status="delivered", idempotency_key="ik_rule_price_usr_alice_1", attempts=1, dm_id="dm_101", created_at=now, updated_at=now),
                DMJob(id="job_auto_2", rule_id="rule_link", user_id="usr_bob_2", comment_id="cmt_2", message="Access the link to our latest course here: https://example.com/course", status="delivered", idempotency_key="ik_rule_link_usr_bob_2", attempts=1, dm_id="dm_102", created_at=now, updated_at=now),
                DMJob(id="job_auto_3", rule_id="rule_discount", user_id="usr_charlie_3", comment_id="cmt_3", message="Exclusive 25% discount code: SAVE25. Valid for the next 24 hours!", status="accepted", idempotency_key="ik_rule_discount_usr_charlie_3", attempts=1, dm_id="dm_103", created_at=now, updated_at=now),
                DMJob(id="job_auto_4", rule_id="rule_demo", user_id="usr_david_4", comment_id="cmt_4", message="Book your live 1-on-1 demo call here: https://example.com/demo", status="pending", idempotency_key="ik_rule_demo_usr_david_4", attempts=0, created_at=now, updated_at=now),
                DMJob(id="job_auto_5", rule_id="rule_info", user_id="usr_emma_5", comment_id="cmt_5", message="Here are all product specifications and brochure: https://example.com/info", status="pending", idempotency_key="ik_rule_info_usr_emma_5", attempts=0, created_at=now, updated_at=now),
            ]
            session.add_all(sample_jobs)

        await session.commit()
