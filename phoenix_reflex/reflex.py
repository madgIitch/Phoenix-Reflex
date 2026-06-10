from __future__ import annotations

import re
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from phoenix_reflex.observability import get_tracer

TRACE_SUMMARIES: deque[dict[str, Any]] = deque(maxlen=50)
IMPROVEMENT_CASES: deque[dict[str, Any]] = deque(maxlen=50)
LOCK = Lock()
ACTIONABLE_FAILURE_MODES = {"retrieval", "generation", "answer_quality", "unknown"}

MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€”", "â€“", "�")


def repair_mojibake(value: Any) -> Any:
    """Repair common UTF-8 text that was decoded as Windows-1252/Latin-1."""
    if isinstance(value, str):
        return _repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_mojibake(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_mojibake(item) for key, item in value.items()}
    return value


def _repair_mojibake_text(text: str) -> str:
    repaired = text
    for _ in range(3):
        if not _looks_mojibake(repaired):
            break
        candidate = _decode_mojibake_once(repaired)
        if candidate == repaired or _mojibake_score(candidate) > _mojibake_score(repaired):
            break
        repaired = candidate
    return repaired


def _decode_mojibake_once(text: str) -> str:
    best = text
    best_score = _mojibake_score(text)
    for encoding in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        score = _mojibake_score(candidate)
        if score < best_score:
            best = candidate
            best_score = score
    return best


def _looks_mojibake(text: str) -> bool:
    return any(marker in text for marker in MOJIBAKE_MARKERS)


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def record_trace_summary(
    *,
    question: str,
    answer: str,
    faithfulness: dict[str, Any],
    document_relevance: dict[str, Any] | None = None,
    answer_quality: dict[str, Any] | None = None,
    failure_mode: str = "unknown",
    session_id: str,
    event_count: int,
    retrieved_documents: list[dict[str, Any]] | None = None,
    phantom_citations_detected_count: int = 0,
    phantom_citations_corrected_count: int = 0,
    phantom_citations: list[str] | None = None,
    style_correction_applied: bool = False,
    phoenix_mcp_called: bool = False,
    phoenix_mcp_call_count: int = 0,
    phoenix_mcp_tools: list[str] | None = None,
    phoenix_mcp_evidence: list[dict[str, Any]] | None = None,
    mcp_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a compact runtime summary for agent self-introspection."""
    retrieved_documents = retrieved_documents or []
    question = _repair_mojibake_text(question)
    answer = _repair_mojibake_text(answer)
    faithfulness = repair_mojibake(faithfulness)
    document_relevance = repair_mojibake(document_relevance)
    answer_quality = repair_mojibake(answer_quality)
    retrieved_documents = repair_mojibake(retrieved_documents)
    phoenix_mcp_evidence = repair_mojibake(phoenix_mcp_evidence)
    summary = {
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "question": question,
        "answer": answer,
        "input": {
            "question": question,
        },
        "output": {
            "answer": answer,
            "faithfulness": faithfulness,
            "document_relevance": document_relevance,
            "answer_quality": answer_quality,
            "failure_mode": failure_mode,
        },
        "retrieved_documents": retrieved_documents,
        "faithfulness": faithfulness,
        "document_relevance": document_relevance,
        "answer_quality": answer_quality,
        "failure_mode": failure_mode,
        "event_count": event_count,
        "phantom_citations_detected_count": phantom_citations_detected_count,
        "phantom_citations_corrected_count": phantom_citations_corrected_count,
        "phantom_citations": phantom_citations or [],
        "style_correction_applied": style_correction_applied,
        "phoenix_mcp_called": phoenix_mcp_called,
        "phoenix_mcp_call_count": phoenix_mcp_call_count,
        "phoenix_mcp_tools": phoenix_mcp_tools or [],
        "phoenix_mcp_evidence": phoenix_mcp_evidence or [],
        "mcp_action": mcp_action,
    }
    with LOCK:
        TRACE_SUMMARIES.appendleft(summary)
    return summary


def maybe_create_improvement_case(summary: dict[str, Any]) -> dict[str, Any] | None:
    faithfulness = summary["faithfulness"]
    answer_quality = summary.get("answer_quality") or {}
    faithfulness_score = float(faithfulness.get("score", 0.0))
    is_suspicious = answer_quality.get("label") == "suspicious"
    if faithfulness_score >= 0.75 and not is_suspicious:
        return None
    quality_only_failure = faithfulness_score >= 0.75 and is_suspicious

    return add_improvement_case(
        question=summary["question"],
        answer=summary["answer"],
        faithfulness_label=str(faithfulness.get("label", "unknown")),
        faithfulness_score=faithfulness_score,
        explanation=(
            str(answer_quality.get("explanation", ""))
            if quality_only_failure
            else str(faithfulness.get("explanation", ""))
        ),
        source_session_id=summary["session_id"],
        failure_mode=(
            "answer_quality"
            if quality_only_failure
            else str(summary.get("failure_mode", "unknown"))
        ),
    )


def build_mcp_action(
    *,
    question: str,
    phoenix_mcp_evidence: list[dict[str, object]],
) -> dict[str, object]:
    """Create a concrete action from Phoenix MCP failure evidence."""
    candidate = extract_mcp_failure_candidate(phoenix_mcp_evidence)
    if candidate is None:
        return _mcp_action(
            status="no_action",
            description="Phoenix MCP returned no traces or spans with actionable failure_mode.",
        )

    source_trace_id = str(candidate["source_trace_id"])
    failure_mode = str(candidate["failure_mode"])
    action_question = str(candidate.get("question") or question)
    existing_cases = list_improvement_cases(limit=50)["cases"]
    duplicate = find_duplicate_improvement_case(
        source_session_id=source_trace_id,
        question=action_question,
        failure_mode=failure_mode,
        existing_cases=existing_cases,
    )
    if duplicate:
        return _mcp_action(
            status="duplicate",
            description=(
                f"Existing improvement case {duplicate['case_id']} already covers trace "
                f"{source_trace_id}."
            ),
            source_trace_id=source_trace_id,
            failure_mode=failure_mode,
            improvement_case=duplicate,
        )

    improvement_case = add_mcp_improvement_case(
        question=question,
        candidate=candidate,
    )
    return _mcp_action(
        status="created",
        description=(
            f"Improvement case {improvement_case['case_id']} captured from trace "
            f"{source_trace_id}."
        ),
        source_trace_id=source_trace_id,
        failure_mode=failure_mode,
        improvement_case=improvement_case,
    )


def extract_mcp_failure_candidate(
    phoenix_mcp_evidence: list[dict[str, object]],
) -> dict[str, object] | None:
    """Return the first actionable failure candidate found in Phoenix MCP evidence."""
    for item in _iter_dicts(phoenix_mcp_evidence):
        failure_mode = _failure_mode_from_item(item)
        if failure_mode is None:
            continue
        source_trace_id = _first_string(
            item,
            ("trace_id", "session_id", "source_session_id", "id"),
        )
        if source_trace_id is None:
            source_trace_id = f"mcp-{_stable_signature(str(item), failure_mode)}"
        question = _first_string(item, ("question", "input", "input.value"))
        answer = _first_string(item, ("answer", "output", "output.value", "bad_answer"))
        explanation = _first_string(
            item,
            ("explanation", "failure_report", "error", "message", "summary"),
        )
        return {
            "source_trace_id": source_trace_id,
            "failure_mode": failure_mode,
            "question": question,
            "answer": answer,
            "explanation": explanation or f"Phoenix MCP reported failure_mode={failure_mode}.",
        }
    return None


def find_duplicate_improvement_case(
    *,
    source_session_id: str,
    question: str,
    failure_mode: str,
    existing_cases: list[dict[str, object]],
) -> dict[str, object] | None:
    """Find an existing case for the same source trace or question/failure signature."""
    signature = _stable_signature(question, failure_mode)
    for case in existing_cases:
        if str(case.get("source_session_id", "")) == source_session_id:
            return case
        case_signature = _stable_signature(
            str(case.get("question", "")),
            str(case.get("failure_mode", "")),
        )
        if case_signature == signature:
            return case
    return None


def add_mcp_improvement_case(
    *,
    question: str,
    candidate: dict[str, object],
) -> dict[str, object]:
    """Create an improvement case from normalized Phoenix MCP failure evidence."""
    action_question = str(candidate.get("question") or question)
    failure_mode = str(candidate.get("failure_mode", "unknown"))
    source_trace_id = str(candidate.get("source_trace_id", "mcp-unknown"))
    return add_improvement_case(
        question=action_question,
        answer=str(candidate.get("answer") or "Phoenix MCP trace reported a failed answer."),
        faithfulness_label="mcp_failure",
        faithfulness_score=0.0,
        explanation=str(candidate.get("explanation") or "Phoenix MCP reported a failed trace."),
        source_session_id=source_trace_id,
        failure_mode=failure_mode,
    )


def list_recent_trace_summaries(limit: int = 5) -> dict[str, Any]:
    """List recent qa_agent traces and faithfulness results."""
    limit = max(1, min(limit, 20))
    with LOCK:
        traces = list(TRACE_SUMMARIES)[:limit]
    return {
        "count": len(traces),
        "traces": traces,
    }


def get_trace_summary(session_id: str) -> dict[str, Any]:
    """Return one trace summary by session id."""
    with LOCK:
        for trace in TRACE_SUMMARIES:
            if trace["session_id"] == session_id:
                return {"found": True, "trace": trace}
    return {"found": False, "trace": None}


def export_trace_io(limit: int = 50) -> dict[str, Any]:
    """Export captured trace inputs, outputs, retrieval context, and eval outputs."""
    limit = max(1, min(limit, 50))
    with LOCK:
        traces = list(TRACE_SUMMARIES)[:limit]
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "trace_count": len(traces),
        "traces": traces,
    }


def add_improvement_case(
    question: str,
    answer: str,
    faithfulness_label: str,
    faithfulness_score: float,
    explanation: str,
    source_session_id: str,
    failure_mode: str = "unknown",
) -> dict[str, Any]:
    """Add a regression case candidate for future evaluation datasets."""
    question = _repair_mojibake_text(question)
    answer = _repair_mojibake_text(answer)
    explanation = _repair_mojibake_text(explanation)
    tracer = get_tracer()
    with tracer.start_as_current_span("add_improvement_case") as span:
        case = {
            "case_id": f"case-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            "dataset": "regression_v1",
            "timestamp": datetime.now(UTC).isoformat(),
            "source_session_id": source_session_id,
            "question": question,
            "bad_answer": answer,
            "faithfulness_label": faithfulness_label,
            "faithfulness_score": faithfulness_score,
            "failure_mode": failure_mode,
            "failure_report": explanation,
            "suggested_fix": (
                _suggest_fix(failure_mode)
            ),
        }
        with LOCK:
            IMPROVEMENT_CASES.appendleft(case)

        span.set_attribute("improvement.dataset", case["dataset"])
        span.set_attribute("improvement.case_id", case["case_id"])
        span.set_attribute("improvement.source_session_id", source_session_id)
        span.set_attribute("eval.faithfulness.label", faithfulness_label)
        span.set_attribute("eval.faithfulness.score", faithfulness_score)
        span.set_attribute("eval.failure_mode", failure_mode)
        span.set_attribute("output.value", case["failure_report"])
        return case


def list_improvement_cases(limit: int = 10) -> dict[str, Any]:
    """List generated regression candidates."""
    limit = max(1, min(limit, 50))
    with LOCK:
        cases = list(IMPROVEMENT_CASES)[:limit]
    return {
        "dataset": "regression_v1",
        "count": len(cases),
        "cases": cases,
    }


def format_reflex_context(limit: int = 5) -> tuple[str, list[str]]:
    """Format recent trace and improvement state for faithfulness evaluation."""
    with LOCK:
        traces = list(TRACE_SUMMARIES)[:limit]
        cases = list(IMPROVEMENT_CASES)[:limit]

    sections: list[str] = []
    context_ids: list[str] = []
    if traces:
        context_ids.append("runtime-traces")
        sections.append(
            "[runtime-traces]\n"
            + "\n".join(
                (
                    f"- session_id={trace['session_id']} "
                    f"faithfulness={trace['faithfulness'].get('label')} "
                    f"score={trace['faithfulness'].get('score')} "
                    f"document_relevance={_relevance_label(trace)} "
                    f"failure_mode={trace.get('failure_mode')} "
                    f"question={_repair_mojibake_text(trace['question'])!r}"
                )
                for trace in traces
            )
        )
    else:
        sections.append("[runtime-traces]\nNo recent trace summaries.")

    if cases:
        context_ids.append("regression_v1")
        sections.append(
            "[regression_v1]\n"
            + "\n".join(
                (
                    f"- case_id={case['case_id']} "
                    f"question={_repair_mojibake_text(case['question'])!r} "
                    f"bad_answer={_repair_mojibake_text(case['bad_answer'])!r} "
                    f"label={case['faithfulness_label']} "
                    f"score={case['faithfulness_score']} "
                    f"failure_mode={case.get('failure_mode')} "
                    f"report={_repair_mojibake_text(case['failure_report'])!r} "
                    f"suggested_fix={case['suggested_fix']!r}"
                )
                for case in cases
            )
        )
    else:
        sections.append("[regression_v1]\nNo improvement cases.")

    return "\n\n".join(sections), context_ids


def _suggest_fix(failure_mode: str) -> str:
    if failure_mode == "retrieval":
        return "Improve corpus coverage or retrieval ranking for this question."
    if failure_mode == "generation":
        return "Tighten the prompt so unsupported claims become explicit abstentions."
    if failure_mode == "answer_quality":
        return (
            "Improve answer usefulness checks: preserve the user language, avoid intent drift, "
            "and do not over-abstain when relevant context exists."
        )
    return (
        "Improve retrieval coverage or tighten the prompt so unsupported claims become explicit "
        "abstentions."
    )


def _mcp_action(
    *,
    status: str,
    description: str,
    source_trace_id: str | None = None,
    failure_mode: str | None = None,
    improvement_case: dict[str, Any] | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "description": description,
        "source_trace_id": source_trace_id,
        "failure_mode": failure_mode,
        "improvement_case": improvement_case,
    }


def _iter_dicts(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        children = []
        for child in value.values():
            children.extend(_iter_dicts(child))
        return [value, *children]
    if isinstance(value, list):
        children = []
        for item in value:
            children.extend(_iter_dicts(item))
        return children
    return []


def _failure_mode_from_item(item: dict[str, object]) -> str | None:
    raw_failure_mode = item.get("failure_mode")
    if raw_failure_mode is None:
        attributes = item.get("attributes")
        if isinstance(attributes, dict):
            raw_failure_mode = attributes.get("failure_mode") or attributes.get("eval.failure_mode")
    if raw_failure_mode is None:
        return None

    failure_mode = str(raw_failure_mode).strip().lower()
    if failure_mode == "none":
        return None
    if failure_mode in ACTIONABLE_FAILURE_MODES:
        return failure_mode
    return "unknown"


def _first_string(item: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _lookup_nested(item, key)
        if isinstance(value, str) and value.strip():
            return _repair_mojibake_text(value.strip())
    return None


def _lookup_nested(item: dict[str, object], key: str) -> object:
    if key in item:
        return item[key]
    value: object = item
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _stable_signature(question: str, failure_mode: str) -> str:
    normalized_question = re.sub(r"\s+", " ", question.strip().lower())
    normalized_failure = failure_mode.strip().lower()
    return f"{normalized_failure}:{normalized_question}"


def _relevance_label(trace: dict[str, Any]) -> str:
    relevance = trace.get("document_relevance") or {}
    return str(relevance.get("label", "unknown"))
