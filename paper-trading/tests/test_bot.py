"""Offline tests: no keys, no network, no orders.

    cd paper-trading && python -m pytest -q
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from papertrader import safety  # noqa: E402
from papertrader.broker import MockBroker  # noqa: E402
from papertrader.config import Settings, load_settings, validate  # noqa: E402
from papertrader.decide import ClaudeDecider, Decision, ProposedTrade, ScriptedDecider  # noqa: E402
from papertrader.features import compute_features  # noqa: E402
from papertrader.risk import apply_limits  # noqa: E402
from papertrader.runner import run_once  # noqa: E402
from papertrader.state import State  # noqa: E402


@pytest.fixture
def settings(tmp_path, monkeypatch):
    for var in ("WATCHLIST", "MAX_POSITION_PCT", "MAX_INVESTED_PCT", "MAX_ORDER_DOLLARS",
                "MAX_ORDERS_PER_RUN", "DAILY_LOSS_LIMIT_PCT", "MAX_DRAWDOWN_PCT"):
        monkeypatch.delenv(var, raising=False)
    s = load_settings()
    return dataclasses.replace(s, log_dir=tmp_path / "logs", state_dir=tmp_path / "state")


def features_for(broker, settings):
    prices = broker.prices(list(settings.watchlist))
    return {s: compute_features(p["closes"], p["last_price"]) for s, p in prices.items()}


ASSETS = {s: {"tradable": True, "fractionable": True} for s in
          "AAPL MSFT NVDA GOOGL AMZN META AVGO AMD CRM ORCL ADBE NOW SPY QQQ".split()}


def limits(decision, broker, settings, **kw):
    snap = broker.snapshot()
    feats = features_for(broker, settings)
    return apply_limits(decision, snap, feats, kw.pop("assets", ASSETS), settings,
                        start_equity=kw.pop("start_equity", snap["account"]["equity"]),
                        halted=kw.pop("halted", False), run_id="pt-test")


def trade(sym, action, dollars, reason="test"):
    return ProposedTrade(symbol=sym, action=action, dollars=dollars, reason=reason)


# ----------------------------------------------------------------- safety
@pytest.mark.parametrize("var", safety.URL_ENV_VARS)
def test_live_url_env_is_refused(var):
    with pytest.raises(safety.LiveTradingRefused):
        safety.check_environment({var: "https://api.alpaca.markets"})


def test_paper_url_env_is_allowed():
    safety.check_environment({"APCA_API_BASE_URL": "https://paper-api.alpaca.markets/"})


def test_live_key_prefix_is_refused():
    with pytest.raises(safety.LiveTradingRefused):
        safety.check_environment({"ALPACA_API_KEY": "AKXXXXXXXX"})


def test_paper_false_is_refused():
    with pytest.raises(safety.LiveTradingRefused):
        safety.check_environment({"ALPACA_PAPER": "false"})


def test_real_sdk_client_is_paper(monkeypatch):
    for var in safety.URL_ENV_VARS + ("ALPACA_PAPER", "ALPACA_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    client = safety.make_paper_trading_client("PKTEST", "secret")  # no network call
    safety.assert_paper(client)


def test_assert_paper_rejects_live_client():
    from alpaca.trading.client import TradingClient

    live = TradingClient("PKTEST", "secret", paper=False)  # constructed only, never used
    with pytest.raises(safety.LiveTradingRefused):
        safety.assert_paper(live)


def test_no_live_endpoint_in_source():
    """No file in the bot may name the live endpoint or ask the SDK for it."""
    pkg = HERE / "papertrader"
    files = list(pkg.glob("*.py")) + [HERE / "run.py", HERE / "report.py"]
    for f in files:
        text = f.read_text()
        assert "paper=False" not in text, f
        assert "TRADING_LIVE" not in text, f
        assert "url_override=" not in text, f
        assert not re.search(r"https://api\.alpaca\.markets", text), f


# --------------------------------------------------------------- settings
def test_settings_validation_rejects_nonsense(settings):
    with pytest.raises(ValueError):
        validate(dataclasses.replace(settings, max_position_pct=1.5))
    with pytest.raises(ValueError):
        validate(dataclasses.replace(settings, max_position_pct=0.9, max_invested_pct=0.5))


# --------------------------------------------------------------- features
def test_features_uptrend():
    closes = [100 * 1.01 ** i for i in range(100)]
    f = compute_features(closes, closes[-1] * 1.01)
    assert f["above_sma50"] and f["sma20_above_sma50"] and f["return_63d"] > 0
    assert f["enough_history"]


def test_features_missing_data():
    f = compute_features([], None)
    assert f["price"] is None and f["enough_history"] is False


# ------------------------------------------------------------------- risk
def test_rejects_symbol_outside_watchlist(settings):
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("GME", "buy", 1000)]),
                    MockBroker(), settings)
    assert not res.approved and "watchlist" in res.rejected[0]["why"]


def test_buy_shrunk_to_position_cap(settings):
    b = MockBroker(positions=[])  # $100k equity, all cash
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 50_000)]),
                    b, settings)
    o = res.approved[0]
    assert o.notional <= settings.max_order_dollars  # $5k single-order cap binds first
    assert "shrunk" in o.reason


def test_existing_position_counts_toward_cap(settings):
    b = MockBroker(positions=[{"symbol": "AAPL", "side": "long", "qty": 50, "qty_available": 50,
                               "avg_entry_price": 190, "current_price": 196, "market_value": 9_800,
                               "unrealized_plpc": 0.03, "asset_class": "us_equity"}])
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 5000)]),
                    b, settings)
    assert res.approved[0].notional == pytest.approx(200.0, abs=0.01)  # 10% of 100k minus 9.8k


def test_cash_floor_and_invested_cap(settings):
    b = MockBroker(positions=[{"symbol": "SPY", "side": "long", "qty": 100, "qty_available": 100,
                               "avg_entry_price": 500, "current_price": 790, "market_value": 79_000,
                               "unrealized_plpc": 0.5, "asset_class": "us_equity"}])
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 5000)]),
                    b, settings)
    assert res.approved[0].notional == pytest.approx(1000.0, abs=0.01)  # 80% cap leaves $1k


def test_no_shorting(settings):
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("NVDA", "sell", 1000)]),
                    MockBroker(), settings)
    assert not res.approved and "not held" in res.rejected[0]["why"]


def test_full_exit_sells_exact_held_qty(settings):
    b = MockBroker()  # holds 10 MSFT
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("MSFT", "sell", 999_999)]),
                    b, settings)
    assert res.approved[0].qty == 10.0 and res.approved[0].notional is None


def test_daily_loss_blocks_buys_not_sells(settings):
    b = MockBroker(equity=95_000, last_equity=100_000)
    d = Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 1000),
                                                   trade("MSFT", "sell", 1000)])
    res, _ = limits(d, b, settings, start_equity=100_000)
    assert [o.side for o in res.approved] == ["sell"]
    assert "no buys" in res.rejected[0]["why"]


def test_drawdown_halts_everything(settings):
    b = MockBroker(equity=80_000, last_equity=80_500)
    d = Decision(market_view="", notes="", trades=[trade("MSFT", "sell", 1000)])
    res, newly_halted = limits(d, b, settings, start_equity=100_000)
    assert newly_halted and not res.approved and res.blocked_reason


def test_max_orders_per_run(settings):
    s = dataclasses.replace(settings, max_orders_per_run=2)
    d = Decision(market_view="", notes="", trades=[trade(x, "buy", 100) for x in ("AAPL", "NVDA", "AMD")])
    res, _ = limits(d, MockBroker(positions=[]), s)
    assert len(res.approved) == 2 and len(res.rejected) == 1


def test_bad_numbers_rejected(settings):
    d = Decision(market_view="", notes="", trades=[trade("AAPL", "buy", -5),
                                                   trade("NVDA", "buy", float("nan"))])
    res, _ = limits(d, MockBroker(positions=[]), settings)
    assert not res.approved and len(res.rejected) == 2


def test_non_fractionable_uses_whole_shares(settings):
    assets = {**ASSETS, "AAPL": {"tradable": True, "fractionable": False}}
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 1000)]),
                    MockBroker(positions=[]), settings, assets=assets)
    o = res.approved[0]
    assert o.notional is None and o.qty == int(o.qty) and o.qty >= 1


def test_untradable_asset_rejected(settings):
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("AAPL", "buy", 1000)]),
                    MockBroker(positions=[]), settings, assets={})
    assert not res.approved


# ------------------------------------------------------------ end to end
def test_mock_dry_run_sends_nothing(settings):
    b = MockBroker()
    rec = run_once(b, ScriptedDecider(), settings, State(settings.state_dir),
                   trade=False, mode_label="mock")
    assert rec["approved"] and rec["results"] is None and b.submitted == []
    assert (settings.log_dir / "runs.jsonl").exists()
    assert (settings.log_dir / "latest.md").read_text().startswith("# Run")


def test_mock_trade_submits_approved_only(settings):
    b = MockBroker()
    rec = run_once(b, ScriptedDecider(), settings, State(settings.state_dir),
                   trade=True, mode_label="mock")
    assert len(b.submitted) == len(rec["approved"]) > 0


def test_closed_market_sends_nothing(settings):
    b = MockBroker(market_open=False)
    rec = run_once(b, ScriptedDecider(), settings, State(settings.state_dir),
                   trade=True, mode_label="mock")
    assert b.submitted == [] and any("market is closed" in e for e in rec["errors"])


def test_halt_persists_across_runs(settings):
    st = State(settings.state_dir)
    st.ensure_start_equity(100_000)
    st.save()
    run_once(MockBroker(equity=80_000, last_equity=80_000), ScriptedDecider(), settings,
             State(settings.state_dir), trade=True, mode_label="mock")
    b = MockBroker()  # equity recovered, but the halt stays until reset
    rec = run_once(b, ScriptedDecider(), settings, State(settings.state_dir),
                   trade=True, mode_label="mock")
    assert rec["halted"] and b.submitted == []


# --------------------------------------------------- Claude call handling
class FakeMessages:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.kwargs = response, exc, None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.response


def make_decider(settings, fake):
    d = ClaudeDecider.__new__(ClaudeDecider)
    d.settings, d.strategy_text = settings, "strategy"
    d.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    return d


def test_claude_refusal_means_no_trades(settings):
    resp = SimpleNamespace(model="m", stop_reason="refusal", usage=None,
                           stop_details=SimpleNamespace(category="other"), parsed_output=None)
    r = make_decider(settings, FakeMessages(resp)).decide(MockBroker().snapshot(), {})
    assert r.decision.trades == [] and "refusal" in r.meta["error"]


def test_claude_error_means_no_trades(settings):
    r = make_decider(settings, FakeMessages(exc=RuntimeError("boom"))).decide(
        MockBroker().snapshot(), {})
    assert r.decision.trades == [] and "error" in r.meta


def test_claude_request_shape(settings):
    parsed = Decision(market_view="v", notes="", trades=[trade("AAPL", "buy", 100)])
    resp = SimpleNamespace(model=settings.model, stop_reason="end_turn",
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1),
                           parsed_output=parsed)
    fake = FakeMessages(resp)
    r = make_decider(settings, fake).decide(MockBroker().snapshot(), {})
    assert r.decision == parsed
    assert fake.kwargs["model"] == "claude-opus-5-5"
    assert fake.kwargs["output_format"] is Decision
    assert "thinking" not in fake.kwargs  # Opus 5.5: thinking is always on; effort controls depth
