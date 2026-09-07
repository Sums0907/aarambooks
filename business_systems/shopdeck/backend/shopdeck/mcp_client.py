#!/usr/bin/env python3
"""
ShopDeck MCP Client
Interacts directly with the ShopDeck MCP Server via JSON-RPC over HTTP.
Provides methods to list live tables, inspect live schemas, and query live data.
"""

import json
import os
import sys
import urllib.error
import urllib.request
import ssl
import time
from typing import Any, Dict, List, Optional

try:
    from shopdeck import config
except ImportError:
    from shopdeck import config

try:
    from .mcp_auth import load_token, _get_ssl_context
except ImportError:
    from mcp_auth import load_token, _get_ssl_context

BASE_URL = config.MCP_BASE_URL
MCP_ENDPOINT = BASE_URL if BASE_URL.endswith("/mcp") else f"{BASE_URL}/mcp"


class ShopDeckMCPClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or load_token()
        if not self.token:
            raise ValueError(
                "No access token provided or found in cache. "
                "Run `python3 business_systems/shopdeck/mcp_auth.py` first to authenticate."
            )
        self._request_id = 0

    def _call_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload).encode("utf-8")
        ctx = _get_ssl_context()
        
        retries = 0
        while True:
            req = urllib.request.Request(MCP_ENDPOINT, data=body, method="POST")
            req.add_header("Authorization", f"Bearer {self.token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json, text/event-stream")
            
            try:
                with urllib.request.urlopen(req, timeout=config.MCP_REQUEST_TIMEOUT, context=ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                if isinstance(e, urllib.error.HTTPError) and e.code == 401:
                    raise PermissionError(
                        "ShopDeck MCP 401 Unauthorized: The access token has expired or is invalid. "
                        "Please re-run `python3 business_systems/shopdeck/mcp_auth.py`."
                    ) from e
                
                retries += 1
                if retries > config.MCP_RETRY_COUNT:
                    if isinstance(e, urllib.error.HTTPError):
                        err_msg = e.read().decode("utf-8")[:400]
                        raise RuntimeError(f"ShopDeck MCP HTTP {e.code}: {err_msg}") from e
                    raise RuntimeError(f"ShopDeck MCP Network Error: {e}") from e
                
                print(f"⚠️ MCP Request Failed ({e}). Retrying in {config.MCP_RETRY_BACKOFF}s ({retries}/{config.MCP_RETRY_COUNT})...")
                time.sleep(config.MCP_RETRY_BACKOFF)

        if "error" in data:
            raise RuntimeError(f"ShopDeck MCP RPC Error: {data['error']}")
        return data.get("result")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server."""
        result = self._call_rpc("tools/call", {"name": tool_name, "arguments": arguments})
        content = result.get("content", [])
        if content and "text" in content[0]:
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return content[0]["text"]
        return result

    def list_tables(self) -> List[Dict[str, Any]]:
        """Fetch all tables and column definitions from the live MCP server."""
        return self.call_tool("list_tables", {})

    def query_data(
        self,
        query: str,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Any:
        """Execute a SQL query against the ShopDeck MCP Server."""
        table_config: Dict[str, Any] = {"table_name": table_name}
        if start_date and end_date:
            table_config["dateRange"] = {
                "startDate": start_date,
                "endDate": end_date,
            }

        return self.call_tool(
            "query_data",
            {
                "query": query,
                "tables_included": [table_config],
            },
        )

    def sync_live_schema(self, output_path: str) -> List[Dict[str, Any]]:
        """Fetch live schema and save to disk."""
        tables = self.list_tables()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tables, f, indent=2)
        return tables


def main():
    token = load_token()
    if not token:
        print("❌ No token found. Please run mcp_auth.py first to authenticate with ShopDeck.")
        sys.exit(1)

    client = ShopDeckMCPClient(token=token)
    print("🔌 Connecting to ShopDeck MCP Server...")
    try:
        tables = client.list_tables()
        print(f"✅ Successfully connected! Found {len(tables)} tables on the live server.")
        for t in tables[:10]:
            print(f" - {t.get('table_name')}: {len(t.get('columns', []))} columns")
        if len(tables) > 10:
            print(f" ... and {len(tables) - 10} more tables.")
    except Exception as e:
        print(f"❌ Error communicating with MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
