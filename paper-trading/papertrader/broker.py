"""Talking to Alpaca: the paper account, prices, and order submission.

``AlpacaBroker`` uses the real Alpaca paper API. ``MockBroker`` has the same
methods with made-up data, so the whole pipeline can be exercised with no keys.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .safety import assert_paper, make_paper_trading_client

NEW_YORK = ZoneInfo("America/New_York")


@dataclass
class PlannedOrder:
    """An order that passed every limit in risk.py. Exactly one of notional/qty is set."""

    symbol: str
    side: str                 # "buy" or "sell"
    est_dollars: float        # what the order is expected to cost or raise
    reason: str
    notional: float | None = None
    qty: float | None = None
    client_order_id: str = ""

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "notional": self.notional,
            "qty": self.qty,
            "est_dollars": round(self.est_dollars, 2),
            "reason": self.reason,
            "client_order_id": self.client_order_id,
        }


def _f(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _enum_value(x) -> str:
    return str(getattr(x, "value", x))


class AlpacaBroker:
    def __init__(self, api_key: str, secret_key: str):
        from alpaca.data.historical import StockHistoricalDataClient

        self.trading = make_paper_trading_client(api_key, secret_key)
        # Market data is read-only and the same for paper and live accounts.
        self.data = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)

    # ------------------------------------------------------------------ reads
    def snapshot(self) -> dict:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        acct = self.trading.get_account()
        clock = self.trading.get_clock()
        positions = self.trading.get_all_positions()
        open_orders = self.trading.get_orders(
            filter=GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=500)
        )
        recent = self.trading.get_orders(
            filter=GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                after=datetime.now(timezone.utc) - timedelta(days=7),
                limit=100,
            )
        )
        return {
            "account": {
                "status": _enum_value(acct.status),
                "equity": _f(acct.equity),
                "last_equity": _f(acct.last_equity),
                "cash": _f(acct.cash),
                "buying_power": _f(acct.buying_power),
                "long_market_value": _f(acct.long_market_value),
                "trading_blocked": bool(acct.trading_blocked),
                "account_blocked": bool(acct.account_blocked),
                "trade_suspended_by_user": bool(acct.trade_suspended_by_user),
                "pattern_day_trader": bool(acct.pattern_day_trader),
                "daytrade_count": acct.daytrade_count or 0,
            },
            "clock": {
                "is_open": bool(clock.is_open),
                "timestamp": clock.timestamp.isoformat(),
                "next_open": clock.next_open.isoformat(),
                "next_close": clock.next_close.isoformat(),
            },
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": _enum_value(p.side),
                    "qty": _f(p.qty),
                    "qty_available": _f(p.qty_available, _f(p.qty)),
                    "avg_entry_price": _f(p.avg_entry_price),
                    "current_price": _f(p.current_price),
                    "market_value": _f(p.market_value),
                    "unrealized_plpc": _f(p.unrealized_plpc),
                    "asset_class": _enum_value(p.asset_class),
                }
                for p in positions
            ],
            "open_orders": [
                {"symbol": o.symbol, "side": _enum_value(o.side), "status": _enum_value(o.status)}
                for o in open_orders
            ],
            "recent_orders": [
                {
                    "symbol": o.symbol,
                    "side": _enum_value(o.side),
                    "status": _enum_value(o.status),
                    "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
                    "filled_qty": _f(o.filled_qty),
                    "filled_avg_price": _f(o.filled_avg_price) or None,
                }
                for o in recent
            ],
        }

    def prices(self, symbols: list[str]) -> dict[str, dict]:
        """Daily closes (oldest first, today's partial bar excluded) and the latest trade.

        Free Alpaca data: SIP (all exchanges) history is allowed when the request
        ends at least 15 minutes ago; the latest trade comes from the IEX feed.
        """
        from alpaca.data.enums import Adjustment, DataFeed
        from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
        from alpaca.data.timeframe import TimeFrame

        now = datetime.now(timezone.utc)
        today_ny = now.astimezone(NEW_YORK).date()
        bars = self.data.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=now - timedelta(days=200),
                end=now - timedelta(minutes=20),
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
            )
        )
        latest = self.data.get_stock_latest_trade(
            StockLatestTradeRequest(symbol_or_symbols=symbols, feed=DataFeed.IEX)
        )
        out: dict[str, dict] = {}
        for sym in symbols:
            sym_bars = bars.data.get(sym, []) if hasattr(bars, "data") else []
            trade = latest.get(sym) if isinstance(latest, dict) else None
            # The latest trade stands in for "today". Drop any daily bar from that
            # trading day (or later) so the same day is not counted twice.
            cutoff = trade.timestamp.astimezone(NEW_YORK).date() if trade is not None else today_ny
            closes = [
                float(b.close)
                for b in sym_bars
                if b.timestamp.astimezone(NEW_YORK).date() < cutoff
            ]
            out[sym] = {
                "closes": closes,
                "last_price": float(trade.price) if trade is not None else None,
                "last_trade_time": trade.timestamp.isoformat() if trade is not None else None,
            }
        return out

    def asset(self, symbol: str) -> dict:
        a = self.trading.get_asset(symbol)
        return {
            "tradable": bool(a.tradable),
            "fractionable": bool(a.fractionable),
            "status": _enum_value(a.status),
        }

    def is_market_open(self) -> bool:
        return bool(self.trading.get_clock().is_open)

    # ----------------------------------------------------------------- writes
    def submit(self, order: PlannedOrder) -> dict:
        """Send one market DAY order to the PAPER account."""
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        assert_paper(self.trading)  # checked again right before every order
        if (order.notional is None) == (order.qty is None):
            raise ValueError("exactly one of notional or qty must be set")
        req = MarketOrderRequest(
            symbol=order.symbol,
            side=OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            notional=order.notional,
            qty=order.qty,
            client_order_id=order.client_order_id or None,
        )
        o = self.trading.submit_order(order_data=req)
        return {"id": str(o.id), "status": _enum_value(o.status), "symbol": o.symbol}


class MockBroker:
    """Fake account and prices for --mock runs and tests. Never touches the network."""

    def __init__(self, equity: float = 100_000.0, last_equity: float | None = None,
                 market_open: bool = True, positions: list[dict] | None = None):
        self.equity = equity
        self.last_equity = equity if last_equity is None else last_equity
        self.market_open = market_open
        self.positions = positions if positions is not None else [
            {"symbol": "MSFT", "side": "long", "qty": 10.0, "qty_available": 10.0,
             "avg_entry_price": 400.0, "current_price": 420.0, "market_value": 4200.0,
             "unrealized_plpc": 0.05, "asset_class": "us_equity"},
        ]
        self.submitted: list[PlannedOrder] = []

    def snapshot(self) -> dict:
        lmv = sum(p["market_value"] for p in self.positions)
        return {
            "account": {
                "status": "ACTIVE", "equity": self.equity, "last_equity": self.last_equity,
                "cash": self.equity - lmv, "buying_power": 2 * (self.equity - lmv),
                "long_market_value": lmv, "trading_blocked": False, "account_blocked": False,
                "trade_suspended_by_user": False, "pattern_day_trader": False, "daytrade_count": 0,
            },
            "clock": {"is_open": self.market_open, "timestamp": datetime.now(timezone.utc).isoformat(),
                      "next_open": "", "next_close": ""},
            "positions": self.positions,
            "open_orders": [],
            "recent_orders": [],
        }

    def prices(self, symbols: list[str]) -> dict[str, dict]:
        out = {}
        for i, sym in enumerate(symbols):
            base = 100.0 + 25 * i
            drift = 0.002 if i % 3 else -0.001  # most trend up, every third trends down
            closes = [round(base * (1 + drift) ** d, 2) for d in range(120)]
            out[sym] = {"closes": closes, "last_price": closes[-1] * (1 + drift),
                        "last_trade_time": None}
        return out

    def asset(self, symbol: str) -> dict:
        return {"tradable": True, "fractionable": True, "status": "active"}

    def is_market_open(self) -> bool:
        return self.market_open

    def submit(self, order: PlannedOrder) -> dict:
        self.submitted.append(order)
        return {"id": f"mock-{len(self.submitted)}", "status": "accepted", "symbol": order.symbol}
