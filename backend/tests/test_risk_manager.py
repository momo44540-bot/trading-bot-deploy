from app.risk.risk_manager import RiskLimits, check_can_open, compute_position_quote_size, update_daily_loss_state


def test_check_can_open_ok():
    limits = RiskLimits(max_concurrent_positions=5)
    decision = check_can_open(limits, "BTC-USDT", set(), kill_switch=False, daily_loss_limit_hit=False)
    assert decision.allowed


def test_check_can_open_blocked_by_kill_switch():
    limits = RiskLimits()
    decision = check_can_open(limits, "BTC-USDT", set(), kill_switch=True, daily_loss_limit_hit=False)
    assert not decision.allowed
    assert decision.reason == "kill_switch_active"


def test_check_can_open_blocked_by_daily_loss_limit():
    limits = RiskLimits()
    decision = check_can_open(limits, "BTC-USDT", set(), kill_switch=False, daily_loss_limit_hit=True)
    assert not decision.allowed
    assert decision.reason == "daily_loss_limit_hit"


def test_check_can_open_blocked_symbol_already_open():
    limits = RiskLimits()
    decision = check_can_open(limits, "BTC-USDT", {"BTC-USDT"}, kill_switch=False, daily_loss_limit_hit=False)
    assert not decision.allowed
    assert decision.reason == "position_already_open_for_symbol"


def test_check_can_open_blocked_max_concurrent():
    limits = RiskLimits(max_concurrent_positions=2)
    open_symbols = {"BTC-USDT", "ETH-USDT"}
    decision = check_can_open(limits, "SOL-USDT", open_symbols, kill_switch=False, daily_loss_limit_hit=False)
    assert not decision.allowed
    assert decision.reason == "max_concurrent_positions_reached"


def test_compute_position_quote_size_within_balance():
    limits = RiskLimits(position_size_pct=20.0)
    size = compute_position_quote_size(equity=1000, limits=limits, available_quote_balance=5000)
    assert abs(size - 200) < 1e-9


def test_compute_position_quote_size_capped_by_available_balance():
    limits = RiskLimits(position_size_pct=20.0)
    size = compute_position_quote_size(equity=1000, limits=limits, available_quote_balance=50)
    assert size == 50


def test_daily_loss_limit_triggers_at_threshold():
    limits = RiskLimits(daily_loss_limit_pct=5.0)
    assert update_daily_loss_state(-5.0, limits) is True
    assert update_daily_loss_state(-4.9, limits) is False
    assert update_daily_loss_state(2.0, limits) is False
