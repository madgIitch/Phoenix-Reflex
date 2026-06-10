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
from phoenix_reflex import reflex  # noqa: E402


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
        yield FakeFinalEvent("Trace answer from first turn.")


class FakeSessionService:
    async def create_session(self, **kwargs) -> None:
        return None

    async def get_session(self, **kwargs) -> object:
        return SimpleNamespace(events=[])


async def _failed_mcp_calls(session_id: str) -> list[dict[str, object]]:
    return _mcp_evidence("none")


async def _empty_mcp_calls(session_id: str) -> list[dict[str, object]]:
    return []


def _mcp_evidence(failure_mode: str = "retrieval") -> list[dict[str, object]]:
    return [
        {
            "tool": "phoenix_get-spans",
            "response": {
                "spans": [
                    {
                        "trace_id": "trace-123",
                        "failure_mode": failure_mode,
                        "question": "Why did retrieval miss the answer?",
                        "answer": "Unsupported answer.",
                        "explanation": "Retriever returned irrelevant context.",
                    },
                ],
            },
        },
    ]


def test_mcp_failure_evidence_creates_action(monkeypatch) -> None:
    case = {"case_id": "case-1", "dataset": "regression_v1"}

    monkeypatch.setattr(reflex, "list_improvement_cases", lambda limit=50: {"cases": []})
    monkeypatch.setattr(reflex, "add_mcp_improvement_case", lambda **kwargs: case)

    action = reflex.build_mcp_action(
        question="What failed?",
        phoenix_mcp_evidence=_mcp_evidence(),
    )

    assert action["status"] == "created"
    assert action["source_trace_id"] == "trace-123"
    assert action["failure_mode"] == "retrieval"
    assert action["improvement_case"] == case


def test_mcp_action_checks_existing_cases_before_create(monkeypatch) -> None:
    existing_case = {
        "case_id": "case-existing",
        "source_session_id": "trace-123",
        "question": "Why did retrieval miss the answer?",
        "failure_mode": "retrieval",
    }
    calls = {"list": 0, "add": 0}

    def fake_list_improvement_cases(limit: int = 50) -> dict[str, object]:
        calls["list"] += 1
        return {"cases": [existing_case]}

    def fake_add_mcp_improvement_case(**kwargs) -> dict[str, object]:
        calls["add"] += 1
        return {"case_id": "case-new"}

    monkeypatch.setattr(reflex, "list_improvement_cases", fake_list_improvement_cases)
    monkeypatch.setattr(reflex, "add_mcp_improvement_case", fake_add_mcp_improvement_case)

    action = reflex.build_mcp_action(
        question="What failed?",
        phoenix_mcp_evidence=_mcp_evidence(),
    )

    assert action["status"] == "duplicate"
    assert action["improvement_case"] == existing_case
    assert calls == {"list": 1, "add": 0}


def test_mcp_failure_evidence_creates_improvement_case(monkeypatch) -> None:
    monkeypatch.setattr(reflex, "get_tracer", lambda: FakeTracer())
    reflex.IMPROVEMENT_CASES.clear()

    case = reflex.add_mcp_improvement_case(
        question="What failed?",
        candidate=reflex.extract_mcp_failure_candidate(_mcp_evidence()),
    )

    assert case["source_session_id"] == "trace-123"
    assert case["failure_mode"] == "retrieval"
    assert case["question"] == "Why did retrieval miss the answer?"
    assert case["failure_report"] == "Retriever returned irrelevant context."


def test_ask_returns_mcp_action_payload(monkeypatch) -> None:
    action = {
        "status": "no_action",
        "description": "No failed traces.",
        "source_trace_id": None,
        "failure_mode": None,
        "improvement_case": None,
    }

    monkeypatch.setattr(qa, "_runner", lambda: FakeRunner())
    monkeypatch.setattr(qa, "_session_service", lambda: FakeSessionService())
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(qa, "format_reflex_context", lambda: ("local traces", ["runtime-traces"]))
    monkeypatch.setattr(qa, "_extract_phoenix_mcp_calls", _failed_mcp_calls)
    monkeypatch.setattr(qa, "build_mcp_action", lambda **kwargs: action)
    monkeypatch.setattr(
        qa,
        "evaluate_document_relevance",
        lambda *args, **kwargs: {"label": "relevant", "score": 1.0, "explanation": "ok"},
    )
    monkeypatch.setattr(
        qa,
        "evaluate_faithfulness",
        lambda *args, **kwargs: {"label": "faithful", "score": 1.0, "explanation": "ok"},
    )
    monkeypatch.setattr(qa, "maybe_create_improvement_case", lambda summary: None)

    result = asyncio.run(qa.ask_agent("Que fallo muestran las trazas?"))

    assert result["mcp_action"] == action


def test_mcp_action_no_action_without_failed_trace(monkeypatch) -> None:
    monkeypatch.setattr(reflex, "list_improvement_cases", lambda limit=50: {"cases": []})
    monkeypatch.setattr(
        reflex,
        "add_mcp_improvement_case",
        lambda **kwargs: {"case_id": "unexpected"},
    )

    action = reflex.build_mcp_action(
        question="What failed?",
        phoenix_mcp_evidence=_mcp_evidence("none"),
    )

    assert action["status"] == "no_action"
    assert action["source_trace_id"] is None
    assert action["improvement_case"] is None


def test_ask_keeps_local_fallback_without_mcp_action(monkeypatch) -> None:
    monkeypatch.setattr(qa, "_runner", lambda: FakeRunner())
    monkeypatch.setattr(qa, "_session_service", lambda: FakeSessionService())
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(qa, "format_reflex_context", lambda: ("local traces", ["runtime-traces"]))
    monkeypatch.setattr(qa, "_extract_phoenix_mcp_calls", _empty_mcp_calls)
    monkeypatch.setattr(
        qa,
        "evaluate_document_relevance",
        lambda *args, **kwargs: {"label": "relevant", "score": 1.0, "explanation": "ok"},
    )
    monkeypatch.setattr(
        qa,
        "evaluate_faithfulness",
        lambda *args, **kwargs: {"label": "faithful", "score": 1.0, "explanation": "ok"},
    )
    monkeypatch.setattr(qa, "maybe_create_improvement_case", lambda summary: None)

    result = asyncio.run(qa.ask_agent("Que fallo muestran las trazas?"))

    assert result["mcp_action"] is None
