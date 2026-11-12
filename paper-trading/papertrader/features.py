"""Price features computed in code, so Claude reasons over numbers it did not have
to calculate itself."""

from __future__ import annotations

import math
from typing import Sequence


def _sma(values: Sequence[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def _ret(values: Sequence[float], n: int) -> float | None:
    if len(values) <= n or values[-n - 1] <= 0:
        return None
    return values[-1] / values[-n - 1] - 1


def _annualized_vol(values: Sequence[float], n: int) -> float | None:
    if len(values) <= n:
        return None
    window = values[-n - 1:]
    rets = [math.log(b / a) for a, b in zip(window, window[1:]) if a > 0 and b > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def _round(x: float | None, places: int = 4) -> float | None:
    return None if x is None else round(x, places)


def compute_features(daily_closes: Sequence[float], last_price: float | None) -> dict:
    """Trend and risk numbers for one symbol from its daily closes (oldest first).

    ``last_price`` is the latest trade, used as "today's" price when available.
    """
    closes = [float(c) for c in daily_closes if c is not None and float(c) > 0]
    price = float(last_price) if last_price and last_price > 0 else (closes[-1] if closes else None)
    if price is None:
        return {"price": None, "enough_history": False}

    series = closes + [price] if last_price and closes else closes
    sma20 = _sma(series, 20)
    sma50 = _sma(series, 50)
    high = max(series) if series else None

    return {
        "price": round(price, 4),
        "sma20": _round(sma20),
        "sma50": _round(sma50),
        "above_sma50": None if sma50 is None else price > sma50,
        "sma20_above_sma50": None if sma20 is None or sma50 is None else sma20 > sma50,
        "return_5d": _round(_ret(series, 5)),
        "return_21d": _round(_ret(series, 21)),
        "return_63d": _round(_ret(series, 63)),
        "vol_20d_annualized": _round(_annualized_vol(series, 20)),
        "pct_below_window_high": None if not high else _round(1 - price / high),
        "days_of_history": len(closes),
        "enough_history": sma50 is not None and len(series) > 63,
    }
