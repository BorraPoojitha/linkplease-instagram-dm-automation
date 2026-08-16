import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"rule_{uuid.uuid4().hex[:12]}")
    keyword: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    dm_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
