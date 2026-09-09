import datetime as dt
from dataclasses import dataclass


@dataclass
class Candle:
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_okx(cls, row: list[str]) -> "Candle":
        # OKX candle row: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        ts = dt.datetime.fromtimestamp(int(row[0]) / 1000, tz=dt.timezone.utc)
        return cls(ts=ts, open=float(row[1]), high=float(row[2]), low=float(row[3]),
                    close=float(row[4]), volume=float(row[5]))


def session_anchor(now: dt.datetime) -> dt.datetime:
    return now.astimezone(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def compute_vwap(candles: list[Candle], anchor: dt.datetime | None = None) -> float | None:
    """VWAP مرجّح بالحجم، محسوب من الشموع منذ anchor (افتراضيًا بداية اليوم UTC)."""
    if not candles:
        return None
    if anchor is None:
        anchor = session_anchor(candles[-1].ts)
    session_candles = [c for c in candles if c.ts >= anchor]
    if not session_candles:
        session_candles = candles[-1:]
    cum_pv = 0.0
    cum_v = 0.0
    for c in session_candles:
        typical_price = (c.high + c.low + c.close) / 3
        cum_pv += typical_price * c.volume
        cum_v += c.volume
    if cum_v == 0:
        return None
    return cum_pv / cum_v


def volume_ratio(candles: list[Candle], lookback: int = 20) -> float | None:
    """نسبة حجم آخر شمعة مغلقة إلى متوسط حجم الشموع السابقة (lookback)."""
    if len(candles) < lookback + 1:
        return None
    current = candles[-1]
    prior = candles[-(lookback + 1):-1]
    avg_volume = sum(c.volume for c in prior) / len(prior)
    if avg_volume == 0:
        return None
    return current.volume / avg_volume


def orderbook_pressure(bids: list[list[str]], asks: list[list[str]], depth: int = 20) -> float | None:
    """نسبة مجموع أحجام الشراء إلى مجموع أحجام البيع لأفضل `depth` مستوى.
    bids/asks بصيغة OKX: [[price, size, liquidated_orders, num_orders], ...]
    """
    bid_vol = sum(float(level[1]) for level in bids[:depth])
    ask_vol = sum(float(level[1]) for level in asks[:depth])
    if ask_vol == 0:
        return None
    return bid_vol / ask_vol
