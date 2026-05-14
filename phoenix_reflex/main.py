from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from phoenix_reflex.document_store import (
    delete_document,
    get_document,
    list_chunks,
    list_documents,
    set_anchor_questions,
    update_chunk_enabled,
)
from phoenix_reflex.evaluator import evaluate_document_relevance, evaluate_faithfulness
from phoenix_reflex.experiments import generate_prompt_candidate, run_prompt_experiment
from phoenix_reflex.ingestion import ingest_pdf
from phoenix_reflex.mcp import phoenix_mcp_status
from phoenix_reflex.observability import configure_tracing, get_tracer
from phoenix_reflex.prompts import list_prompts, promote_prompt_tag
from phoenix_reflex.qa import ask_agent
from phoenix_reflex.reflex import (
    add_improvement_case,
    export_trace_io,
    get_trace_summary,
    list_improvement_cases,
    list_recent_trace_summaries,
)
from phoenix_reflex.retriever import retrieve_documents


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class FaithfulnessDemoRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=4000)


class ChunkUpdateRequest(BaseModel):
    enabled: bool


class AnchorQuestionsRequest(BaseModel):
    questions: list[str] = Field(..., min_length=1, max_length=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tracer_provider = configure_tracing()
    yield
    if tracer_provider is not None:
        tracer_provider.shutdown()


app = FastAPI(
    title="Phoenix Reflex",
    description="Regression-driven PDF RAG service.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/observability/mcp")
def observability_mcp() -> dict[str, object]:
    status = phoenix_mcp_status()
    tracing_backend = (
        "arize-ax"
        if os.getenv("ARIZE_API_KEY")
        else "phoenix"
        if os.getenv("PHOENIX_API_KEY")
        else "disabled"
    )
    return {
        **status,
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "tracing_backend": tracing_backend,
        "note": (
            "Phoenix MCP is ready for the demo."
            if status["demo_ready"]
            else "Phoenix MCP demo is not ready; check missing fields before recording."
        ),
    }


@app.get("/retrieve")
def retrieve(query: str, top_k: int = 4) -> dict[str, object]:
    return retrieve_documents(query=query, top_k=top_k)


@app.post("/documents/pdf")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    try:
        return await ingest_pdf(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/documents")
def documents() -> dict[str, object]:
    return {"documents": list_documents()}


@app.get("/documents/search")
def documents_search(query: str, top_k: int = 6) -> dict[str, object]:
    return retrieve_documents(query=query, top_k=top_k)


@app.get("/documents/{document_id}")
def document(document_id: str) -> dict[str, object]:
    found = get_document(document_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": found}


@app.get("/documents/{document_id}/chunks")
def document_chunks(document_id: str) -> dict[str, object]:
    if get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"chunks": list_chunks(document_id=document_id)}


@app.patch("/documents/chunks/{chunk_id}")
def patch_chunk(chunk_id: str, request: ChunkUpdateRequest) -> dict[str, object]:
    updated = update_chunk_enabled(chunk_id, request.enabled)
    if updated is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {"chunk": updated}


@app.put("/documents/{document_id}/anchor-questions")
def put_anchor_questions(document_id: str, request: AnchorQuestionsRequest) -> dict[str, object]:
    questions = [q.strip() for q in request.questions if q.strip()]
    if not questions:
        raise HTTPException(status_code=400, detail="At least one non-empty question is required")
    updated = set_anchor_questions(document_id, questions)
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": document_id, "anchor_questions": questions}


@app.delete("/documents/{document_id}")
def remove_document(document_id: str) -> dict[str, object]:
    deleted = delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True, "document_id": document_id}


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
            failure_mode="generation",
        )
    return {
        "question": request.question,
        "answer": request.answer,
        "faithfulness": faithfulness,
        "improvement_case": improvement_case,
    }


@app.get("/eval/document-relevance")
def eval_document_relevance(query: str) -> dict[str, object]:
    return {
        "query": query,
        "document_relevance": evaluate_document_relevance(query),
    }


@app.get("/introspection/traces")
def introspection_traces(limit: int = 5) -> dict[str, object]:
    return list_recent_trace_summaries(limit=limit)


@app.get("/introspection/traces/export")
def introspection_trace_export(limit: int = 50) -> dict[str, object]:
    return export_trace_io(limit=limit)


@app.get("/introspection/traces/{session_id}")
def introspection_trace(session_id: str) -> dict[str, object]:
    trace = get_trace_summary(session_id)
    if not trace["found"]:
        raise HTTPException(status_code=404, detail="Trace summary not found")
    return trace


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
def prompt_experiment(n_runs: int = 1) -> dict[str, object]:
    return run_prompt_experiment(n_runs=n_runs)


@app.post("/prompts/promote")
def promote_prompt(source_tag: str = "candidate", target_tag: str = "staging") -> dict[str, object]:
    return promote_prompt_tag(source_tag=source_tag, target_tag=target_tag)
