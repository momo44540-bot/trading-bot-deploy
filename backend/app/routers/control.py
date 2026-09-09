from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.db import SessionLocal
from app.models import BotState
from app.security import require_auth
from app.services.bot_runner import bot_runner, get_or_create_state

router = APIRouter(prefix="/api/control", tags=["control"], dependencies=[Depends(require_auth)])


@router.get("/status")
async def status():
    state = await get_or_create_state()
    return {
        "running": state.running,
        "kill_switch": state.kill_switch,
        "trading_mode": state.trading_mode,
    }


@router.post("/start")
async def start():
    await bot_runner.start()
    return {"ok": True}


@router.post("/stop")
async def stop():
    await bot_runner.stop()
    return {"ok": True}


class KillSwitchRequest(BaseModel):
    enabled: bool
    close_positions: bool = False


@router.post("/kill-switch")
async def kill_switch(payload: KillSwitchRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(BotState).where(BotState.id == 1))
        state = result.scalar_one_or_none() or BotState(id=1)
        state.kill_switch = payload.enabled
        session.add(state)
        await session.commit()
    if payload.enabled and payload.close_positions:
        await bot_runner.close_all_positions(reason="kill_switch")
    return {"ok": True}


class ModeRequest(BaseModel):
    mode: str


@router.post("/mode")
async def set_mode(payload: ModeRequest):
    if payload.mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="invalid_mode")
    async with SessionLocal() as session:
        result = await session.execute(select(BotState).where(BotState.id == 1))
        state = result.scalar_one_or_none() or BotState(id=1)
        state.trading_mode = payload.mode
        session.add(state)
        await session.commit()
    return {"ok": True}


@router.post("/close-all")
async def close_all():
    await bot_runner.close_all_positions(reason="manual")
    return {"ok": True}
