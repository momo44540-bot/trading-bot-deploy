from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.db import SessionLocal
from app.models import BotState, Position
from app.okx.client import OKXError, okx_client
from app.security import require_auth
from app.services.bot_runner import bot_runner, get_or_create_state

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_auth)])


@router.get("")
async def get_dashboard():
    state = await get_or_create_state()

    async with SessionLocal() as session:
        result = await session.execute(select(Position).where(Position.status == "open"))
        positions = result.scalars().all()

    open_positions = []
    for p in positions:
        data = bot_runner.store.get(p.symbol)
        current_price = data.last_price or p.entry_price
        unrealized_pct = (current_price - p.entry_price) / p.entry_price * 100
        open_positions.append({
            "id": p.id, "symbol": p.symbol, "entry_price": p.entry_price,
            "current_price": current_price, "size": p.size, "quote_spent": p.quote_spent,
            "take_profit_price": p.take_profit_price, "stop_loss_price": p.stop_loss_price,
            "unrealized_pct": unrealized_pct, "entry_time": p.entry_time, "mode": p.mode,
        })

    if state.trading_mode == "live":
        try:
            balance = await okx_client.get_balance("USDT")
            available_balance = float(balance["details"][0]["availBal"]) if balance.get("details") else 0.0
        except (OKXError, KeyError, IndexError):
            available_balance = None
    else:
        available_balance = state.paper_balance

    return {
        "running": state.running,
        "kill_switch": state.kill_switch,
        "trading_mode": state.trading_mode,
        "available_balance": available_balance,
        "daily_realized_pnl_pct": state.daily_realized_pnl_pct,
        "daily_loss_limit_hit": state.daily_loss_limit_hit,
        "open_positions": open_positions,
    }
