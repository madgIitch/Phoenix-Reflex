from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from opentelemetry import trace

load_dotenv()

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def configure_tracing() -> Any | None:
    """Configure Arize AX or Phoenix tracing once per process."""
    tracer_provider = _configure_arize_ax() or _configure_phoenix()
    if tracer_provider is None:
        logger.info("Tracing is disabled; configure Arize AX or Phoenix credentials")
        return None

    _instrument_google_adk(tracer_provider)
    _instrument_google_genai(tracer_provider)
    return tracer_provider


def _configure_arize_ax() -> Any | None:
    api_key = os.getenv("ARIZE_API_KEY", "").strip()
    space_id = os.getenv("ARIZE_SPACE_ID", "").strip()
    if not api_key or not space_id:
        return None

    try:
        from arize.otel import register

        kwargs: dict[str, Any] = {
            "space_id": space_id,
            "api_key": api_key,
            "project_name": os.getenv("ARIZE_PROJECT_NAME", "phoenix-reflex"),
            "batch": False,
        }
        endpoint = os.getenv("ARIZE_OTEL_ENDPOINT", "").strip()
        if endpoint:
            kwargs["endpoint"] = endpoint

        return register(**kwargs)
    except Exception:
        logger.exception("Arize AX tracing could not be configured")
        return None


def _configure_phoenix() -> Any | None:
    if not os.getenv("PHOENIX_API_KEY", "").strip():
        return None

    try:
        from phoenix.otel import register

        return register(
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "phoenix-reflex"),
            auto_instrument=True,
            batch=False,
            verbose=False,
        )
    except Exception:
        logger.exception("Phoenix tracing could not be configured")
        return None


def _instrument_google_adk(tracer_provider: Any) -> None:
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        logger.exception("Google ADK instrumentation could not be configured")


def _instrument_google_genai(tracer_provider: Any) -> None:
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        logger.exception("Google GenAI instrumentation could not be configured")


def get_tracer():
    configure_tracing()
    return trace.get_tracer("phoenix-reflex")
