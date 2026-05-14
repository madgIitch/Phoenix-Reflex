from __future__ import annotations

import re
from functools import lru_cache
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from phoenix_reflex.evaluator import evaluate_document_relevance, evaluate_faithfulness
from phoenix_reflex.mcp import PHOENIX_MCP_TOOL_FILTER, phoenix_mcp_status
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

        # Inject runtime context into the message BEFORE the agent runs so it
        # can actually use it. (Previously this was computed post-run and only
        # reached the faithfulness evaluator, not the agent itself.)
        is_introspection = _is_introspection_question(question)
        extra_context = None
        extra_context_ids = None
        if is_introspection:
            extra_context, extra_context_ids = format_reflex_context()

        if extra_context:
            message_text = (
                f"[Runtime Context — use this to answer the question]\n"
                f"{extra_context}\n\n"
                f"[Question]\n{question}"
            )
        else:
            message_text = question

        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message_text)],
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
        phoenix_mcp_calls = await _extract_phoenix_mcp_calls(session_id)
        if is_introspection and not phoenix_mcp_calls and phoenix_mcp_status()["demo_ready"]:
            forced_answer, forced_event_count = await _force_phoenix_mcp_introspection(
                session_id=session_id,
                question=question,
            )
            event_count += forced_event_count
            if forced_answer:
                answer = forced_answer
                span.set_attribute("output.value", answer)
            phoenix_mcp_calls = await _extract_phoenix_mcp_calls(session_id)
            span.set_attribute("qa.event_count", event_count)
        phoenix_mcp_tools = sorted({str(call["tool"]) for call in phoenix_mcp_calls})
        span.set_attribute("phoenix_mcp.called", bool(phoenix_mcp_calls))
        span.set_attribute("phoenix_mcp.call_count", len(phoenix_mcp_calls))
        span.set_attribute("phoenix_mcp.tools", ", ".join(phoenix_mcp_tools))

        agent_retrieved = await _extract_agent_retrieval(session_id)
        if agent_retrieved:
            retrieved_documents = agent_retrieved["documents"]
            valid_ids = set(agent_retrieved["valid_citation_ids"])
        elif is_introspection:
            retrieved_documents = []
            valid_ids = set()
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
        style_issues = _find_answer_style_issues(answer)
        style_correction_applied = False
        if style_issues:
            corrected = await _correct_answer_style(
                session_id=session_id,
                style_issues=style_issues,
                valid_ids=valid_ids,
            )
            event_count += 1
            if corrected:
                answer = corrected
                style_correction_applied = True
                span.set_attribute("eval.style_correction_applied", True)
                span.set_attribute("eval.style_issues", ", ".join(style_issues))
                span.set_attribute("output.value", answer)
                phantom_citations = _find_phantom_citations(answer, valid_ids)
                if phantom_citations:
                    span.set_attribute("eval.style_correction_phantom_citations", ", ".join(phantom_citations))
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
            phantom_citations_detected_count=len(detected_phantom_citations),
            phantom_citations_corrected_count=len(corrected_phantom_citations),
            phantom_citations=sorted(phantom_citations),
            style_correction_applied=style_correction_applied,
            phoenix_mcp_called=bool(phoenix_mcp_calls),
            phoenix_mcp_call_count=len(phoenix_mcp_calls),
            phoenix_mcp_tools=phoenix_mcp_tools,
            phoenix_mcp_evidence=phoenix_mcp_calls,
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
            "style_correction_applied": style_correction_applied,
            "improvement_case": improvement_case,
            "session_id": session_id,
            "event_count": event_count,
            "retrieved_documents": retrieved_documents,
            "phoenix_mcp_called": bool(phoenix_mcp_calls),
            "phoenix_mcp_call_count": len(phoenix_mcp_calls),
            "phoenix_mcp_tools": phoenix_mcp_tools,
            "phoenix_mcp_evidence": phoenix_mcp_calls,
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

    if _find_answer_style_issues(answer):
        reasons.append("internal_mechanics_leak")

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


async def _extract_phoenix_mcp_calls(session_id: str) -> list[dict[str, object]]:
    """Read Phoenix MCP tool responses from the agent session for demo evidence."""
    try:
        session = await _session_service().get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        if not session:
            return []
        calls: list[dict[str, object]] = []
        for event in session.events or []:
            if not event.content:
                continue
            for part in event.content.parts or []:
                fr = getattr(part, "function_response", None)
                name = str(getattr(fr, "name", "") or "")
                if not fr or not _is_phoenix_mcp_tool_name(name):
                    continue
                calls.append(
                    {
                        "tool": name,
                        "summary": _summarize_tool_response(fr.response),
                    }
                )
        return calls
    except Exception:
        return []


def _is_phoenix_mcp_tool_name(name: str) -> bool:
    normalized = name.lower().replace("_", "-")
    if normalized.startswith("phoenix"):
        return True
    return normalized in {tool.lower() for tool in PHOENIX_MCP_TOOL_FILTER}


def _summarize_tool_response(response: object) -> str:
    if response is None:
        return "No response payload."
    if isinstance(response, dict):
        keys = list(response.keys())[:8]
        count_bits: list[str] = []
        for key, value in response.items():
            if isinstance(value, list):
                count_bits.append(f"{key}={len(value)}")
            elif isinstance(value, dict):
                count_bits.append(f"{key}.keys={len(value)}")
        prefix = f"keys={', '.join(keys)}" if keys else "empty object"
        suffix = f"; {', '.join(count_bits[:4])}" if count_bits else ""
        return (prefix + suffix)[:500]
    if isinstance(response, list):
        return f"list items={len(response)}"
    return str(response)[:500]


async def _force_phoenix_mcp_introspection(session_id: str, question: str) -> tuple[str, int]:
    """Second pass for demo-critical introspection questions when the first turn skipped MCP."""
    mcp_tools = ", ".join(f"phoenix_{tool}" for tool in PHOENIX_MCP_TOOL_FILTER)
    correction = (
        "This is an observability introspection request, not a PDF retrieval request. "
        "Use Phoenix MCP now before answering. Available Phoenix MCP tools include: "
        f"{mcp_tools}. "
        "Inspect the latest traces or spans, then answer the original question with what failed "
        "and the next concrete improvement. Original question: "
        f"{question}"
    )
    correction_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=correction)],
    )
    corrected_answer = ""
    event_count = 0
    async for event in _runner().run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=correction_message,
    ):
        event_count += 1
        if event.is_final_response() and event.content:
            text = _content_text(event.content)
            if text:
                corrected_answer = text
    return corrected_answer, event_count


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


async def _correct_answer_style(
    session_id: str,
    style_issues: list[str],
    valid_ids: set[str],
) -> str:
    """Send a correction turn when the answer violates generic response constraints."""
    valid_list = ", ".join(sorted(valid_ids)) if valid_ids else "none"
    issue_list = ", ".join(style_issues)
    correction = (
        f"Your previous answer violated these answer constraints: {issue_list}. "
        "Rewrite the answer for the user. Do not mention retrieval mechanics, tools, context, or the system. "
        "Use only facts directly supported by the returned documents. "
        "For each part of a compound question, answer only if the returned text directly supports it; "
        "otherwise say that the provided documents do not cover that part. "
        "Do not use background knowledge or common-sense assumptions to bridge gaps. "
        "Do not turn incomplete sentence fragments into standalone facts. "
        f"Use only these citation IDs: {valid_list}."
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


def _find_answer_style_issues(answer: str) -> list[str]:
    # Only match multi-word phrases where the LLM is clearly describing its own
    # retrieval mechanics, not citing technical content from the uploaded document.
    # Single words like "context", "tool", "system" are standard tech vocabulary
    # and produce false positives with technical PDFs.
    normalized = _normalize_for_language_hint(answer)
    issues: list[str] = []
    meta_mechanic_phrases = (
        # English meta-phrases
        " based on the retrieved ",
        " according to the retrieved ",
        " the retrieved documents ",
        " from the retrieved context ",
        " in the retrieved context ",
        " i retrieved ",
        " i used the tool ",
        " the tool returned ",
        " the system provided me ",
        " my retrieval ",
        # Spanish meta-phrases
        " según el contexto recuperado ",
        " de los documentos recuperados ",
        " los documentos recuperados ",
        " el contexto recuperado ",
        " recuperé ",
        " usé la herramienta ",
        " la herramienta me devolvió ",
        " el sistema me proporcionó ",
    )
    if any(phrase in normalized for phrase in meta_mechanic_phrases):
        issues.append("mentions_internal_mechanics")
    return issues


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
    # Only use stopwords that are unambiguous English words; avoid single-word
    # tech terms (" context ", " question ", " answer ") that are routinely used
    # in Spanish technical prose without implying an English response.
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
        " is ",
        " this ",
        " it ",
        " are ",
        " with ",
    )
    return _marker_hits(text, markers) >= 5


def _normalize_for_language_hint(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return f" {normalized.strip()} "


def _marker_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)
