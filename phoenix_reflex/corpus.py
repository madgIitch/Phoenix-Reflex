from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    tags: tuple[str, ...]


CORPUS: tuple[Document, ...] = (
    Document(
        id="s0-runtime",
        title="Sprint 0 runtime",
        text=(
            "Sprint 0 validates the critical deployment path before RAG logic. "
            "The service runs as a code-owned FastAPI and Google ADK runtime, "
            "exposes /health and /hello, and emits a hello_world trace."
        ),
        tags=("sprint-0", "runtime", "cloud-run"),
    ),
    Document(
        id="s0-observability",
        title="Sprint 0 observability",
        text=(
            "Phoenix Reflex sends traces to Arize AX using arize.otel.register. "
            "The required AX values are ARIZE_API_KEY, ARIZE_SPACE_ID, "
            "ARIZE_PROJECT_NAME, and the EU endpoint https://otlp.eu-west-1a.arize.com/v1."
        ),
        tags=("sprint-0", "arize-ax", "tracing"),
    ),
    Document(
        id="s0-cloud-run",
        title="Sprint 0 Cloud Run deployment",
        text=(
            "The Cloud Run service is phoenix-reflex in europe-west1. It uses "
            "Secret Manager secrets named ARIZE_API_KEY, ARIZE_SPACE_ID, and "
            "GEMINI_API_KEY. The public service URL responds on /health and /hello."
        ),
        tags=("sprint-0", "cloud-run", "secrets"),
    ),
    Document(
        id="s1-goal",
        title="Sprint 1 goal",
        text=(
            "Sprint 1 adds a minimal RAG loop over a small curated corpus. The goal "
            "is a retriever tool connected to qa_agent, with traces showing both "
            "retrieval and model generation spans."
        ),
        tags=("sprint-1", "rag", "retriever"),
    ),
    Document(
        id="s1-corpus",
        title="Sprint 1 corpus requirements",
        text=(
            "The corpus should contain 10 to 20 short documents in a domain where "
            "the builder can judge answer quality. It must include at least one "
            "terminological ambiguity, one partially answerable question, and one "
            "unanswerable question that should force abstention."
        ),
        tags=("sprint-1", "corpus", "evaluation"),
    ),
    Document(
        id="s1-retriever",
        title="Sprint 1 retriever design",
        text=(
            "The MVP retriever can use embeddings with cosine similarity or BM25. "
            "Vertex RAG Engine is intentionally excluded from Sprint 1 so the demo "
            "stays small, transparent, and easy to debug."
        ),
        tags=("sprint-1", "retriever", "bm25"),
    ),
    Document(
        id="s1-prompt",
        title="Sprint 1 answer policy",
        text=(
            "qa_agent must answer only from retrieved context, cite document ids, "
            "and say it does not know when the context is missing, unrelated, or too weak. "
            "When abstaining, it should briefly explain what information is missing. "
            "This abstention behavior is part of the demo design."
        ),
        tags=("sprint-1", "prompt", "abstention"),
    ),
    Document(
        id="ambiguity-phoenix",
        title="Phoenix terminology ambiguity",
        text=(
            "In this project, Phoenix Reflex is the product name. Phoenix can also "
            "refer to Arize Phoenix, an observability project, or to unrelated city "
            "and mythology meanings. The agent should disambiguate using context."
        ),
        tags=("ambiguity", "phoenix", "naming"),
    ),
    Document(
        id="ax-vs-phoenix",
        title="Arize AX versus Phoenix Cloud",
        text=(
            "The current sprint 0 deployment uses Arize AX for tracing because the "
            "workspace provided ARIZE_API_KEY and ARIZE_SPACE_ID. Phoenix Cloud can "
            "remain an optional fallback, but AX is the validated backend."
        ),
        tags=("arize-ax", "phoenix", "tracing"),
    ),
    Document(
        id="mcp-role",
        title="MCP role in the demo",
        text=(
            "MCP is not the initial tracing transport. It is the runtime introspection "
            "layer used later so the agent can query traces, prompts, datasets, and "
            "experiments as tools."
        ),
        tags=("mcp", "introspection", "sprint-3"),
    ),
    Document(
        id="eval-faithfulness",
        title="Faithfulness evaluation",
        text=(
            "The first evaluation target is faithfulness over the final answer. A weak "
            "faithfulness score should identify likely hallucination and later feed a "
            "regression dataset example."
        ),
        tags=("evaluation", "faithfulness", "sprint-2"),
    ),
    Document(
        id="known-gap",
        title="Known missing information",
        text=(
            "The corpus does not contain budget limits, team member biographies, exact "
            "hackathon judging weights, or production traffic forecasts. Questions "
            "about those topics should be treated as unsupported."
        ),
        tags=("abstention", "unsupported", "gaps"),
    ),
)
