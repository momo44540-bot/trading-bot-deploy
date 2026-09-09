from dataclasses import dataclass


@dataclass
class RiskLimits:
    position_size_pct: float = 20.0
    max_concurrent_positions: int = 5
    daily_loss_limit_pct: float = 5.0


@dataclass
class RiskDecision:
    allowed: bool
    reason: str


def check_can_open(
    limits: RiskLimits,
    symbol: str,
    open_symbols: set[str],
    kill_switch: bool,
    daily_loss_limit_hit: bool,
) -> RiskDecision:
    if kill_switch:
        return RiskDecision(False, "kill_switch_active")
    if daily_loss_limit_hit:
        return RiskDecision(False, "daily_loss_limit_hit")
    if symbol in open_symbols:
        return RiskDecision(False, "position_already_open_for_symbol")
    if len(open_symbols) >= limits.max_concurrent_positions:
        return RiskDecision(False, "max_concurrent_positions_reached")
    return RiskDecision(True, "ok")


def compute_position_quote_size(equity: float, limits: RiskLimits, available_quote_balance: float) -> float:
    """يحسب مبلغ الشراء بعملة التسعير (USDT) كنسبة من رأس المال، بحد أقصى الرصيد المتاح فعليًا."""
    target = equity * (limits.position_size_pct / 100)
    return min(target, available_quote_balance)


def update_daily_loss_state(daily_realized_pnl_pct: float, limits: RiskLimits) -> bool:
    """يعيد True إذا تجاوزت الخسارة اليومية المتراكمة الحد المسموح (يوقف دخول صفقات جديدة)."""
    return daily_realized_pnl_pct <= -abs(limits.daily_loss_limit_pct)
