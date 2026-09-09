import datetime as dt

from app.strategy.indicators import Candle, compute_vwap, orderbook_pressure, volume_ratio


def make_candle(hour: int, close: float, volume: float) -> Candle:
    ts = dt.datetime(2026, 1, 1, hour, 0, tzinfo=dt.timezone.utc)
    return Candle(ts=ts, open=close, high=close, low=close, close=close, volume=volume)


def test_vwap_basic():
    candles = [make_candle(0, 100, 10), make_candle(1, 110, 20)]
    vwap = compute_vwap(candles)
    expected = (100 * 10 + 110 * 20) / 30
    assert abs(vwap - expected) < 1e-9


def test_vwap_resets_at_session_anchor():
    yesterday = dt.datetime(2025, 12, 31, 23, 0, tzinfo=dt.timezone.utc)
    today = dt.datetime(2026, 1, 1, 1, 0, tzinfo=dt.timezone.utc)
    candles = [
        Candle(ts=yesterday, open=1, high=1, low=1, close=1, volume=1000),
        Candle(ts=today, open=200, high=200, low=200, close=200, volume=10),
    ]
    vwap = compute_vwap(candles)
    assert abs(vwap - 200) < 1e-9


def test_volume_ratio_above_average():
    candles = [make_candle(h, 100, 10) for h in range(20)] + [make_candle(20, 100, 30)]
    ratio = volume_ratio(candles, lookback=20)
    assert abs(ratio - 3.0) < 1e-9


def test_volume_ratio_insufficient_data():
    candles = [make_candle(0, 100, 10)]
    assert volume_ratio(candles, lookback=20) is None


def test_orderbook_pressure_buy_dominant():
    bids = [["100", "5"], ["99", "5"]]
    asks = [["101", "2"], ["102", "2"]]
    ratio = orderbook_pressure(bids, asks, depth=20)
    assert abs(ratio - 2.5) < 1e-9


def test_orderbook_pressure_zero_ask_volume():
    bids = [["100", "5"]]
    asks = [["101", "0"]]
    assert orderbook_pressure(bids, asks) is None
