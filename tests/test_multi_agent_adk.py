from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from phoenix_reflex import qa
from phoenix_reflex.prompts import PRODUCTION_PROMPT
from phoenix_reflex_agent import agent
from phoenix_reflex_agent import multi_agent


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
    author = "qa_coordinator"

    def __init__(self, text: str):
        self.content = qa.types.Content(
            role="model",
            parts=[qa.types.Part.from_text(text=text)],
        )

    def is_final_response(self) -> bool:
        return True


class FakeRunner:
    async def run_async(self, **kwargs):
        yield FakeFinalEvent("Stable answer.")


class FakeSessionService:
    async def create_session(self, **kwargs) -> None:
        return None

    async def get_session(self, **kwargs) -> object:
        return SimpleNamespace(events=[])


def test_google_adk_requirement_allows_v2() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "google-adk>=2.0.0,<3.0.0" in requirements


def test_build_root_agent_preserves_root_agent_export(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_MULTI_AGENT_ADK", raising=False)
    built_agent = multi_agent.build_root_agent()

    assert built_agent.name == agent.root_agent.name == "qa_agent"
    assert built_agent.instruction == agent.root_agent.instruction == PRODUCTION_PROMPT


def test_multi_agent_builder_defines_judge_subagent(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PHOENIX_MCP", "0")
    root = multi_agent.build_multi_agent()
    judge = next(subagent for subagent in root.sub_agents if subagent.name == "judge_subagent")

    assert "faithfulness" in judge.instruction
    assert "document_relevance" in judge.instruction
    assert "answer_quality" in judge.instruction
    assert "failure_mode" in judge.instruction


def test_multi_agent_builder_defines_improvement_subagent(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PHOENIX_MCP", "0")
    root = multi_agent.build_multi_agent()
    improvement = next(
        subagent for subagent in root.sub_agents if subagent.name == "improvement_subagent"
    )

    assert "improvement cases" in improvement.instruction
    assert "failure_mode" in improvement.instruction


def test_default_mode_uses_single_agent(monkeypatch) -> None:
    sentinel = SimpleNamespace(name="single")

    monkeypatch.delenv("ENABLE_MULTI_AGENT_ADK", raising=False)
    monkeypatch.setattr(multi_agent, "build_single_agent", lambda: sentinel)

    assert multi_agent.build_root_agent() is sentinel


def test_flag_builds_multi_agent_without_prompt_mutation(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_MULTI_AGENT_ADK", "1")
    monkeypatch.setenv("ENABLE_PHOENIX_MCP", "0")
    original_prompt = PRODUCTION_PROMPT

    root = multi_agent.build_root_agent()

    assert root.name == "qa_coordinator"
    assert PRODUCTION_PROMPT == original_prompt
    assert root.instruction == multi_agent.COORDINATOR_INSTRUCTION


def test_multi_agent_build_failure_falls_back_to_single_agent(monkeypatch) -> None:
    sentinel = SimpleNamespace(name="single")

    monkeypatch.setenv("ENABLE_MULTI_AGENT_ADK", "1")
    monkeypatch.setattr(multi_agent, "build_multi_agent", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(multi_agent, "build_single_agent", lambda: sentinel)

    assert multi_agent.build_root_agent() is sentinel


def test_runner_uses_build_root_agent_in_qa(monkeypatch) -> None:
    sentinel_agent = SimpleNamespace(name="selected")
    captured: dict[str, object] = {}

    class CapturingRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    qa._runner.cache_clear()
    monkeypatch.setattr(qa, "build_root_agent", lambda: sentinel_agent)
    monkeypatch.setattr(qa, "Runner", CapturingRunner)

    qa._runner()

    assert captured["agent"] is sentinel_agent


def test_ask_contract_keys_stay_stable_with_multi_agent_flag(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_MULTI_AGENT_ADK", "1")
    monkeypatch.setattr(qa, "_runner", lambda: FakeRunner())
    monkeypatch.setattr(qa, "_session_service", lambda: FakeSessionService())
    monkeypatch.setattr(qa, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(qa, "retrieve_documents", lambda *args, **kwargs: {"documents": [], "valid_citation_ids": []})
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

    result = asyncio.run(qa.ask_agent("legal question"))

    assert {
        "answer",
        "faithfulness",
        "document_relevance",
        "answer_quality",
        "failure_mode",
        "loop",
        "improvement_case",
    }.issubset(result)
