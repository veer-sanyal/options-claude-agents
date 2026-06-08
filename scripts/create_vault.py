#!/usr/bin/env python3
"""Setup (control plane): create a vault holding the brokerage MCP OAuth
credential, and print BROKERAGE_VAULT_ID.

The coordinator agent only *declares* the brokerage MCP server URL — it carries
no auth. Credentials live in a vault that run_session.py attaches to the session
via vault_ids; Anthropic injects the token after the request leaves the sandbox
and auto-refreshes it. The container never sees the secret.

Provide the OAuth credential via env vars (obtain these from your MCP server /
brokerage — see its docs; MCP OAuth tokens are NOT the same as a REST API key):

    export BROKERAGE_MCP_URL=https://...            # must match the agent YAML
    export BROKERAGE_MCP_ACCESS_TOKEN=...           # required
    # optional — enables auto-refresh (omit if you only have an access token):
    export BROKERAGE_MCP_REFRESH_TOKEN=...
    export BROKERAGE_MCP_CLIENT_ID=...
    export BROKERAGE_MCP_TOKEN_ENDPOINT=https://.../oauth/token

    eval "$(python scripts/create_vault.py)"        # capture BROKERAGE_VAULT_ID
    export BROKERAGE_VAULT_ID=$(python scripts/create_vault.py --quiet)

Skip this entirely if you're starting read-only without the brokerage MCP — leave
BROKERAGE_VAULT_ID unset and run_session.py omits vault_ids.
"""

from __future__ import annotations

import argparse
import os
import sys

import anthropic

VAULT_NAME = os.environ.get("VAULT_NAME", "options-brokerage")


def require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"set {name} (see this script's docstring).")
    return val


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true",
                        help="print only the bare vault id (for $(...) capture)")
    args = parser.parse_args()

    mcp_url = require("BROKERAGE_MCP_URL")
    access_token = require("BROKERAGE_MCP_ACCESS_TOKEN")

    # The refresh block is what enables auto-refresh; include it only if all the
    # OAuth pieces are present. Without it, the credential works until it expires.
    auth: dict = {
        "type": "mcp_oauth",
        "mcp_server_url": mcp_url,
        "access_token": access_token,
    }
    refresh_token = os.environ.get("BROKERAGE_MCP_REFRESH_TOKEN")
    if refresh_token:
        auth["refresh"] = {
            "refresh_token": refresh_token,
            "client_id": require("BROKERAGE_MCP_CLIENT_ID"),
            "token_endpoint": require("BROKERAGE_MCP_TOKEN_ENDPOINT"),
            "token_endpoint_auth": {"type": "none"},  # public client; see managed-agents Vaults docs
        }

    client = anthropic.Anthropic()
    vault = client.beta.vaults.create(name=VAULT_NAME)
    client.beta.vaults.credentials.create(
        vault.id,
        display_name=f"brokerage ({mcp_url})",
        auth=auth,
    )

    if args.quiet:
        print(vault.id)
    else:
        print(f"# created vault {vault.id} with brokerage MCP credential", file=sys.stderr)
        print(f"BROKERAGE_VAULT_ID={vault.id}")


if __name__ == "__main__":
    main()
