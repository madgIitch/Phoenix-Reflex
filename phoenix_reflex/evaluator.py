from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

from phoenix_reflex.observability import get_tracer
from phoenix_reflex.retriever import retrieve_documents

load_dotenv()

FAITHFULNESS_PROMPT = """You are a strict faithfulness judge for a RAG system.

Evaluate whether the answer is fully supported by the retrieved context.

Rules:
- Score 1.0 only when every factual claim in the answer is supported by the context.
- Score 0.5 when the answer is mostly supported but contains minor unsupported wording.
- Score 0.0 when the answer contains important unsupported claims or contradicts the context.
- If the answer correctly abstains because context is missing, score 1.0.
- Return JSON only.

JSON schema:
{{
  "label": "faithful" | "partially_faithful" | "unfaithful",
  "score": 1.0 | 0.5 | 0.0,
  "explanation": "short explanation"
}}

[Question]
{question}

[Retrieved Context]
{context}

[Answer]
{answer}
"""

DOCUMENT_RELEVANCE_PROMPT = """You are a strict retrieval relevance judge for a RAG system.

Evaluate whether the retrieved context contains enough relevant information to answer the question.

Rules:
- Score 1.0 when the retrieved documents directly contain the information needed to answer.
- Score 0.5 when the documents are related but incomplete or indirect.
- Score 0.0 when no documents are retrieved or the documents are unrelated.
- For compound questions, evaluate whether the context supports each required part.
- Do not infer missing applicability conditions from general topic overlap.
- A document that discusses a category does not automatically answer questions about every entity, place, relationship, or condition in that category.
- Treat incomplete sentence fragments as incomplete evidence.
- Return JSON only.

JSON schema:
{{
  "label": "relevant" | "partially_relevant" | "irrelevant",
  "score": 1.0 | 0.5 | 0.0,
  "explanation": "short explanation"
}}

[Question]
{question}

[Retrieved Context]
{context}
"""


def evaluate_faithfulness(
    question: str,
    answer: str,
    extra_context: str | None = None,
    extra_context_ids: list[str] | None = None,
    retrieved_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate final answer faithfulness against retrieved context."""
    tracer = get_tracer()
    with tracer.start_as_current_span("faithfulness_eval") as span:
        if retrieved_documents is not None:
            docs = retrieved_documents
        else:
            docs = retrieve_documents(question, top_k=5)["documents"]
        context = _format_context(docs)
        if extra_context:
            context = f"{context}\n\n{extra_context}"
        context_doc_ids = [doc["id"] for doc in docs]
        if extra_context_ids:
            context_doc_ids.extend(extra_context_ids)

        span.set_attribute("input.value", question)
        span.set_attribute("eval.name", "faithfulness")
        span.set_attribute("eval.context_doc_ids", ", ".join(context_doc_ids))
        span.set_attribute("critic.implementation", "llm_judge")

        if not answer.strip():
            result = {
                "label": "unfaithful",
                "score": 0.0,
                "explanation": "No answer was produced.",
                "context_doc_ids": context_doc_ids,
            }
            _set_eval_attributes(span, result)
            return result

        try:
            response_text = _judge(question=question, answer=answer, context=context)
            result = _parse_judge_response(response_text)
        except Exception as exc:
            result = {
                "label": "eval_error",
                "score": 0.0,
                "explanation": f"Faithfulness judge failed: {exc}",
            }

        result["context_doc_ids"] = context_doc_ids
        _set_eval_attributes(span, result)
        return result


def evaluate_document_relevance(
    question: str,
    retrieved_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate whether retrieval found enough context for the question."""
    tracer = get_tracer()
    with tracer.start_as_current_span("document_relevance_eval") as span:
        if retrieved_documents is not None:
            docs = retrieved_documents
        else:
            docs = retrieve_documents(question, top_k=5)["documents"]
        context = _format_context(docs)
        context_doc_ids = [doc["id"] for doc in docs]
        span.set_attribute("input.value", question)
        span.set_attribute("eval.name", "document_relevance")
        span.set_attribute("eval.context_doc_ids", ", ".join(context_doc_ids))
        span.set_attribute("critic.implementation", "llm_judge")

        if not docs:
            result = {
                "label": "irrelevant",
                "score": 0.0,
                "explanation": "No documents were retrieved.",
                "context_doc_ids": context_doc_ids,
            }
            _set_relevance_attributes(span, result)
            return result

        try:
            response_text = _judge_relevance(question=question, context=context)
            result = _parse_relevance_response(response_text)
        except Exception as exc:
            result = {
                "label": "eval_error",
                "score": 0.0,
                "explanation": f"Document relevance judge failed: {exc}",
            }

        result["context_doc_ids"] = context_doc_ids
        _set_relevance_attributes(span, result)
        return result


def _judge(question: str, answer: str, context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for faithfulness eval")

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    response = client.models.generate_content(
        model=model,
        contents=FAITHFULNESS_PROMPT.format(
            question=question,
            context=context,
            answer=answer,
        ),
    )
    return response.text or ""


def _judge_relevance(question: str, context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for document relevance eval")

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    response = client.models.generate_content(
        model=model,
        contents=DOCUMENT_RELEVANCE_PROMPT.format(
            question=question,
            context=context,
        ),
    )
    return response.text or ""


def _parse_judge_response(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    data = json.loads(cleaned)
    label = str(data.get("label", "unfaithful"))
    score = float(data.get("score", 0.0))
    explanation = str(data.get("explanation", "")).strip()

    if label not in {"faithful", "partially_faithful", "unfaithful"}:
        label = "unfaithful"
    if score not in {0.0, 0.5, 1.0}:
        score = max(0.0, min(1.0, score))

    return {
        "label": label,
        "score": score,
        "explanation": explanation,
    }


def _parse_relevance_response(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    data = json.loads(cleaned)
    label = str(data.get("label", "irrelevant"))
    score = float(data.get("score", 0.0))
    explanation = str(data.get("explanation", "")).strip()

    if label not in {"relevant", "partially_relevant", "irrelevant"}:
        label = "irrelevant"
    if score not in {0.0, 0.5, 1.0}:
        score = max(0.0, min(1.0, score))

    return {
        "label": label,
        "score": score,
        "explanation": explanation,
    }


def _format_context(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "No documents retrieved."
    return "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['text']}" for doc in documents
    )


def _set_eval_attributes(span: Any, result: dict[str, Any]) -> None:
    span.set_attribute("eval.faithfulness.label", str(result["label"]))
    span.set_attribute("eval.faithfulness.score", float(result["score"]))
    span.set_attribute("eval.faithfulness.explanation", str(result["explanation"]))
    span.set_attribute("output.value", json.dumps(result, ensure_ascii=False))


def _set_relevance_attributes(span: Any, result: dict[str, Any]) -> None:
    span.set_attribute("eval.document_relevance.label", str(result["label"]))
    span.set_attribute("eval.document_relevance.score", float(result["score"]))
    span.set_attribute("eval.document_relevance.explanation", str(result["explanation"]))
    span.set_attribute("output.value", json.dumps(result, ensure_ascii=False))
