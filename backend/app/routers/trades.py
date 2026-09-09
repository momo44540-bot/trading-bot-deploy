from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.db import SessionLocal
from app.models import DecisionLog, Trade
from app.security import require_auth

router = APIRouter(prefix="/api/trades", tags=["trades"], dependencies=[Depends(require_auth)])


@router.get("")
async def list_trades(limit: int = 100):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Trade).order_by(Trade.exit_time.desc()).limit(limit)
        )
        trades = result.scalars().all()
    return [
        {
            "id": t.id, "symbol": t.symbol, "entry_price": t.entry_price, "exit_price": t.exit_price,
            "size": t.size, "quote_spent": t.quote_spent, "pnl_quote": t.pnl_quote, "pnl_pct": t.pnl_pct,
            "exit_reason": t.exit_reason, "mode": t.mode, "entry_time": t.entry_time, "exit_time": t.exit_time,
        }
        for t in trades
    ]


@router.get("/logs")
async def list_logs(limit: int = 200):
    async with SessionLocal() as session:
        result = await session.execute(
            select(DecisionLog).order_by(DecisionLog.timestamp.desc()).limit(limit)
        )
        logs = result.scalars().all()
    return [
        {
            "id": l.id, "timestamp": l.timestamp, "symbol": l.symbol,
            "decision": l.decision, "reason": l.reason, "details": l.details,
        }
        for l in logs
    ]
