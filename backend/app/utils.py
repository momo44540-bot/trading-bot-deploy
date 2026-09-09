from decimal import ROUND_DOWN, Decimal


def round_down_to_step(value: float, step: float) -> float:
    """يقرّب value لأسفل لأقرب مضاعف لـ step (مطلوب لتحقيق lotSz في أوامر OKX)."""
    if step <= 0:
        return value
    d_value = Decimal(str(value))
    d_step = Decimal(str(step))
    rounded = (d_value / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step
    return float(rounded)
