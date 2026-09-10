from dataclasses import dataclass, field

from app.strategy.indicators import Candle, compute_vwap, orderbook_pressure, volume_ratio


@dataclass
class SymbolMarketData:
    candles: list[Candle] = field(default_factory=list)
    bids: list[list[str]] = field(default_factory=list)
    asks: list[list[str]] = field(default_factory=list)
    last_price: float | None = None

    def add_candle(self, candle: Candle, is_update: bool) -> None:
        if is_update and self.candles and self.candles[-1].ts == candle.ts:
            self.candles[-1] = candle
        else:
            self.candles.append(candle)
            self.candles = self.candles[-200:]


class MarketDataStore:
    def __init__(self) -> None:
        self.symbols: dict[str, SymbolMarketData] = {}

    def get(self, symbol: str) -> SymbolMarketData:
        return self.symbols.setdefault(symbol, SymbolMarketData())


@dataclass
class EntrySignal:
    should_enter: bool
    price_above_vwap: bool | None
    vwap: float | None
    orderbook_ratio: float | None
    volume_ratio_value: float | None
    reason: str


@dataclass
class StrategyParams:
    # السعر فوق VWAP + تأكيد واحد على الأقل (حجم أو ضغط دفتر أوامر).
    orderbook_depth_levels: int = 20
    orderbook_ratio_threshold: float = 1.0
    volume_avg_lookback: int = 20
    volume_ratio_threshold: float = 1.0

    # حماية من الشراء بعد اندفاع السعر بعيدًا جدًا عن VWAP.
    max_distance_above_vwap_pct: float = 2.0


def evaluate_entry(data: SymbolMarketData, params: StrategyParams, *,
                    orderbook_required: bool = False) -> EntrySignal:
    if data.last_price is None or not data.candles:
        return EntrySignal(False, None, None, None, None, "insufficient_data")

    vwap = compute_vwap(data.candles)
    vol_ratio = volume_ratio(data.candles, lookback=params.volume_avg_lookback)
    ob_ratio = orderbook_pressure(data.bids, data.asks, depth=params.orderbook_depth_levels)

    if vwap is None:
        return EntrySignal(False, None, None, ob_ratio, vol_ratio, "vwap_unavailable")

    price_above_vwap = data.last_price > vwap
    distance_pct = ((data.last_price - vwap) / vwap * 100) if vwap else 999.0

    if not price_above_vwap:
        return EntrySignal(False, False, vwap, ob_ratio, vol_ratio, "price_below_vwap")

    if distance_pct > params.max_distance_above_vwap_pct:
        return EntrySignal(False, True, vwap, ob_ratio, vol_ratio, "price_too_far_above_vwap")

    volume_positive = vol_ratio is not None and vol_ratio >= params.volume_ratio_threshold
    orderbook_positive = ob_ratio is not None and ob_ratio >= params.orderbook_ratio_threshold

    # السعر فوق VWAP + (حجم جيد OR دفتر أوامر جيد).
    if not orderbook_required and volume_positive:
        return EntrySignal(True, True, vwap, ob_ratio, vol_ratio, "vwap_plus_volume")

    if orderbook_positive:
        return EntrySignal(True, True, vwap, ob_ratio, vol_ratio, "vwap_plus_orderbook")

    if vol_ratio is None and ob_ratio is None:
        reason = "no_confirmation_data"
    elif not volume_positive and not orderbook_positive:
        reason = "no_confirmation"
    else:
        reason = "confirmation_not_met"

    return EntrySignal(False, True, vwap, ob_ratio, vol_ratio, reason)


@dataclass
class ExitSignal:
    should_exit: bool
    reason: str
    pnl_pct: float


def evaluate_exit(entry_price: float, current_price: float, take_profit_pct: float,
                   stop_loss_pct: float) -> ExitSignal:
    pnl_pct = (current_price - entry_price) / entry_price * 100
    if pnl_pct >= take_profit_pct:
        return ExitSignal(True, "take_profit", pnl_pct)
    if pnl_pct <= -abs(stop_loss_pct):
        return ExitSignal(True, "stop_loss", pnl_pct)
    return ExitSignal(False, "hold", pnl_pct)
