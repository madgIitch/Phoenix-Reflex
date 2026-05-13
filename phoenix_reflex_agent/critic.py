from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()


critic_agent = Agent(
    name="critic_agent",
    model=os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
    description="Evaluation agent for faithfulness and document relevance.",
    instruction=(
        "You are critic_agent for Phoenix Reflex. Judge whether answers are "
        "faithful to retrieved context and whether retrieved documents are "
        "relevant to the question. Be strict, concise, and return structured "
        "labels when asked."
    ),
)
