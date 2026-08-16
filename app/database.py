from typing import AsyncGenerator
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

    # Auto-seed default rules if database is newly initialized
    from app.models.rule import Rule
    async with AsyncSessionLocal() as session:
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
            await session.commit()
