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


def evaluate_faithfulness(question: str, answer: str) -> dict[str, Any]:
    """Evaluate final answer faithfulness against retrieved context."""
    tracer = get_tracer()
    with tracer.start_as_current_span("faithfulness_eval") as span:
        retrieved = retrieve_documents(question, top_k=5)
        context = _format_context(retrieved["documents"])
        span.set_attribute("input.value", question)
        span.set_attribute("eval.name", "faithfulness")
        span.set_attribute("eval.context_doc_ids", ", ".join(doc["id"] for doc in retrieved["documents"]))

        if not answer.strip():
            result = {
                "label": "unfaithful",
                "score": 0.0,
                "explanation": "No answer was produced.",
                "context_doc_ids": [doc["id"] for doc in retrieved["documents"]],
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

        result["context_doc_ids"] = [doc["id"] for doc in retrieved["documents"]]
        _set_eval_attributes(span, result)
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
