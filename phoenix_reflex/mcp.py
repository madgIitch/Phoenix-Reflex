from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def optional_phoenix_mcp_tools() -> list[object]:
    """Return Phoenix MCP tools when explicitly enabled.

    The current deployed backend is Arize AX. Phoenix MCP is kept optional because
    it requires a Phoenix host/API key and starts an npx stdio subprocess.
    """
    if os.getenv("ENABLE_PHOENIX_MCP", "").lower() not in {"1", "true", "yes"}:
        return []

    phoenix_host = os.getenv("PHOENIX_HOST") or os.getenv("PHOENIX_BASE_URL")
    phoenix_api_key = os.getenv("PHOENIX_API_KEY")
    if not phoenix_host or not phoenix_api_key:
        return []

    try:
        from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
        from mcp import StdioServerParameters
    except Exception:
        return []

    return [
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@arizeai/phoenix-mcp@latest",
                        "--baseUrl",
                        phoenix_host,
                        "--apiKey",
                        phoenix_api_key,
                    ],
                ),
                timeout=20.0,
            ),
            tool_filter=[
                "list-traces",
                "get-trace",
                "get-spans",
                "add-dataset-examples",
                "upsert-prompt",
            ],
            tool_name_prefix="phoenix",
        )
    ]
