"""Pre-compute and cache embeddings for all indexed chunks.

Run once before starting the server so the first query is not slow:
    python scripts/precompute_embeddings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from phoenix_reflex.embeddings import EMBEDDING_MODEL, EMBEDDINGS_PATH, ensure_embeddings, _load
from phoenix_reflex.retriever import _searchable_documents

_load()

docs = _searchable_documents()
print(f"Documents to embed: {len(docs)}  |  model: {EMBEDDING_MODEL}")
print(f"Cache path: {EMBEDDINGS_PATH}")

ensure_embeddings(docs, verbose=True)

from phoenix_reflex.embeddings import _store
print(f"\nDone. {len(_store)} embeddings cached.")
