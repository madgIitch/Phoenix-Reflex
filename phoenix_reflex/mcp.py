from __future__ import annotations

import os
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PHOENIX_MCP_TOOL_FILTER = [
    "list-traces",
    "get-trace",
    "get-spans",
    "add-dataset-examples",
    "upsert-prompt",
]


def is_observability_question(question: str) -> bool:
    """Return whether a question asks about runtime observability or regressions."""
    normalized = question.lower()
    keywords = (
        "traza",
        "trazas",
        "trace",
        "traces",
        "span",
        "spans",
        "fallo",
        "fallos",
        "failure",
        "failures",
        "caso de mejora",
        "casos de mejora",
        "improvement",
        "regression",
        "regresion",
        "regresiones",
        "introspeccion",
        "introspection",
        "observabilidad",
        "observability",
    )
    return any(keyword in normalized for keyword in keywords)


def build_observability_agent_message(question: str, reflex_context: str | None) -> str:
    """Build the first-turn message for observability questions."""
    context_block = (
        f"[Local Reflex Context - use if Phoenix MCP is unavailable]\n{reflex_context}\n\n"
        if reflex_context
        else ""
    )
    mcp_tools = ", ".join(f"phoenix_{tool}" for tool in PHOENIX_MCP_TOOL_FILTER)
    return (
        "[Observability Request]\n"
        "This question asks about traces, spans, failures, regressions, or improvement cases. "
        "If Phoenix MCP tools are available, use them in this first turn before answering. "
        f"Relevant Phoenix MCP tools include: {mcp_tools}. "
        "If Phoenix MCP is unavailable or returns no useful trace data, answer from the local "
        "Reflex context below without failing.\n\n"
        f"{context_block}"
        f"[Question]\n{question}"
    )


def _mcp_enabled() -> bool:
    return os.getenv("ENABLE_PHOENIX_MCP", "").lower() in {"1", "true", "yes"}


def _phoenix_host() -> str:
    return (os.getenv("PHOENIX_HOST") or os.getenv("PHOENIX_BASE_URL") or "").strip()


def phoenix_mcp_status() -> dict[str, Any]:
    """Return demo-readiness status for Phoenix MCP without starting the server."""
    enabled = _mcp_enabled()
    phoenix_host = _phoenix_host()
    phoenix_api_key = os.getenv("PHOENIX_API_KEY", "").strip()
    missing: list[str] = []
    if not enabled:
        missing.append("ENABLE_PHOENIX_MCP")
    if not phoenix_host:
        missing.append("PHOENIX_HOST")
    if not phoenix_api_key:
        missing.append("PHOENIX_API_KEY")

    importable = True
    for module in ("google.adk.tools.mcp_tool", "mcp"):
        try:
            __import__(module)
        except Exception:
            importable = False
            missing.append(module)

    configured = bool(phoenix_host and phoenix_api_key)
    return {
        "enabled": enabled,
        "configured": configured,
        "importable": importable,
        "demo_ready": enabled and configured and importable,
        "phoenix_host": phoenix_host,
        "tool_filter": PHOENIX_MCP_TOOL_FILTER,
        "missing": missing,
    }


def optional_phoenix_mcp_tools() -> list[object]:
    """Return Phoenix MCP tools when explicitly enabled.

    The current deployed backend is Arize AX. Phoenix MCP is kept optional because
    it requires a Phoenix host/API key and starts an npx stdio subprocess.
    """
    if not _mcp_enabled():
        return []

    status = phoenix_mcp_status()
    if not status["demo_ready"]:
        logger.warning(
            "Phoenix MCP enabled but not ready: missing=%s",
            ", ".join(status["missing"]),
        )
        return []

    phoenix_host = str(status["phoenix_host"])
    phoenix_api_key = os.getenv("PHOENIX_API_KEY", "").strip()
    if not phoenix_host or not phoenix_api_key:
        return []

    try:
        from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
        from mcp import StdioServerParameters
    except Exception:
        logger.exception("Phoenix MCP dependencies could not be imported")
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
            tool_filter=PHOENIX_MCP_TOOL_FILTER,
            tool_name_prefix="phoenix",
        )
    ]
