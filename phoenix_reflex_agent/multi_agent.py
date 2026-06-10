from __future__ import annotations

import logging
import os

from google.adk.agents import Agent
from google.genai import types

from phoenix_reflex.mcp import optional_phoenix_mcp_tools
from phoenix_reflex.reflex import add_mcp_improvement_case, list_improvement_cases
from phoenix_reflex.retriever import retrieve_documents
from phoenix_reflex_agent.agent import build_single_agent


logger = logging.getLogger(__name__)

COORDINATOR_INSTRUCTION = """You are the QA coordinator. Your job:
1. Retrieve context using the available retrieval tool.
2. Answer the user's question directly in plain text, grounded only in the retrieved context.
3. Delegate evaluation (faithfulness, document_relevance, answer_quality, failure_mode) to the judge subagent.
4. If failure_mode != 'none', delegate improvement case creation to the improvement subagent.
Do not modify the user query. Do not wrap your answer in JSON or code blocks. Return plain text only."""

JUDGE_INSTRUCTION = """You are the judge subagent for Phoenix Reflex.
Produce only evaluation fields: faithfulness, document_relevance, answer_quality, and failure_mode.
Use the evidence supplied by the coordinator and do not create improvement cases."""

IMPROVEMENT_INSTRUCTION = """You are the improvement subagent for Phoenix Reflex.
Use existing Reflex rules to propose or create improvement cases when failure_mode is not 'none'.
Check existing improvement cases before creating a new one."""


def is_multi_agent_enabled() -> bool:
    """Return whether the experimental ADK multi-agent builder is enabled."""
    return os.getenv("ENABLE_MULTI_AGENT_ADK", "").strip().lower() in {"1", "true", "yes", "on"}


def build_multi_agent() -> Agent:
    """Build the experimental ADK 2.x coordinator with judge and improvement subagents."""
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    config = types.GenerateContentConfig(temperature=0.0)
    judge_subagent = Agent(
        name="judge_subagent",
        model=model,
        description="Evaluates answer faithfulness, relevance, quality, and failure mode.",
        instruction=JUDGE_INSTRUCTION,
        generate_content_config=config,
        tools=[],
    )
    improvement_subagent = Agent(
        name="improvement_subagent",
        model=model,
        description="Creates or proposes Reflex improvement cases after evaluation failures.",
        instruction=IMPROVEMENT_INSTRUCTION,
        generate_content_config=config,
        tools=[
            list_improvement_cases,
            add_mcp_improvement_case,
        ],
    )
    return Agent(
        name="qa_coordinator",
        model=model,
        description="Coordinates RAG QA, evaluation, and Reflex improvement workflows.",
        instruction=COORDINATOR_INSTRUCTION,
        generate_content_config=config,
        tools=[
            retrieve_documents,
            list_improvement_cases,
            *optional_phoenix_mcp_tools(),
        ],
        sub_agents=[
            judge_subagent,
            improvement_subagent,
        ],
    )


def build_root_agent() -> Agent:
    """Build the enabled agent, falling back to the stable single-agent path on failure."""
    if not is_multi_agent_enabled():
        return build_single_agent()
    try:
        return build_multi_agent()
    except Exception:
        logger.exception("Falling back to single-agent mode after multi-agent build failure.")
        return build_single_agent()
