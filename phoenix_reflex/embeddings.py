from __future__ import annotations

import json
import math
import os
from pathlib import Path
from threading import Lock
from typing import Any

from google import genai
from google.genai import types

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-2")
EMBEDDINGS_PATH = Path("data/embeddings.json")
_LOCK = Lock()
_store: dict[str, list[float]] = {}
_store_loaded = False


_client_instance: genai.Client | None = None


def _client() -> genai.Client:
    global _client_instance
    if _client_instance is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        _client_instance = genai.Client(api_key=api_key)
    return _client_instance


def _load() -> None:
    global _store, _store_loaded
    if _store_loaded:
        return
    if EMBEDDINGS_PATH.exists():
        try:
            _store = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            _store = {}
    _store_loaded = True


def _save() -> None:
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_PATH.write_text(
        json.dumps(_store, ensure_ascii=False),
        encoding="utf-8",
    )


def embed_query(text: str) -> list[float]:
    result = _client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return list(result.embeddings[0].values)


def get_chunk_embedding(chunk_id: str, text: str) -> list[float]:
    with _LOCK:
        _load()
        if chunk_id in _store:
            return _store[chunk_id]

    emb = _embed_document(text)

    with _LOCK:
        _store[chunk_id] = emb
        _save()
    return emb


def ensure_embeddings(chunks: list[dict[str, Any]], verbose: bool = False) -> None:
    """Pre-compute and persist embeddings for all chunks missing one."""
    with _LOCK:
        _load()
        missing = [c for c in chunks if c["id"] not in _store]

    if not missing:
        return

    for i, chunk in enumerate(missing):
        if verbose:
            print(f"  [{i + 1}/{len(missing)}] {chunk['id']}", flush=True)
        emb = _embed_document(chunk["text"])
        with _LOCK:
            _store[chunk["id"]] = emb
            if (i + 1) % 50 == 0 or i + 1 == len(missing):
                _save()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_document(text: str) -> list[float]:
    result = _client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return list(result.embeddings[0].values)
