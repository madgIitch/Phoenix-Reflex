from __future__ import annotations

from types import SimpleNamespace

from phoenix_reflex import retriever


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


def test_retrieve_documents_falls_back_to_bm25_when_semantic_errors(monkeypatch) -> None:
    chunks = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "source": "demo.pdf",
            "source_type": "pdf",
            "title": "Estatuto de los Trabajadores",
            "page": 1,
            "chunk_index": 1,
            "text": "El Estatuto de los Trabajadores regula derechos laborales y jornada.",
            "tags": [],
            "enabled": True,
        }
    ]

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(retriever, "get_tracer", lambda: FakeTracer())
    monkeypatch.setattr(retriever, "list_chunks", lambda enabled_only=True: chunks)
    monkeypatch.setattr(
        retriever,
        "_semantic_rank",
        lambda query, top_k: (_ for _ in ()).throw(RuntimeError("429 RESOURCE_EXHAUSTED")),
    )

    result = retriever.retrieve_documents("derechos laborales", top_k=4)

    assert result["retrieval_method"] == "bm25_fallback"
    assert result["documents"][0]["chunk_id"] == "chunk-1"
    assert "429 RESOURCE_EXHAUSTED" in result["semantic_error"]
