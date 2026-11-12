"""Paper-only guard rails.

This bot has no code path for live trading. The checks here make that hold even
if the environment is misconfigured:

1. The trading client is always built with ``paper=True`` and never with a URL
   override, then its base URL is compared to the paper URL. Anything else stops
   the program.
2. Environment variables that other Alpaca tools use to point at a server are
   checked. If one names anything other than the paper URL, the bot refuses to
   start, because that usually means the machine is set up for live trading.
3. Alpaca live API key ids start with "AK" and paper key ids with "PK". A key
   that starts with "AK" is refused outright.
4. ``assert_paper`` runs again right before every order is sent.
"""

from __future__ import annotations

import os
from typing import Mapping

PAPER_BASE_URL = "https://paper-api.alpaca.markets"

# Variables that Alpaca's SDKs, CLIs and community tools read for the server URL.
URL_ENV_VARS = (
    "APCA_API_BASE_URL",
    "ALPACA_BASE_URL",
    "ALPACA_API_BASE_URL",
    "ALPACA_ENDPOINT",
    "ALPACA_URL",
    "ALPACA_TRADING_URL",
)


class LiveTradingRefused(RuntimeError):
    """Raised whenever anything points this bot away from the paper endpoint."""


def _norm(url: str) -> str:
    return url.strip().rstrip("/").lower()


def check_environment(env: Mapping[str, str] | None = None) -> None:
    """Refuse to run if the environment looks configured for live trading."""
    env = os.environ if env is None else env

    for var in URL_ENV_VARS:
        value = env.get(var)
        if value and _norm(value) not in (_norm(PAPER_BASE_URL), _norm(PAPER_BASE_URL + "/v2")):
            raise LiveTradingRefused(
                f"{var} is set to {value!r}. This bot only talks to {PAPER_BASE_URL}. "
                f"Unset {var} or set it to the paper URL."
            )

    paper_flag = env.get("ALPACA_PAPER")
    if paper_flag is not None and paper_flag.strip().lower() not in ("1", "true", "yes", "on"):
        raise LiveTradingRefused(
            "ALPACA_PAPER is set to something other than true. This bot is paper-only; "
            "remove ALPACA_PAPER or set it to true."
        )

    key = (env.get("ALPACA_API_KEY") or "").strip()
    if key.upper().startswith("AK"):
        raise LiveTradingRefused(
            "ALPACA_API_KEY looks like a LIVE key (live key ids start with 'AK'). "
            "Use the keys from your Alpaca PAPER dashboard (they start with 'PK')."
        )


def assert_paper(trading_client) -> None:
    """Stop unless the client points at the paper endpoint. Run before every order."""
    base = getattr(trading_client, "_base_url", None)
    base = getattr(base, "value", base)  # BaseURL enum or plain string
    if not isinstance(base, str) or _norm(base) != _norm(PAPER_BASE_URL):
        raise LiveTradingRefused(f"Trading client points at {base!r}, not {PAPER_BASE_URL}.")
    if getattr(trading_client, "_sandbox", True) is not True:
        raise LiveTradingRefused("Trading client is not in paper (sandbox) mode.")


def make_paper_trading_client(api_key: str, secret_key: str):
    """Build an Alpaca TradingClient that can only reach the paper endpoint."""
    check_environment()
    from alpaca.trading.client import TradingClient

    # paper=True and no url_override: the SDK then uses its paper URL constant.
    client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
    assert_paper(client)
    return client
