from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from phoenix_reflex.observability import get_tracer

TRACE_SUMMARIES: deque[dict[str, Any]] = deque(maxlen=50)
IMPROVEMENT_CASES: deque[dict[str, Any]] = deque(maxlen=50)
LOCK = Lock()


def record_trace_summary(
    *,
    question: str,
    answer: str,
    faithfulness: dict[str, Any],
    session_id: str,
    event_count: int,
) -> dict[str, Any]:
    """Store a compact runtime summary for agent self-introspection."""
    summary = {
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "question": question,
        "answer": answer,
        "faithfulness": faithfulness,
        "event_count": event_count,
    }
    with LOCK:
        TRACE_SUMMARIES.appendleft(summary)
    return summary


def maybe_create_improvement_case(summary: dict[str, Any]) -> dict[str, Any] | None:
    faithfulness = summary["faithfulness"]
    if float(faithfulness.get("score", 0.0)) >= 0.75:
        return None

    return add_improvement_case(
        question=summary["question"],
        answer=summary["answer"],
        faithfulness_label=str(faithfulness.get("label", "unknown")),
        faithfulness_score=float(faithfulness.get("score", 0.0)),
        explanation=str(faithfulness.get("explanation", "")),
        source_session_id=summary["session_id"],
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


def add_improvement_case(
    question: str,
    answer: str,
    faithfulness_label: str,
    faithfulness_score: float,
    explanation: str,
    source_session_id: str,
) -> dict[str, Any]:
    """Add a regression case candidate for future evaluation datasets."""
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
            "failure_report": explanation,
            "suggested_fix": (
                "Improve retrieval coverage or tighten the prompt so unsupported "
                "claims become explicit abstentions."
            ),
        }
        with LOCK:
            IMPROVEMENT_CASES.appendleft(case)

        span.set_attribute("improvement.dataset", case["dataset"])
        span.set_attribute("improvement.case_id", case["case_id"])
        span.set_attribute("improvement.source_session_id", source_session_id)
        span.set_attribute("eval.faithfulness.label", faithfulness_label)
        span.set_attribute("eval.faithfulness.score", faithfulness_score)
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
                    f"question={trace['question']!r}"
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
                    f"question={case['question']!r} "
                    f"bad_answer={case['bad_answer']!r} "
                    f"label={case['faithfulness_label']} "
                    f"score={case['faithfulness_score']} "
                    f"report={case['failure_report']!r} "
                    f"suggested_fix={case['suggested_fix']!r}"
                )
                for case in cases
            )
        )
    else:
        sections.append("[regression_v1]\nNo improvement cases.")

    return "\n\n".join(sections), context_ids
