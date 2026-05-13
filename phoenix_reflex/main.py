from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI
from pydantic import BaseModel, Field

from phoenix_reflex.evaluator import evaluate_faithfulness
from phoenix_reflex.experiments import generate_prompt_candidate, run_prompt_experiment
from phoenix_reflex.observability import configure_tracing, get_tracer
from phoenix_reflex.prompts import list_prompts, promote_prompt_tag
from phoenix_reflex.qa import ask_agent
from phoenix_reflex.reflex import (
    add_improvement_case,
    list_improvement_cases,
    list_recent_trace_summaries,
)
from phoenix_reflex.retriever import retrieve_documents


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class FaithfulnessDemoRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=4000)


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
        project = os.getenv(
            "ARIZE_PROJECT_NAME",
            os.getenv("PHOENIX_PROJECT_NAME", "phoenix-reflex"),
        )
        backend = "arize-ax" if os.getenv("ARIZE_API_KEY") else "phoenix"
        message = "Phoenix Reflex hello-world trace emitted."
        span.set_attribute("output.value", message)
        span.set_attribute("app.observability_backend", backend)
        return {
            "message": message,
            "observability_backend": backend,
            "project": project,
            "timestamp": datetime.now(UTC).isoformat(),
        }


@app.get("/retrieve")
def retrieve(query: str, top_k: int = 4) -> dict[str, object]:
    return retrieve_documents(query=query, top_k=top_k)


@app.post("/ask")
async def ask(request: AskRequest) -> dict[str, object]:
    return await ask_agent(request.question)


@app.post("/eval/faithfulness")
def eval_faithfulness(request: FaithfulnessDemoRequest) -> dict[str, object]:
    faithfulness = evaluate_faithfulness(request.question, request.answer)
    improvement_case = None
    if float(faithfulness.get("score", 0.0)) < 0.75:
        improvement_case = add_improvement_case(
            question=request.question,
            answer=request.answer,
            faithfulness_label=str(faithfulness.get("label", "unknown")),
            faithfulness_score=float(faithfulness.get("score", 0.0)),
            explanation=str(faithfulness.get("explanation", "")),
            source_session_id="manual-eval",
        )
    return {
        "question": request.question,
        "answer": request.answer,
        "faithfulness": faithfulness,
        "improvement_case": improvement_case,
    }


@app.get("/introspection/traces")
def introspection_traces(limit: int = 5) -> dict[str, object]:
    return list_recent_trace_summaries(limit=limit)


@app.get("/improvement-cases")
def improvement_cases(limit: int = 10) -> dict[str, object]:
    return list_improvement_cases(limit=limit)


@app.get("/prompts")
def prompts() -> dict[str, object]:
    return list_prompts()


@app.post("/prompts/candidate")
def prompts_candidate() -> dict[str, object]:
    return generate_prompt_candidate()


@app.post("/experiments/prompt")
def prompt_experiment() -> dict[str, object]:
    return run_prompt_experiment()


@app.post("/prompts/promote")
def promote_prompt(source_tag: str = "candidate", target_tag: str = "staging") -> dict[str, object]:
    return promote_prompt_tag(source_tag=source_tag, target_tag=target_tag)
