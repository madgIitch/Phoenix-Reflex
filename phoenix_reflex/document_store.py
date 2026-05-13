from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"
LOCK = Lock()


def ensure_store() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not DOCUMENTS_PATH.exists():
        _write_json(DOCUMENTS_PATH, [])
    if not CHUNKS_PATH.exists():
        _write_json(CHUNKS_PATH, [])


def list_documents() -> list[dict[str, Any]]:
    ensure_store()
    with LOCK:
        return list(_read_json(DOCUMENTS_PATH))


def get_document(document_id: str) -> dict[str, Any] | None:
    for document in list_documents():
        if document["id"] == document_id:
            return document
    return None


def list_chunks(document_id: str | None = None, enabled_only: bool = False) -> list[dict[str, Any]]:
    ensure_store()
    with LOCK:
        chunks = list(_read_json(CHUNKS_PATH))
    if document_id:
        chunks = [chunk for chunk in chunks if chunk["document_id"] == document_id]
    if enabled_only:
        chunks = [chunk for chunk in chunks if chunk.get("enabled", True)]
    return chunks


def save_document_with_chunks(
    document: dict[str, Any],
    chunks: list[dict[str, Any]],
    source_path: Path,
) -> dict[str, Any]:
    ensure_store()
    upload_path = UPLOAD_DIR / f"{document['id']}.pdf"
    shutil.copyfile(source_path, upload_path)
    document["stored_path"] = str(upload_path)
    document["updated_at"] = datetime.now(UTC).isoformat()

    with LOCK:
        documents = [item for item in _read_json(DOCUMENTS_PATH) if item["id"] != document["id"]]
        existing_chunks = [item for item in _read_json(CHUNKS_PATH) if item["document_id"] != document["id"]]
        documents.append(document)
        existing_chunks.extend(chunks)
        _write_json(DOCUMENTS_PATH, documents)
        _write_json(CHUNKS_PATH, existing_chunks)
    return document


def update_chunk_enabled(chunk_id: str, enabled: bool) -> dict[str, Any] | None:
    ensure_store()
    with LOCK:
        chunks = _read_json(CHUNKS_PATH)
        updated = None
        for chunk in chunks:
            if chunk["id"] == chunk_id:
                chunk["enabled"] = enabled
                chunk["updated_at"] = datetime.now(UTC).isoformat()
                updated = chunk
                break
        if updated is None:
            return None
        _write_json(CHUNKS_PATH, chunks)
        return updated


def delete_document(document_id: str) -> bool:
    ensure_store()
    with LOCK:
        documents = _read_json(DOCUMENTS_PATH)
        target = next((item for item in documents if item["id"] == document_id), None)
        if target is None:
            return False
        documents = [item for item in documents if item["id"] != document_id]
        chunks = [item for item in _read_json(CHUNKS_PATH) if item["document_id"] != document_id]
        _write_json(DOCUMENTS_PATH, documents)
        _write_json(CHUNKS_PATH, chunks)
    stored_path = target.get("stored_path")
    if stored_path:
        Path(stored_path).unlink(missing_ok=True)
    return True


def _read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8") or "[]")


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
