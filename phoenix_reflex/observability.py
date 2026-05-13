from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def configure_tracing() -> Any | None:
    """Configure Phoenix tracing once per process."""
    if not os.getenv("PHOENIX_API_KEY", "").strip():
        logger.info("PHOENIX_API_KEY is not set; Phoenix tracing is disabled")
        return None

    try:
        from phoenix.otel import register

        tracer_provider = register(
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "phoenix-reflex"),
            auto_instrument=True,
            batch=False,
            verbose=False,
        )
    except Exception:
        logger.exception("Phoenix tracing could not be configured")
        return None

    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        logger.exception("Google ADK instrumentation could not be configured")

    return tracer_provider


def get_tracer():
    configure_tracing()
    return trace.get_tracer("phoenix-reflex")
