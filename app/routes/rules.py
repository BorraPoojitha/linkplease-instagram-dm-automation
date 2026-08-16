from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.rule import Rule
from app.schemas import RuleCreate, RuleResponse

router = APIRouter()


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule_in: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = Rule(
        keyword=rule_in.keyword,
        dm_message=rule_in.dm_message
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return RuleResponse(
        rule_id=rule.id,
        keyword=rule.keyword,
        dm_message=rule.dm_message
    )


@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    stmt = select(Rule).order_by(Rule.created_at.desc())
    res = await db.execute(stmt)
    rules = res.scalars().all()
    return [
        RuleResponse(
            rule_id=r.id,
            keyword=r.keyword,
            dm_message=r.dm_message
        )
        for r in rules
    ]
