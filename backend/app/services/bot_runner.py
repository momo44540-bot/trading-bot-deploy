import asyncio
import datetime as dt
import logging

from sqlalchemy import select

from app.db import SessionLocal
from app.models import BotState, DecisionLog, Position, StrategyConfig, Trade
from app.okx.client import OKXError, okx_client
from app.okx.ws_public import OKXPublicWS
from app.services.broadcaster import broadcaster
from app.strategy.engine import Candle, MarketDataStore, StrategyParams, evaluate_entry, evaluate_exit
from app.risk.risk_manager import RiskLimits, check_can_open, compute_position_quote_size, update_daily_loss_state
from app.utils import round_down_to_step

logger = logging.getLogger("bot_runner")


async def get_or_create_config() -> StrategyConfig:
    async with SessionLocal() as session:
        result = await session.execute(select(StrategyConfig).where(StrategyConfig.id == 1))
        config = result.scalar_one_or_none()
        if config is None:
            config = StrategyConfig(id=1, symbols=["BTC-USDT", "ETH-USDT", "SOL-USDT"])
            session.add(config)
            await session.commit()
            await session.refresh(config)
        return config


async def get_or_create_state() -> BotState:
    async with SessionLocal() as session:
        result = await session.execute(select(BotState).where(BotState.id == 1))
        state = result.scalar_one_or_none()
        if state is None:
            state = BotState(id=1)
            session.add(state)
            await session.commit()
            await session.refresh(state)
        return state


class BotRunner:
    def __init__(self) -> None:
        self.store = MarketDataStore()
        self.ws: OKXPublicWS | None = None
        self._running = False
        self._lock = asyncio.Lock()
        self.lot_size: dict[str, float] = {}
        self.min_size: dict[str, float] = {}
        self.symbols: list[str] = []

    async def _log(self, symbol: str, decision: str, reason: str, details: dict | None = None) -> None:
        async with SessionLocal() as session:
            session.add(DecisionLog(symbol=symbol, decision=decision, reason=reason, details=details or {}))
            await session.commit()
        await broadcaster.publish({
            "type": "decision", "symbol": symbol, "decision": decision,
            "reason": reason, "details": details or {},
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        })

    async def _load_all_usdt_symbols(self) -> list[str]:
        instruments = await okx_client.get_spot_usdt_instruments()
        self.lot_size = {}
        self.min_size = {}
        symbols: list[str] = []
        for item in instruments:
            symbol = item["instId"]
            symbols.append(symbol)
            try:
                self.lot_size[symbol] = float(item.get("lotSz") or 0)
                self.min_size[symbol] = float(item.get("minSz") or 0)
            except (TypeError, ValueError):
                pass
        return sorted(set(symbols))

    async def start(self) -> None:
        async with self._lock:
            if self._running:
                return
            config = await get_or_create_config()
            async with SessionLocal() as session:
                result = await session.execute(select(BotState).where(BotState.id == 1))
                state = result.scalar_one_or_none() or BotState(id=1)
                state.running = True
                session.add(state)
                await session.commit()

            try:
                self.symbols = await self._load_all_usdt_symbols()
            except OKXError as exc:
                await self._log("SYSTEM", "error", f"load_all_symbols_failed:{exc}", {})
                return

            if not self.symbols:
                await self._log("SYSTEM", "error", "no_live_usdt_spot_symbols", {})
                return

            semaphore = asyncio.Semaphore(10)

            async def preload(symbol: str) -> None:
                async with semaphore:
                    await self._preload_candles(symbol, config.timeframe)

            await asyncio.gather(*(preload(s) for s in self.symbols))

            self.ws = OKXPublicWS(self.symbols, self._on_ws_message, timeframe=config.timeframe)
            await self.ws.start()
            self._running = True
            await self._log("SYSTEM", "info", "bot_started_all_usdt_spot", {
                "symbols_count": len(self.symbols), "timeframe": config.timeframe,
                "strategy": "VWAP + volume OR orderbook",
            })

    async def stop(self) -> None:
        async with self._lock:
            if self.ws:
                await self.ws.stop()
                self.ws = None
            async with SessionLocal() as session:
                result = await session.execute(select(BotState).where(BotState.id == 1))
                state = result.scalar_one_or_none()
                if state:
                    state.running = False
                    session.add(state)
                    await session.commit()
            self._running = False
            await self._log("SYSTEM", "info", "bot_stopped", {})

    async def _preload_candles(self, symbol: str, timeframe: str) -> None:
        try:
            raw = await okx_client.get_candles(symbol, bar=timeframe, limit=100)
            data = self.store.get(symbol)
            candles = [Candle.from_okx(row) for row in reversed(raw)]
            data.candles = candles
            if candles:
                data.last_price = candles[-1].close
        except OKXError as exc:
            logger.warning("failed to preload candles for %s: %s", symbol, exc)

    async def _on_ws_message(self, msg: dict) -> None:
        channel = msg.get("arg", {}).get("channel")
        inst_id = msg.get("arg", {}).get("instId")
        if not channel or not inst_id:
            return
        data = self.store.get(inst_id)

        if channel.startswith("candle"):
            row = msg["data"][0]
            candle = Candle.from_okx(row)
            is_confirmed = row[-1] == "1"
            data.add_candle(candle, is_update=not is_confirmed)
            if is_confirmed:
                await self._evaluate_symbol(inst_id, signal_price=candle.close)

        elif channel == "tickers":
            ticker = msg["data"][0]
            data.last_price = float(ticker["last"])
            await self._check_exits(inst_id, data.last_price)

    async def _evaluate_symbol(self, symbol: str, signal_price: float | None = None) -> None:
        config = await get_or_create_config()
        state = await get_or_create_state()
        data = self.store.get(symbol)

        async with SessionLocal() as session:
            result = await session.execute(
                select(Position).where(Position.status == "open", Position.symbol == symbol)
            )
            existing = result.scalar_one_or_none()
        if existing is not None:
            return

        if signal_price is not None:
            original_price = data.last_price
            data.last_price = signal_price
        else:
            original_price = None

        params = StrategyParams(
            orderbook_depth_levels=config.orderbook_depth_levels,
            orderbook_ratio_threshold=config.orderbook_ratio_threshold,
            volume_avg_lookback=config.volume_avg_lookback,
            volume_ratio_threshold=config.volume_ratio_threshold,
            max_distance_above_vwap_pct=2.0,
        )

        # تقييم أولي: VWAP + الحجم فقط، بدون بث دفتر أوامر مستمر لكل عملة (غير عملي لمسح السوق كاملاً).
        signal = evaluate_entry(data, params)

        # إذا لم يكفِ الحجم، نمنح دفتر الأوامر فرصة تأكيد (جلب REST عند الحاجة فقط).
        if not signal.should_enter and signal.reason == "no_confirmation":
            try:
                book = await okx_client.get_order_book(symbol, depth=config.orderbook_depth_levels)
                data.bids = book.get("bids", [])
                data.asks = book.get("asks", [])
                signal = evaluate_entry(data, params, orderbook_required=True)
            except OKXError as exc:
                await self._log(symbol, "reject", "orderbook_fetch_failed", {"error": str(exc)})

        details = {
            "price": data.last_price, "vwap": signal.vwap,
            "orderbook_ratio": signal.orderbook_ratio, "volume_ratio": signal.volume_ratio_value,
        }
        if not signal.should_enter:
            await self._log(symbol, "reject", signal.reason, details)
            if original_price is not None:
                data.last_price = original_price
            return

        async with SessionLocal() as session:
            result = await session.execute(select(Position.symbol).where(Position.status == "open"))
            open_symbols = {row[0] for row in result.all()}

        limits = RiskLimits(
            position_size_pct=config.position_size_pct,
            max_concurrent_positions=config.max_concurrent_positions,
            daily_loss_limit_pct=config.daily_loss_limit_pct,
        )
        risk_decision = check_can_open(limits, symbol, open_symbols, state.kill_switch, state.daily_loss_limit_hit)
        if not risk_decision.allowed:
            await self._log(symbol, "reject", risk_decision.reason, details)
            if original_price is not None:
                data.last_price = original_price
            return

        await self._open_position(symbol, data.last_price, config, state, limits, signal.reason)
        if original_price is not None:
            data.last_price = original_price

    async def _open_position(self, symbol: str, price: float, config: StrategyConfig,
                              state: BotState, limits: RiskLimits, signal_reason: str) -> None:
        if state.trading_mode == "live":
            try:
                balance = await okx_client.get_balance("USDT")
                available = float(balance["details"][0]["availBal"]) if balance.get("details") else 0.0
            except (OKXError, KeyError, IndexError) as exc:
                await self._log(symbol, "error", f"balance_fetch_failed:{exc}", {})
                return
            equity = available
        else:
            available = state.paper_balance
            equity = state.paper_balance

        quote_size = compute_position_quote_size(equity, limits, available)
        if quote_size <= 0:
            await self._log(symbol, "reject", "insufficient_balance", {"available": available})
            return

        order_id = ""
        if state.trading_mode == "live":
            try:
                order = await okx_client.place_market_buy_quote(symbol, f"{quote_size:.2f}")
                order_id = order.get("ordId", "")
                filled = await self._poll_fill(symbol, order_id)
                if filled is None:
                    await self._log(symbol, "error", "order_fill_confirmation_timeout", {"order_id": order_id})
                    return
                fill_price, base_size = filled
            except OKXError as exc:
                await self._log(symbol, "error", f"order_failed:{exc}", {})
                return
        else:
            fill_price = price
            base_size = quote_size / price

        tp_price = fill_price * (1 + config.take_profit_pct / 100)
        sl_price = fill_price * (1 - config.stop_loss_pct / 100)

        async with SessionLocal() as session:
            position = Position(
                symbol=symbol, entry_price=fill_price, size=base_size, quote_spent=quote_size,
                take_profit_price=tp_price, stop_loss_price=sl_price,
                mode=state.trading_mode, status="open", entry_order_id=order_id,
            )
            session.add(position)
            if state.trading_mode == "paper":
                result = await session.execute(select(BotState).where(BotState.id == 1))
                db_state = result.scalar_one()
                db_state.paper_balance -= quote_size
                session.add(db_state)
            await session.commit()

        await self._log(symbol, "entry", signal_reason, {
            "entry_price": fill_price, "size": base_size, "quote_spent": quote_size,
            "take_profit_price": tp_price, "stop_loss_price": sl_price, "mode": state.trading_mode,
        })
        await broadcaster.publish({"type": "position_opened", "symbol": symbol})

    async def _poll_fill(self, symbol: str, order_id: str, attempts: int = 8) -> tuple[float, float] | None:
        for _ in range(attempts):
            await asyncio.sleep(1)
            try:
                order = await okx_client.get_order(symbol, order_id)
            except OKXError:
                continue
            if order.get("state") == "filled":
                return float(order["avgPx"]), float(order["accFillSz"])
        return None

    async def _check_exits(self, symbol: str, current_price: float) -> None:
        async with SessionLocal() as session:
            result = await session.execute(
                select(Position).where(Position.status == "open", Position.symbol == symbol)
            )
            position = result.scalar_one_or_none()
        if position is None:
            return

        config = await get_or_create_config()
        exit_signal = evaluate_exit(position.entry_price, current_price,
                                     config.take_profit_pct, config.stop_loss_pct)
        if exit_signal.should_exit:
            await self._close_position(position, current_price, exit_signal.reason, exit_signal.pnl_pct)

    async def _close_position(self, position: Position, exit_price: float, reason: str, pnl_pct: float) -> None:
        state = await get_or_create_state()

        if state.trading_mode == "live":
            try:
                lot_size = self.lot_size.get(position.symbol)
                sell_size = round_down_to_step(position.size, lot_size) if lot_size else position.size
                if sell_size <= 0:
                    await self._log(position.symbol, "error", "sell_size_below_lot_size",
                                     {"size": position.size, "lot_size": lot_size})
                    return
                order = await okx_client.place_market_sell_base(position.symbol, f"{sell_size:.8f}")
                order_id = order.get("ordId", "")
                filled = await self._poll_fill(position.symbol, order_id)
                if filled is None:
                    await self._log(position.symbol, "error", "exit_fill_confirmation_timeout",
                                     {"order_id": order_id})
                    return
                exit_price = filled[0]
            except OKXError as exc:
                await self._log(position.symbol, "error", f"exit_order_failed:{exc}", {})
                return

        pnl_quote = (exit_price - position.entry_price) * position.size
        realized_pct = (exit_price - position.entry_price) / position.entry_price * 100
        config = await get_or_create_config()
        # تحويل عائد الصفقة إلى مساهمة تقريبية على مستوى المحفظة، لأغراض حد الخسارة اليومي.
        portfolio_pnl_pct = realized_pct * config.position_size_pct / 100

        async with SessionLocal() as session:
            db_position = await session.get(Position, position.id)
            db_position.status = "closed"
            session.add(Trade(
                symbol=position.symbol, entry_price=position.entry_price, exit_price=exit_price,
                size=position.size, quote_spent=position.quote_spent, pnl_quote=pnl_quote,
                pnl_pct=realized_pct, exit_reason=reason, mode=position.mode,
                entry_time=position.entry_time,
            ))
            result = await session.execute(select(BotState).where(BotState.id == 1))
            db_state = result.scalar_one()
            if position.mode == "paper":
                db_state.paper_balance += position.quote_spent + pnl_quote

            today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            if db_state.daily_pnl_date != today:
                db_state.daily_pnl_date = today
                db_state.daily_realized_pnl_pct = 0.0
                db_state.daily_loss_limit_hit = False
            db_state.daily_realized_pnl_pct += portfolio_pnl_pct
            limits = RiskLimits(daily_loss_limit_pct=config.daily_loss_limit_pct)
            db_state.daily_loss_limit_hit = update_daily_loss_state(db_state.daily_realized_pnl_pct, limits)
            session.add(db_state)
            await session.commit()

        await self._log(position.symbol, "exit", reason, {
            "exit_price": exit_price, "pnl_quote": pnl_quote, "pnl_pct": realized_pct,
            "portfolio_pnl_pct": portfolio_pnl_pct,
        })
        await broadcaster.publish({"type": "position_closed", "symbol": position.symbol, "reason": reason})

    async def close_all_positions(self, reason: str = "manual") -> None:
        async with SessionLocal() as session:
            result = await session.execute(select(Position).where(Position.status == "open"))
            positions = result.scalars().all()
        for position in positions:
            data = self.store.get(position.symbol)
            price = data.last_price or position.entry_price
            pnl_pct = (price - position.entry_price) / position.entry_price * 100
            await self._close_position(position, price, reason, pnl_pct)


bot_runner = BotRunner()
