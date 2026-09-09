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
    orderbook_depth_levels: int = 20
    orderbook_ratio_threshold: float = 1.0
    volume_avg_lookback: int = 20
    volume_ratio_threshold: float = 1.0


def evaluate_entry(data: SymbolMarketData, params: StrategyParams) -> EntrySignal:
    if data.last_price is None or not data.candles:
        return EntrySignal(False, None, None, None, None, "insufficient_data")

    vwap = compute_vwap(data.candles)
    vol_ratio = volume_ratio(data.candles, lookback=params.volume_avg_lookback)
    ob_ratio = orderbook_pressure(data.bids, data.asks, depth=params.orderbook_depth_levels)

    if vwap is None or vol_ratio is None or ob_ratio is None:
        return EntrySignal(False, None, vwap, ob_ratio, vol_ratio, "insufficient_data")

    price_above_vwap = data.last_price > vwap
    orderbook_positive = ob_ratio > params.orderbook_ratio_threshold
    volume_positive = vol_ratio > params.volume_ratio_threshold

    should_enter = price_above_vwap and orderbook_positive and volume_positive
    if should_enter:
        reason = "all_conditions_met"
    else:
        failed = []
        if not price_above_vwap:
            failed.append("price_below_vwap")
        if not orderbook_positive:
            failed.append("orderbook_pressure_not_positive")
        if not volume_positive:
            failed.append("volume_not_above_average")
        reason = ",".join(failed)

    return EntrySignal(should_enter, price_above_vwap, vwap, ob_ratio, vol_ratio, reason)


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
