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
                "MAX_ORDERS_PER_RUN", "DAILY_LOSS_LIMIT_PCT", "MAX_DRAWDOWN_PCT",
                "MIN_ORDER_DOLLARS", "CLAUDE_MODEL", "CLAUDE_EFFORT", "CLAUDE_BIN",
                "CLAUDE_TIMEOUT_S"):
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
# Claude is reached through the Claude Code CLI. These tests replace the
# subprocess call with a fake, so nothing is actually run.
import json as _json  # noqa: E402
import subprocess as _subprocess  # noqa: E402


class FakeRun:
    def __init__(self, stdout="", returncode=0, stderr="", exc=None):
        self.stdout, self.returncode, self.stderr, self.exc = stdout, returncode, stderr, exc
        self.args = self.kwargs = None

    def __call__(self, args, **kwargs):
        self.args, self.kwargs = args, kwargs
        if self.exc:
            raise self.exc
        return SimpleNamespace(stdout=self.stdout, stderr=self.stderr, returncode=self.returncode)


def cc_result(structured=None, subtype="success", is_error=False, result=""):
    out = {"type": "result", "subtype": subtype, "is_error": is_error, "result": result,
           "num_turns": 2, "duration_ms": 1000, "stop_reason": "end_turn",
           "usage": {"input_tokens": 1, "output_tokens": 1},
           "modelUsage": {"claude-opus-5-5": {}}}
    if structured is not None:
        out["structured_output"] = structured
    return _json.dumps(out)


def make_decider(settings, fake, claude_bin="/usr/local/bin/claude"):
    d = ClaudeDecider.__new__(ClaudeDecider)
    d.settings, d.strategy_text, d.claude_bin, d._run = settings, "strategy", claude_bin, fake
    return d


GOOD = Decision(market_view="v", notes="", trades=[trade("AAPL", "buy", 100)])


def decide_with(settings, fake, **kw):
    return make_decider(settings, fake, **kw).decide(MockBroker().snapshot(), {})


def test_claude_code_good_answer(settings):
    r = decide_with(settings, FakeRun(cc_result(GOOD.model_dump())))
    assert r.decision == GOOD and "error" not in r.meta
    assert r.meta["served_by"] == ["claude-opus-5-5"]


def test_claude_code_command_is_locked_down(settings, monkeypatch):
    from papertrader.decide import CHILD_ENV_ALLOW

    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                 "CLAUDE_CODE_USE_BEDROCK", "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "GITHUB_TOKEN"):
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sub-token")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    seen = {}

    class Run(FakeRun):
        def __call__(self, args, **kwargs):
            seen["cwd_files"] = list(Path(kwargs["cwd"]).iterdir())
            seen["cwd"] = kwargs["cwd"]
            return super().__call__(args, **kwargs)

    fake = Run(cc_result(GOOD.model_dump()))
    decide_with(settings, fake)
    a = fake.args
    assert a[0] == "/usr/local/bin/claude" and "-p" in a
    assert a[a.index("--tools") + 1] == ""                      # no tools at all
    assert a[a.index("--setting-sources") + 1] == ""            # no settings files
    assert a[a.index("--output-format") + 1] == "json"
    assert _json.loads(a[a.index("--json-schema") + 1])["title"] == "Decision"
    assert a[a.index("--model") + 1] == "claude-opus-5-5"
    assert a[a.index("--effort") + 1] == "high"
    assert a[a.index("--max-turns") + 1] == "5"
    assert a[a.index("--system-prompt") + 1].startswith("strategy")
    for flag in ("--safe-mode", "--strict-mcp-config", "--no-session-persistence"):
        assert flag in a
    # Runs in a fresh, empty temporary folder that is gone afterwards.
    assert seen["cwd_files"] == [] and not Path(seen["cwd"]).exists()
    # The account data goes in on stdin; only allowlisted variables reach the child.
    assert "watchlist_features" in fake.kwargs["input"]
    env = fake.kwargs["env"]
    assert set(env) <= set(CHILD_ENV_ALLOW)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sub-token"
    assert "/usr/local/bin" in env["PATH"].split(":")           # node next to claude is findable
    assert fake.kwargs["timeout"] == settings.claude_timeout_s


@pytest.mark.parametrize("fake", [
    FakeRun("", returncode=1, stderr="Invalid API key \u00b7 Please run /login"),  # not logged in
    FakeRun("not json"),
    FakeRun(_json.dumps(["a list"])),
    FakeRun("warning: update available\n" + cc_result(GOOD.model_dump())),  # text before JSON
    FakeRun(cc_result(GOOD.model_dump()).replace('"type": "result"', '"type": "assistant"')),
    FakeRun(cc_result(GOOD.model_dump(), subtype="error_max_structured_output_retries",
                      is_error=True)),
    FakeRun(cc_result(GOOD.model_dump(), is_error=True, result="usage limit reached")),
    FakeRun(cc_result(GOOD.model_dump()), returncode=1),
    FakeRun(cc_result(None)),                                   # no structured answer
    FakeRun(cc_result({"market_view": "x"})),                   # missing fields
    FakeRun(cc_result({**GOOD.model_dump(), "extra": 1})),      # unexpected field
    FakeRun(cc_result({**GOOD.model_dump(), "trades": [{"symbol": "AAPL", "action": "short",
                                                         "dollars": 5, "reason": "r"}]})),
    FakeRun(exc=_subprocess.TimeoutExpired("claude", 600)),
    FakeRun(exc=FileNotFoundError("claude")),
])
def test_claude_code_problems_mean_no_trades(settings, fake):
    r = decide_with(settings, fake)
    assert r.decision.trades == [] and r.meta.get("error")


def test_claude_code_missing_means_no_trades(settings):
    fake = FakeRun(cc_result(GOOD.model_dump()))
    r = decide_with(settings, fake, claude_bin=None)
    assert r.decision.trades == [] and "not found" in r.meta["error"]
    assert fake.args is None  # never tried to run anything


def test_find_claude_respects_claude_bin(tmp_path):
    from papertrader.decide import find_claude

    exe = tmp_path / "claude"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    assert find_claude(str(exe)) == str(exe)
    assert find_claude(str(tmp_path / "nope")) is None


# ------------------------------------------------------- round 1 review fixes
@pytest.mark.parametrize("value", ["nan", "inf"])
def test_non_finite_settings_rejected(monkeypatch, value):
    monkeypatch.setenv("MAX_ORDER_DOLLARS", value)
    with pytest.raises(ValueError):
        load_settings()


def test_tiny_partial_sell_rejected(settings):
    res, _ = limits(Decision(market_view="", notes="", trades=[trade("MSFT", "sell", 0.30)]),
                    MockBroker(), settings)
    assert not res.approved and "minimum" in res.rejected[0]["why"]


def test_closed_market_with_trade_skips_claude(settings):
    class Boom:
        def decide(self, *a):
            raise AssertionError("Claude should not be called")
    b = MockBroker(market_open=False)
    rec = run_once(b, Boom(), settings, State(settings.state_dir), trade=True, mode_label="mock")
    assert rec["claude"]["skipped"] == "market closed" and b.submitted == []


def test_failed_run_is_logged(settings):
    from papertrader.journal import read_runs
    from papertrader.runner import log_failed_run
    log_failed_run(settings, "dry-run", "APIError: boom")
    runs = read_runs(settings.log_dir)
    assert runs and "boom" in runs[-1]["errors"][0]


# --------------------------------------------- AlpacaBroker with fake SDK objects
def test_alpaca_broker_snapshot_and_submit_offline(monkeypatch):
    """Runs AlpacaBroker.snapshot() and submit() against the real SDK request classes
    with a fake trading client, so no network call or order happens."""
    from datetime import datetime, timezone

    from alpaca.trading.requests import MarketOrderRequest

    from papertrader.broker import AlpacaBroker, PlannedOrder

    now = datetime.now(timezone.utc)
    acct = SimpleNamespace(status="ACTIVE", equity="100000", last_equity="99000", cash="50000",
                           buying_power="200000", long_market_value="50000", trading_blocked=False,
                           account_blocked=False, trade_suspended_by_user=False,
                           pattern_day_trader=False, daytrade_count=0)
    pos = SimpleNamespace(symbol="MSFT", side="long", qty="10", qty_available="10",
                          avg_entry_price="400", current_price="420", market_value="4200",
                          unrealized_plpc="0.05", asset_class="us_equity")
    sent = []

    class FakeTrading:
        _base_url = safety.PAPER_BASE_URL
        _sandbox = True

        def get_account(self): return acct
        def get_clock(self): return SimpleNamespace(is_open=True, timestamp=now, next_open=now,
                                                    next_close=now)
        def get_all_positions(self): return [pos]
        def get_orders(self, filter=None): return []
        def submit_order(self, order_data):
            sent.append(order_data)
            return SimpleNamespace(id="abc", status="accepted", symbol=order_data.symbol)

    b = AlpacaBroker.__new__(AlpacaBroker)
    b.trading = FakeTrading()
    snap = b.snapshot()
    assert snap["account"]["equity"] == 100000.0 and snap["positions"][0]["qty_available"] == 10.0

    out = b.submit(PlannedOrder(symbol="AAPL", side="buy", est_dollars=123.45, reason="t",
                                notional=123.45, client_order_id="pt-1-1"))
    assert out["status"] == "accepted"
    req = sent[0]
    assert isinstance(req, MarketOrderRequest) and req.notional == 123.45 and req.qty is None
    assert str(req.time_in_force.value) == "day"

    b.trading._base_url = "https://api.alpaca.markets"  # simulate a live client
    with pytest.raises(safety.LiveTradingRefused):
        b.submit(PlannedOrder(symbol="AAPL", side="buy", est_dollars=1, reason="t", notional=1.0))
    assert len(sent) == 1


# ------------------------------------------------------- round 2 review fixes
def test_paper_refusal_at_order_time_stops_the_run(settings):
    class LiveLooking(MockBroker):
        def submit(self, order):
            raise safety.LiveTradingRefused("not paper")
    with pytest.raises(safety.LiveTradingRefused):
        run_once(LiveLooking(), ScriptedDecider(), settings, State(settings.state_dir),
                 trade=True, mode_label="mock")


def test_bad_setting_names_the_variable(monkeypatch):
    monkeypatch.setenv("MAX_POSITION_PCT", "10%")
    with pytest.raises(ValueError, match="MAX_POSITION_PCT"):
        load_settings()


def test_decider_init_finds_claude_bin(settings, tmp_path):
    exe = tmp_path / "claude"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    d = ClaudeDecider(dataclasses.replace(settings, claude_bin=str(exe)), run=FakeRun())
    assert d.claude_bin == str(exe)
    d = ClaudeDecider(dataclasses.replace(settings, claude_bin=str(tmp_path / "missing")))
    assert d.claude_bin is None


def test_find_claude_fallback_paths(tmp_path, monkeypatch):
    from papertrader import decide

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(decide.shutil, "which", lambda name: None)
    monkeypatch.setattr(decide, "CLAUDE_BIN_CANDIDATES", ("~/.local/bin/claude",))
    assert decide.find_claude() is None
    nvm = tmp_path / ".nvm/versions/node/v22.1.0/bin/claude"
    nvm.parent.mkdir(parents=True)
    nvm.write_text("#!/usr/bin/env node\n")
    nvm.chmod(0o755)
    assert decide.find_claude() == str(nvm)
    native = tmp_path / ".local/bin/claude"
    native.parent.mkdir(parents=True)
    native.write_text("bin")
    native.chmod(0o755)
    assert decide.find_claude() == str(native)               # native install wins


def test_check_call_trades_nothing(settings):
    fake = FakeRun(cc_result({"market_view": "ok", "trades": [], "notes": ""}))
    r = make_decider(settings, fake).check()
    assert "error" not in r.meta and r.decision.trades == []
    assert "watchlist_features" not in fake.kwargs["input"]  # no account data sent


def test_timeout_must_stay_under_lock_staleness(monkeypatch):
    monkeypatch.setenv("CLAUDE_TIMEOUT_S", "4000")
    with pytest.raises(ValueError, match="CLAUDE_TIMEOUT_S"):
        load_settings()


def test_run_exits_nonzero_when_claude_step_fails(tmp_path, monkeypatch):
    import run as run_module
    from papertrader import runner

    rec = {"approved": [], "claude": {"error": "not logged in"}}
    monkeypatch.setattr(runner, "run_once", lambda *a, **k: rec)
    monkeypatch.setenv("ALPACA_API_KEY", "PKTEST")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "x")
    monkeypatch.setattr(run_module, "find_claude", lambda *a: "/usr/local/bin/claude")
    monkeypatch.setattr("papertrader.broker.AlpacaBroker", lambda *a: object())
    monkeypatch.setattr("papertrader.decide.ClaudeDecider", lambda *a, **k: object())
    monkeypatch.setattr(run_module, "load_dotenv_file", lambda: None)
    import papertrader.config as cfg
    real = cfg.load_settings
    monkeypatch.setattr(run_module, "load_settings",
                        lambda: dataclasses.replace(real(), log_dir=tmp_path, state_dir=tmp_path))
    (tmp_path / "latest.md").write_text("log")
    assert run_module.main([]) == 1
    rec["claude"] = {}                       # same run with a clean Claude step exits 0,
    assert run_module.main([]) == 0          # so the 1 above came from the Claude error


def test_nvm_fallback_picks_newest_version(tmp_path, monkeypatch):
    from papertrader import decide

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(decide.shutil, "which", lambda *a, **k: None)
    monkeypatch.setattr(decide, "CLAUDE_BIN_CANDIDATES", ())
    for v in ("v9.11.2", "v22.3.0", "v20.10.0"):
        exe = tmp_path / f".nvm/versions/node/{v}/bin/claude"
        exe.parent.mkdir(parents=True)
        exe.write_text("#!/usr/bin/env node\n")
        exe.chmod(0o755)
    assert "/v22.3.0/" in decide.find_claude()


def test_early_exit_is_logged(tmp_path, monkeypatch):
    import run as run_module
    from papertrader.journal import read_runs

    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setattr(run_module, "load_dotenv_file", lambda: None)
    import papertrader.config as cfg
    real = cfg.load_settings
    monkeypatch.setattr(run_module, "load_settings",
                        lambda: dataclasses.replace(real(), log_dir=tmp_path, state_dir=tmp_path))
    assert run_module.main(["--trade"]) == 2
    runs = read_runs(tmp_path)
    assert len(runs) == 1 and "ALPACA_API_KEY" in runs[0]["errors"][0]
