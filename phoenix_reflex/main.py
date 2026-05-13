from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI

from phoenix_reflex.observability import configure_tracing, get_tracer


@asynccontextmanager
async def lifespan(app: FastAPI):
    tracer_provider = configure_tracing()
    yield
    if tracer_provider is not None:
        tracer_provider.shutdown()


app = FastAPI(
    title="Phoenix Reflex",
    description="Sprint 0: trivial ADK app with Phoenix tracing.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "phoenix-reflex",
        "status": "ready",
        "health": "/health",
        "hello_trace": "/hello",
    }


@app.get("/hello")
def hello() -> dict[str, str]:
    tracer = get_tracer()
    with tracer.start_as_current_span("hello_world") as span:
        span.set_attribute("app.sprint", "0")
        span.set_attribute("app.agent", "qa_agent")
        span.set_attribute("app.runtime", "google-adk")
        message = "Phoenix Reflex hello-world trace emitted."
        span.set_attribute("output.value", message)
        return {
            "message": message,
            "project": os.getenv("PHOENIX_PROJECT_NAME", "phoenix-reflex"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
