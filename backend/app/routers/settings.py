from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings as app_settings
from app.db import SessionLocal
from app.models import StrategyConfig
from app.security import require_auth
from app.services.bot_runner import get_or_create_config

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])


class StrategyConfigUpdate(BaseModel):
    symbols: list[str] | None = None
    timeframe: str | None = None
    take_profit_pct: float | None = None
    stop_loss_pct: float | None = None
    position_size_pct: float | None = None
    max_concurrent_positions: int | None = None
    orderbook_depth_levels: int | None = None
    orderbook_ratio_threshold: float | None = None
    volume_avg_lookback: int | None = None
    volume_ratio_threshold: float | None = None
    daily_loss_limit_pct: float | None = None


@router.get("")
async def get_settings():
    config = await get_or_create_config()
    return {
        "symbols": config.symbols,
        "timeframe": config.timeframe,
        "take_profit_pct": config.take_profit_pct,
        "stop_loss_pct": config.stop_loss_pct,
        "position_size_pct": config.position_size_pct,
        "max_concurrent_positions": config.max_concurrent_positions,
        "orderbook_depth_levels": config.orderbook_depth_levels,
        "orderbook_ratio_threshold": config.orderbook_ratio_threshold,
        "volume_avg_lookback": config.volume_avg_lookback,
        "volume_ratio_threshold": config.volume_ratio_threshold,
        "daily_loss_limit_pct": config.daily_loss_limit_pct,
        "okx_keys_configured": bool(app_settings.okx_api_key and app_settings.okx_api_secret
                                     and app_settings.okx_api_passphrase),
        "okx_demo": app_settings.okx_demo,
        "note": "تغيير قائمة الأزواج يتطلب إعادة تشغيل البوت من زر الإيقاف/التشغيل ليأخذ مفعوله. "
                "مفاتيح OKX تُدار من ملف backend/.env فقط ولا تُعرض أو تُعدَّل من هنا.",
    }


@router.put("")
async def update_settings(payload: StrategyConfigUpdate):
    async with SessionLocal() as session:
        result = await session.execute(select(StrategyConfig).where(StrategyConfig.id == 1))
        config = result.scalar_one_or_none() or StrategyConfig(id=1)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
        session.add(config)
        await session.commit()
    return {"ok": True}
