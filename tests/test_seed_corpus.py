"""Tests for the auto-seed demo corpus logic in phoenix_reflex/main.py."""

from __future__ import annotations

import sys
import types as py_types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _install_dependency_stubs() -> None:
    """Install minimal stubs for heavy dependencies not needed in unit tests."""
    if "dotenv" not in sys.modules:
        dotenv_module = py_types.ModuleType("dotenv")
        dotenv_module.load_dotenv = lambda: None
        sys.modules["dotenv"] = dotenv_module

    if "google" not in sys.modules:
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
            def __init__(self, role: str, parts: list):
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

    for mod_name in [
        "google.adk",
        "google.adk.agents",
        "google.adk.runners",
        "google.adk.sessions",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = py_types.ModuleType(mod_name)

    adk_agents = sys.modules["google.adk.agents"]
    if not hasattr(adk_agents, "Agent"):
        adk_agents.Agent = lambda **kwargs: SimpleNamespace(**kwargs)

    adk_runners = sys.modules["google.adk.runners"]
    if not hasattr(adk_runners, "Runner"):
        adk_runners.Runner = lambda **kwargs: SimpleNamespace(**kwargs)

    adk_sessions = sys.modules["google.adk.sessions"]
    if not hasattr(adk_sessions, "InMemorySessionService"):
        adk_sessions.InMemorySessionService = object

    if "opentelemetry" not in sys.modules:
        otel_module = py_types.ModuleType("opentelemetry")
        trace_module = py_types.ModuleType("opentelemetry.trace")
        trace_module.get_tracer = lambda name: SimpleNamespace()
        otel_module.trace = trace_module
        sys.modules["opentelemetry"] = otel_module
        sys.modules["opentelemetry.trace"] = trace_module


_install_dependency_stubs()

from phoenix_reflex.main import _seed_demo_corpus, _DEMO_PDFS  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_page(page_num: int = 1, text: str = "Hello world\n\nSecond paragraph."):
    """Return a minimal object mimicking ExtractedPage."""
    return SimpleNamespace(page=page_num, text=text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seed_skips_when_documents_exist(tmp_path: Path) -> None:
    """_seed_demo_corpus must do nothing if there is already at least one document."""
    existing_doc = {"id": "pdf-abc123", "filename": "existing.pdf"}

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[existing_doc]) as mock_list,
        patch("phoenix_reflex.main.save_document_with_chunks") as mock_save,
    ):
        _seed_demo_corpus()

    mock_list.assert_called_once()
    mock_save.assert_not_called()


def test_seed_skips_missing_pdf(tmp_path: Path, monkeypatch) -> None:
    """_seed_demo_corpus logs 'not found' and skips PDFs that do not exist on disk."""
    monkeypatch.chdir(tmp_path)  # cwd has no PDFs

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[]),
        patch("phoenix_reflex.main.save_document_with_chunks") as mock_save,
        patch("builtins.print") as mock_print,
    ):
        _seed_demo_corpus()

    mock_save.assert_not_called()
    printed = " ".join(str(c) for c in mock_print.call_args_list)
    assert "not found" in printed


def test_seed_ingests_pdf_when_present(tmp_path: Path, monkeypatch) -> None:
    """_seed_demo_corpus ingests a PDF file and logs chunk count."""
    # Create a fake PDF file for the first demo PDF
    pdf_name = _DEMO_PDFS[0]
    fake_pdf = tmp_path / pdf_name
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    monkeypatch.chdir(tmp_path)

    fake_page = _make_fake_page()

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[]),
        patch("phoenix_reflex.main.extract_pdf_pages", return_value=[fake_page]),
        patch("phoenix_reflex.main.save_document_with_chunks") as mock_save,
        patch("builtins.print") as mock_print,
    ):
        _seed_demo_corpus()

    mock_save.assert_called_once()
    printed = " ".join(str(c) for c in mock_print.call_args_list)
    assert "ingested" in printed
    assert pdf_name in printed
    assert "chunks" in printed


def test_seed_document_id_uses_sha256_prefix(tmp_path: Path, monkeypatch) -> None:
    """document_id must follow the pattern pdf-<first 12 hex chars of sha256>."""
    import hashlib

    pdf_name = _DEMO_PDFS[0]
    pdf_content = b"%PDF-1.4 deterministic"
    fake_pdf = tmp_path / pdf_name
    fake_pdf.write_bytes(pdf_content)
    monkeypatch.chdir(tmp_path)

    expected_digest = hashlib.sha256(pdf_content).hexdigest()[:12]
    expected_id = f"pdf-{expected_digest}"

    fake_page = _make_fake_page()
    captured: list[dict] = []

    def capture_save(document: dict, chunk_records: list, tmp_path_arg: Path) -> dict:
        captured.append(document)
        return document

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[]),
        patch("phoenix_reflex.main.extract_pdf_pages", return_value=[fake_page]),
        patch("phoenix_reflex.main.save_document_with_chunks", side_effect=capture_save),
    ):
        _seed_demo_corpus()

    assert len(captured) == 1
    assert captured[0]["id"] == expected_id


def test_seed_continues_after_exception(tmp_path: Path, monkeypatch) -> None:
    """An exception during one PDF must not prevent processing of subsequent PDFs."""
    # Create both demo PDFs
    for pdf_name in _DEMO_PDFS:
        (tmp_path / pdf_name).write_bytes(b"%PDF-1.4 content")
    monkeypatch.chdir(tmp_path)

    call_count = 0

    def failing_extract(path: Path):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated extraction failure")
        return [_make_fake_page()]

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[]),
        patch("phoenix_reflex.main.extract_pdf_pages", side_effect=failing_extract),
        patch("phoenix_reflex.main.save_document_with_chunks") as mock_save,
        patch("builtins.print"),
    ):
        _seed_demo_corpus()

    # First PDF fails, second succeeds → save called exactly once
    assert mock_save.call_count == 1


def test_seed_chunk_records_have_seed_tag(tmp_path: Path, monkeypatch) -> None:
    """Chunks produced by the seed function must carry the 'seed' tag."""
    pdf_name = _DEMO_PDFS[0]
    (tmp_path / pdf_name).write_bytes(b"%PDF-1.4 content")
    monkeypatch.chdir(tmp_path)

    fake_page = _make_fake_page()
    captured_chunks: list[list] = []

    def capture_save(document: dict, chunk_records: list, tmp_path_arg: Path) -> dict:
        captured_chunks.append(chunk_records)
        return document

    with (
        patch("phoenix_reflex.main.list_documents", return_value=[]),
        patch("phoenix_reflex.main.extract_pdf_pages", return_value=[fake_page]),
        patch("phoenix_reflex.main.save_document_with_chunks", side_effect=capture_save),
    ):
        _seed_demo_corpus()

    assert captured_chunks, "save_document_with_chunks was not called"
    for chunk in captured_chunks[0]:
        assert "seed" in chunk["tags"]
