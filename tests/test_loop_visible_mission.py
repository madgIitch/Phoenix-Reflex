from __future__ import annotations

import asyncio
import sys
import types as py_types
from types import SimpleNamespace


def _install_dependency_stubs() -> None:
    dotenv_module = py_types.ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv_module

    google_module = py_types.ModuleType("google")
    genai_module = py_types.ModuleType("google.genai")
    genai_types_module = py_types.ModuleType("google.genai.types")

    class FakePart:
        def __init__(self, text: str | None = None):
            self.text = text
            self.function_response = None

        @staticmethod
        def from_text(text: str) -> "FakePart":
            return FakePart(text=text)

    class FakeContent:
        def __init__(self, role: str, parts: list[FakePart]):
            self.role = role
            self.parts = parts

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    genai_types_module.Part = FakePart
    genai_types_module.Content = FakeContent
    genai_types_module.GenerateContentConfig = FakeGenerateContentConfig
    genai_module.types = genai_types_module
    genai_module.Client = object
    google_module.genai = genai_module
    sys.modules["google"] = google_module
    sys.modules["google.genai"] = genai_module
    sys.modules["google.genai.types"] = genai_types_module

    adk_module = py_types.ModuleType("google.adk")
    adk_agents_module = py_types.ModuleType("google.adk.agents")
    adk_runners_module = py_types.ModuleType("google.adk.runners")
    adk_sessions_module = py_types.ModuleType("google.adk.sessions")
    adk_agents_module.Agent = lambda **kwargs: SimpleNamespace(**kwargs)
    adk_runners_module.Runner = lambda **kwargs: SimpleNamespace(**kwargs)
    adk_sessions_module.InMemorySessionService = object
    sys.modules["google.adk"] = adk_module
    sys.modules["google.adk.agents"] = adk_agents_module
    sys.modules["google.adk.runners"] = adk_runners_module
    sys.modules["google.adk.sessions"] = adk_sessions_module

    otel_module = py_types.ModuleType("opentelemetry")
    trace_module = py_types.ModuleType("opentelemetry.trace")
    trace_module.get_tracer = lambda name: SimpleNamespace()
    otel_module.trace = trace_module
    sys.modules["opentelemetry"] = otel_module
    sys.modules["opentelemetry.trace"] = trace_module


_install_dependency_stubs()

from phoenix_reflex import qa  # noqa: E402


class FakeSpan:
    def __enter__(self) -> "FakeSpan":
        return self

    def __exit__(self, *args) -> None:
        return None

    def set_attribute(self, key: str, value: object) -> None:
        return None


class FakeTracer:
    def start_as_current_span(self, name: str) -> FakeSpan:
        return FakeSpan()


class FakeFinalEvent:
    author = "qa_agent"

    def __init__(self, text: str):
        self.content = qa.types.Content(
            role="model",
            parts=[qa.types.Part.from_text(text=text)],
        )

    def is_final_response(self) -> bool:
        return True


class FakeRunner:
    async def run_async(self, **kwargs):
        yield FakeFinalEvent("Unsupported answer without citations.")


class FakeSessionService:
    async def create_session(self, **kwargs) -> None:
        return None

    async def get_session(self, **kwargs) -> object:
        return SimpleNamespace(events=[])


def _faithfulness(score: float = 0.4) -> dict[str, object]:
    return {
        "label": "unfaithful" if score < 0.75 else "faithful",
        "score": score,
        "explanation": "unsupported claim",
        "context_doc_ids": [],
    }


def _relevance(score: float = 0.95) -> dict[str, object]:
    return {
        "label": "relevant",
        "score": score,
        "explanation": "documents are relevant",
        "context_doc_ids": [],
    }


def test_ask_returns_improvement_case_when_faithfulness_low(monkeypatch) -> None:
    improvement_case = {
        "case_id": "case-demo",
        "dataset": "regression_v1",
        "question": "legal question",
        "bad_answer": "Unsupported answer without citations.",
        "faithfulness_label": "unfaithful",
        "faithfulness_score": 0.4,
        "failure_mode": "generation",
        "failure_report": "unsupported claim",
        "suggested_fix": "Abstain when unsupported.",
    }

    monkeypatch.setattr(qa, "_runner", lambda: FakeRunner())
    monkeypatch.setattr(qa, "_session_service", lambda: FakeSessionService())
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(qa, "retrieve_documents", lambda *args, **kwargs: {"documents": [], "valid_citation_ids": []})
    monkeypatch.setattr(qa, "evaluate_document_relevance", lambda *args, **kwargs: _relevance())
    monkeypatch.setattr(qa, "evaluate_faithfulness", lambda *args, **kwargs: _faithfulness())
    monkeypatch.setattr(qa, "maybe_create_improvement_case", lambda summary: improvement_case)
    monkeypatch.setattr(qa, "record_trace_summary", lambda **kwargs: kwargs)

    result = asyncio.run(qa.ask_agent("legal question"))

    assert result["improvement_case"] == improvement_case
    assert result["loop"]["improvement_case"] == improvement_case


def test_loop_summary_includes_correction_step() -> None:
    loop = qa._build_loop_summary(
        correction_rounds=1,
        phantom_citations_detected_count=2,
        phantom_citations_corrected_count=2,
        style_correction_applied=True,
        faithfulness=_faithfulness(),
        document_relevance=_relevance(),
        answer_quality={"label": "ok", "reasons": [], "explanation": "ok"},
        failure_mode="generation",
        improvement_case=None,
    )

    assert loop["steps"] == ["correction", "eval", "improvement_case"]
    assert loop["correction"]["attempted"] is True
    assert loop["correction"]["rounds"] == 1
    assert loop["correction"]["phantom_citations_detected_count"] == 2
    assert loop["correction"]["phantom_citations_corrected_count"] == 2
    assert loop["correction"]["style_correction_applied"] is True


def test_loop_summary_includes_eval_step() -> None:
    faithfulness = _faithfulness()
    relevance = _relevance()
    answer_quality = {"label": "suspicious", "reasons": ["language_mismatch"], "explanation": "mismatch"}

    loop = qa._build_loop_summary(
        correction_rounds=0,
        phantom_citations_detected_count=0,
        phantom_citations_corrected_count=0,
        style_correction_applied=False,
        faithfulness=faithfulness,
        document_relevance=relevance,
        answer_quality=answer_quality,
        failure_mode="answer_quality",
        improvement_case=None,
    )

    assert loop["eval"]["faithfulness"] == faithfulness
    assert loop["eval"]["document_relevance"] == relevance
    assert loop["eval"]["answer_quality"] == answer_quality
    assert loop["eval"]["failure_mode"] == "answer_quality"


def test_loop_summary_includes_improvement_case_step() -> None:
    improvement_case = {"case_id": "case-demo", "dataset": "regression_v1"}

    loop = qa._build_loop_summary(
        correction_rounds=0,
        phantom_citations_detected_count=0,
        phantom_citations_corrected_count=0,
        style_correction_applied=False,
        faithfulness=_faithfulness(),
        document_relevance=_relevance(),
        answer_quality={"label": "ok", "reasons": [], "explanation": "ok"},
        failure_mode="generation",
        improvement_case=improvement_case,
    )

    assert loop["improvement_case"] == improvement_case
