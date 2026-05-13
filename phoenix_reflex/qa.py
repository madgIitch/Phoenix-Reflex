from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from phoenix_reflex.evaluator import evaluate_faithfulness
from phoenix_reflex.observability import get_tracer
from phoenix_reflex_agent.agent import root_agent

APP_NAME = "phoenix-reflex"
USER_ID = "api-user"


@lru_cache(maxsize=1)
def _session_service() -> InMemorySessionService:
    return InMemorySessionService()


@lru_cache(maxsize=1)
def _runner() -> Runner:
    return Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=_session_service(),
    )


async def ask_agent(question: str) -> dict[str, object]:
    tracer = get_tracer()
    with tracer.start_as_current_span("qa_agent.ask") as span:
        span.set_attribute("input.value", question)
        session_id = f"session-{uuid4().hex}"
        await _session_service().create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )

        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=question)],
        )
        answer = ""
        event_count = 0
        final_author = None

        async for event in _runner().run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
        ):
            event_count += 1
            if event.is_final_response() and event.content:
                text = _content_text(event.content)
                if text:
                    answer = text
                    final_author = event.author

        span.set_attribute("qa.event_count", event_count)
        span.set_attribute("qa.final_author", final_author or "")
        span.set_attribute("output.value", answer)
        faithfulness = evaluate_faithfulness(question, answer)
        span.set_attribute("eval.faithfulness.label", str(faithfulness["label"]))
        span.set_attribute("eval.faithfulness.score", float(faithfulness["score"]))
        span.set_attribute("eval.faithfulness.explanation", str(faithfulness["explanation"]))
        return {
            "question": question,
            "answer": answer,
            "faithfulness": faithfulness,
            "session_id": session_id,
            "event_count": event_count,
        }


def _content_text(content: types.Content) -> str:
    parts = content.parts or []
    texts = [part.text for part in parts if getattr(part, "text", None)]
    return "\n".join(texts).strip()
