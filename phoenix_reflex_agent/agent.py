from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from phoenix_reflex.mcp import optional_phoenix_mcp_tools
from phoenix_reflex.prompts import PRODUCTION_PROMPT
from phoenix_reflex.reflex import (
    get_trace_summary,
    list_improvement_cases,
    list_recent_trace_summaries,
)
from phoenix_reflex.retriever import retrieve_documents


load_dotenv()

if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


root_agent = Agent(
    name="qa_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    description="RAG QA agent for Phoenix Reflex.",
    instruction=PRODUCTION_PROMPT,
    tools=[
        retrieve_documents,
        list_recent_trace_summaries,
        get_trace_summary,
        list_improvement_cases,
        *optional_phoenix_mcp_tools(),
    ],
)
