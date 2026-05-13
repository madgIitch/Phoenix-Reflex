from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents import Agent


load_dotenv()

if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


root_agent = Agent(
    name="qa_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    description="Sprint 0 placeholder agent for Phoenix Reflex.",
    instruction=(
        "You are the Phoenix Reflex sprint 0 QA agent. "
        "For now, respond briefly and state that RAG retrieval will be added in sprint 1."
    ),
)
