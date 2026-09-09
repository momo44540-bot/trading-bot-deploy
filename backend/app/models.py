import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    quote_spent: Mapped[float] = mapped_column(Float)
    take_profit_price: Mapped[float] = mapped_column(Float)
    stop_loss_price: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String)  # paper | live
    status: Mapped[str] = mapped_column(String, default="open")  # open | closed
    entry_order_id: Mapped[str] = mapped_column(String, default="")
    entry_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    quote_spent: Mapped[float] = mapped_column(Float)
    pnl_quote: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    exit_reason: Mapped[str] = mapped_column(String)  # take_profit | stop_loss | manual | kill_switch
    mode: Mapped[str] = mapped_column(String)
    entry_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    exit_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StrategyConfig(Base):
    __tablename__ = "strategy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    symbols: Mapped[list] = mapped_column(JSON, default=list)
    timeframe: Mapped[str] = mapped_column(String, default="15m")
    take_profit_pct: Mapped[float] = mapped_column(Float, default=10.0)
    stop_loss_pct: Mapped[float] = mapped_column(Float, default=1.0)
    position_size_pct: Mapped[float] = mapped_column(Float, default=20.0)
    max_concurrent_positions: Mapped[int] = mapped_column(Integer, default=5)
    orderbook_depth_levels: Mapped[int] = mapped_column(Integer, default=20)
    orderbook_ratio_threshold: Mapped[float] = mapped_column(Float, default=1.0)
    volume_avg_lookback: Mapped[int] = mapped_column(Integer, default=20)
    volume_ratio_threshold: Mapped[float] = mapped_column(Float, default=1.0)
    daily_loss_limit_pct: Mapped[float] = mapped_column(Float, default=5.0)


class BotState(Base):
    __tablename__ = "bot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    running: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    trading_mode: Mapped[str] = mapped_column(String, default="paper")
    paper_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    daily_realized_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    daily_pnl_date: Mapped[str] = mapped_column(String, default="")
    daily_loss_limit_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DecisionLog(Base):
    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    decision: Mapped[str] = mapped_column(String)  # entry | reject | exit | info | error
    reason: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
