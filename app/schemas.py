from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Rule Schemas
class RuleCreate(BaseModel):
    keyword: str = Field(..., min_length=1)
    dm_message: str = Field(..., min_length=1)


class RuleResponse(BaseModel):
    rule_id: str
    keyword: str
    dm_message: str

    model_config = {"from_attributes": True}



# Webhook Schemas
class UserData(BaseModel):
    user_id: str
    username: Optional[str] = None


class CommentData(BaseModel):
    comment_id: str
    post_id: Optional[str] = None
    text: Optional[str] = None
    created_at: Optional[str] = None
    from_user: Optional[UserData] = Field(default=None, alias="from")


class WebhookPayload(BaseModel):
    event_id: str
    event_type: str
    sent_at: Optional[str] = None
    data: CommentData


# Stats Schema
class StatsResponse(BaseModel):
    sent: int
    failed: int
    queued: int
    duplicates_blocked: int
