from __future__ import annotations

import asyncio
import importlib
import sys
import types as py_types
from pathlib import Path
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

from phoenix_reflex import mcp  # noqa: E402
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
    def __init__(self):
        self.messages: list[object] = []

    async def run_async(self, **kwargs):
        self.messages.append(kwargs["new_message"])
        yield FakeFinalEvent("Trace answer from first turn.")


class FakeSessionService:
    def __init__(self):
        self.session = SimpleNamespace(events=[])

    async def create_session(self, **kwargs) -> None:
        return None

    async def get_session(self, **kwargs) -> object:
        return self.session


def _mcp_response_event(name: str = "phoenix_list-traces") -> object:
    function_response = SimpleNamespace(
        name=name,
        response={"traces": [{"trace_id": "trace-1"}]},
    )
    part = SimpleNamespace(function_response=function_response)
    content = SimpleNamespace(parts=[part])
    return SimpleNamespace(content=content)


def test_introspection_message_requests_mcp_on_first_turn() -> None:
    message = mcp.build_observability_agent_message("Que fallo en las trazas?", "local traces")

    assert "If Phoenix MCP tools are available, use them in this first turn" in message
    assert "phoenix_list-traces" in message
    assert "[Local Reflex Context - use if Phoenix MCP is unavailable]" in message
    assert "[Question]\nQue fallo en las trazas?" in message


def test_ask_reports_mcp_call_from_first_turn(monkeypatch) -> None:
    fake_runner = FakeRunner()
    fake_session_service = FakeSessionService()
    fake_session_service.session.events.append(_mcp_response_event())

    monkeypatch.setattr(qa, "_runner", lambda: fake_runner)
    monkeypatch.setattr(qa, "_session_service", lambda: fake_session_service)
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(
        qa,
        "format_reflex_context",
        lambda: ("local trace summary", ["runtime-traces"]),
    )
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

    sent_text = fake_runner.messages[0].parts[0].text
    assert result["phoenix_mcp_called"] is True
    assert result["phoenix_mcp_call_count"] == 1
    assert result["phoenix_mcp_tools"] == ["phoenix_list-traces"]
    assert len(fake_runner.messages) == 1
    assert "use them in this first turn" in sent_text


def test_no_forced_mcp_second_turn_exists() -> None:
    qa_source = Path(qa.__file__).read_text(encoding="utf-8")

    assert not hasattr(qa, "_force_phoenix_mcp_introspection")
    assert "forced_answer" not in qa_source


def test_introspection_falls_back_to_local_reflex_context_without_mcp(monkeypatch) -> None:
    fake_runner = FakeRunner()
    fake_session_service = FakeSessionService()

    monkeypatch.setattr(qa, "_runner", lambda: fake_runner)
    monkeypatch.setattr(qa, "_session_service", lambda: fake_session_service)
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(qa, "format_reflex_context", lambda: ("local fallback", ["runtime-traces"]))
    monkeypatch.setattr(
        qa,
        "evaluate_document_relevance",
        lambda *args, **kwargs: {"label": "relevant", "score": 1.0, "explanation": "local"},
    )
    monkeypatch.setattr(
        qa,
        "evaluate_faithfulness",
        lambda *args, **kwargs: {"label": "faithful", "score": 1.0, "explanation": "local"},
    )
    monkeypatch.setattr(qa, "maybe_create_improvement_case", lambda summary: None)

    result = asyncio.run(qa.ask_agent("Resume los casos de mejora recientes"))

    sent_text = fake_runner.messages[0].parts[0].text
    assert result["phoenix_mcp_called"] is False
    assert result["phoenix_mcp_call_count"] == 0
    assert "local fallback" in sent_text
    assert result["retrieved_documents"] == []


def test_optional_tools_disabled_when_env_false(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PHOENIX_MCP", "0")

    importlib.reload(mcp)

    assert mcp.optional_phoenix_mcp_tools() == []
