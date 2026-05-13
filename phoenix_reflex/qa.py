from __future__ import annotations

import re
from functools import lru_cache
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from phoenix_reflex.evaluator import evaluate_document_relevance, evaluate_faithfulness
from phoenix_reflex.observability import get_tracer
from phoenix_reflex.reflex import (
    format_reflex_context,
    maybe_create_improvement_case,
    record_trace_summary,
)
from phoenix_reflex.retriever import retrieve_documents
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
        extra_context = None
        extra_context_ids = None
        if _is_introspection_question(question):
            extra_context, extra_context_ids = format_reflex_context()

        agent_retrieved = await _extract_agent_retrieval(session_id)
        if agent_retrieved:
            retrieved_documents = agent_retrieved["documents"]
            valid_ids = set(agent_retrieved["valid_citation_ids"])
        else:
            fallback = retrieve_documents(question, top_k=5)
            retrieved_documents = fallback.get("documents", [])
            valid_ids = set(fallback.get("valid_citation_ids", []))
        phantom_citations = _find_phantom_citations(answer, valid_ids)
        detected_phantom_citations = set(phantom_citations)
        correction_rounds = 0
        while phantom_citations and correction_rounds < 2:
            span.set_attribute("eval.phantom_citations", ", ".join(phantom_citations))
            span.set_attribute("eval.phantom_citation_count", len(phantom_citations))
            corrected = await _correct_phantom_citations(
                session_id=session_id,
                phantom_citations=phantom_citations,
                valid_ids=valid_ids,
            )
            correction_rounds += 1
            event_count += 1
            if corrected:
                answer = corrected
                span.set_attribute("eval.citation_correction_applied", True)
                span.set_attribute("output.value", answer)
                phantom_citations = _find_phantom_citations(answer, valid_ids)
            else:
                break
        corrected_phantom_citations = detected_phantom_citations - phantom_citations
        span.set_attribute("eval.phantom_citations_detected_count", len(detected_phantom_citations))
        span.set_attribute("eval.phantom_citations_corrected_count", len(corrected_phantom_citations))
        if phantom_citations:
            span.set_attribute("eval.citation_correction_failed", True)
        document_relevance = evaluate_document_relevance(
            question,
            retrieved_documents=retrieved_documents,
        )
        faithfulness = evaluate_faithfulness(
            question,
            answer,
            extra_context=extra_context,
            extra_context_ids=extra_context_ids,
            retrieved_documents=retrieved_documents,
        )
        answer_quality = _assess_answer_quality(question, answer, faithfulness, document_relevance)
        span.set_attribute("eval.faithfulness.label", str(faithfulness["label"]))
        span.set_attribute("eval.faithfulness.score", float(faithfulness["score"]))
        span.set_attribute("eval.faithfulness.explanation", str(faithfulness["explanation"]))
        span.set_attribute("eval.document_relevance.label", str(document_relevance["label"]))
        span.set_attribute("eval.document_relevance.score", float(document_relevance["score"]))
        span.set_attribute("eval.document_relevance.explanation", str(document_relevance["explanation"]))
        span.set_attribute("eval.answer_quality.label", str(answer_quality["label"]))
        span.set_attribute("eval.answer_quality.explanation", str(answer_quality["explanation"]))
        failure_mode = _classify_failure_mode(faithfulness, document_relevance, answer_quality)
        span.set_attribute("eval.failure_mode", failure_mode)
        summary = record_trace_summary(
            question=question,
            answer=answer,
            faithfulness=faithfulness,
            document_relevance=document_relevance,
            answer_quality=answer_quality,
            failure_mode=failure_mode,
            session_id=session_id,
            event_count=event_count,
            retrieved_documents=retrieved_documents,
        )
        improvement_case = maybe_create_improvement_case(summary)
        if improvement_case:
            span.set_attribute("improvement.case_id", improvement_case["case_id"])
            span.set_attribute("improvement.dataset", improvement_case["dataset"])
        return {
            "question": question,
            "answer": answer,
            "faithfulness": faithfulness,
            "document_relevance": document_relevance,
            "answer_quality": answer_quality,
            "failure_mode": failure_mode,
            "phantom_citations": sorted(phantom_citations),
            "phantom_citations_detected_count": len(detected_phantom_citations),
            "phantom_citations_corrected_count": len(corrected_phantom_citations),
            "improvement_case": improvement_case,
            "session_id": session_id,
            "event_count": event_count,
            "retrieved_documents": retrieved_documents,
        }


def _content_text(content: types.Content) -> str:
    parts = content.parts or []
    texts = [part.text for part in parts if getattr(part, "text", None)]
    return "\n".join(texts).strip()


def _is_introspection_question(question: str) -> bool:
    normalized = question.lower()
    keywords = (
        "traza",
        "trace",
        "caso de mejora",
        "casos de mejora",
        "improvement",
        "regression",
        "regresion",
        "introspeccion",
        "introspection",
    )
    return any(keyword in normalized for keyword in keywords)


def _classify_failure_mode(
    faithfulness: dict[str, object],
    document_relevance: dict[str, object],
    answer_quality: dict[str, object] | None = None,
) -> str:
    faithfulness_score = float(faithfulness.get("score", 0.0))
    relevance_score = float(document_relevance.get("score", 0.0))
    if (
        faithfulness_score >= 0.75
        and (answer_quality or {}).get("label") == "suspicious"
    ):
        return "answer_quality"
    if faithfulness_score >= 0.75:
        return "none"
    if relevance_score < 0.75:
        return "retrieval"
    return "generation"


def _assess_answer_quality(
    question: str,
    answer: str,
    faithfulness: dict[str, object],
    document_relevance: dict[str, object],
) -> dict[str, object]:
    reasons: list[str] = []
    normalized_question = _normalize_for_language_hint(question)
    normalized_answer = _normalize_for_language_hint(answer)
    relevance_score = float(document_relevance.get("score", 0.0))
    faithfulness_score = float(faithfulness.get("score", 0.0))

    if _looks_spanish(normalized_question) and _looks_english(normalized_answer):
        reasons.append("language_mismatch")

    abstention_markers = (
        "cannot answer",
        "can't answer",
        "i do not know",
        "no puedo responder",
        "no puedo contestar",
        "no se puede responder",
        "no lo se",
    )
    if relevance_score >= 0.75 and any(
        marker in normalized_answer for marker in abstention_markers
    ):
        reasons.append("possible_over_abstention")

    label = "suspicious" if reasons else "ok"
    explanation = (
        "Faithful answer, but potentially poor user-intent handling: " + ", ".join(reasons)
        if label == "suspicious" and faithfulness_score >= 0.75
        else "Unfaithful answer also shows answer-quality warning(s): " + ", ".join(reasons)
        if label == "suspicious"
        else "No obvious answer-quality issue detected."
    )
    return {
        "label": label,
        "reasons": reasons,
        "explanation": explanation,
    }


_CITATION_RE = re.compile(r"\[([^\]]+)\]")


async def _extract_agent_retrieval(session_id: str) -> dict[str, object] | None:
    """Read retrieve_documents results from the agent's actual tool calls in this session."""
    try:
        session = await _session_service().get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        if not session:
            return None
        documents: list[dict] = []
        valid_ids: list[str] = []
        for event in session.events or []:
            if not event.content:
                continue
            for part in event.content.parts or []:
                fr = getattr(part, "function_response", None)
                if fr and getattr(fr, "name", None) == "retrieve_documents":
                    response = fr.response or {}
                    ids = response.get("valid_citation_ids", [])
                    docs = response.get("documents", [])
                    if ids:
                        valid_ids = ids
                        documents = docs
        if not valid_ids:
            return None
        return {"valid_citation_ids": valid_ids, "documents": documents}
    except Exception:
        return None


async def _correct_phantom_citations(
    session_id: str,
    phantom_citations: set[str],
    valid_ids: set[str],
) -> str:
    """Send a correction turn in the same session to strip phantom citations."""
    phantom_list = ", ".join(sorted(phantom_citations))
    valid_list = ", ".join(sorted(valid_ids)) if valid_ids else "none"
    correction = (
        f"Your previous answer cited document IDs that were NOT returned by retrieve_documents: {phantom_list}. "
        f"These pages do not exist in the retrieved context. "
        f"The only valid citation IDs for this query are: {valid_list}. "
        "Please rewrite your answer using only those IDs. "
        "If the retrieved documents do not contain enough information to answer a part of the question, "
        "say so explicitly instead of citing other pages."
    )
    correction_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=correction)],
    )
    corrected_answer = ""
    async for event in _runner().run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=correction_message,
    ):
        if event.is_final_response() and event.content:
            text = _content_text(event.content)
            if text:
                corrected_answer = text
    return corrected_answer


def _find_phantom_citations(answer: str, valid_ids: set[str]) -> set[str]:
    """Return citation IDs in the answer that were not in the retrieved set."""
    found = {m.group(1) for m in _CITATION_RE.finditer(answer)}
    return {cid for cid in found if cid not in valid_ids and cid.startswith("pdf:")}


def _looks_spanish(text: str) -> bool:
    """Demo-grade language hint; replace with a real detector before production."""
    markers = (
        " el ",
        " la ",
        " los ",
        " las ",
        " un ",
        " una ",
        " de ",
        " es ",
        " a ",
        " que ",
        " como ",
        " cual ",
        " cuales ",
        " donde ",
        " puede ",
        " pueden ",
        " tiene ",
        " segun ",
        " sobre ",
        " para ",
        " con ",
        " no ",
    )
    return _marker_hits(text, markers) >= 2


def _looks_english(text: str) -> bool:
    """Demo-grade language hint; replace with a real detector before production."""
    markers = (
        " the ",
        " and ",
        " or ",
        " of ",
        " to ",
        " in ",
        " based on ",
        " according to ",
        " i cannot ",
        " i can ",
        " documents ",
        " context ",
        " question ",
        " answer ",
    )
    return _marker_hits(text, markers) >= 2


def _normalize_for_language_hint(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return f" {normalized.strip()} "


def _marker_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)
