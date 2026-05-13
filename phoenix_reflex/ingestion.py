from __future__ import annotations

import hashlib
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from phoenix_reflex.chunking import chunk_pages
from phoenix_reflex.document_store import save_document_with_chunks
from phoenix_reflex.pdf_loader import extract_pdf_pages


async def ingest_pdf(upload: UploadFile) -> dict[str, Any]:
    filename = Path(upload.filename or "uploaded.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    data = await upload.read()
    if not data:
        raise ValueError("Uploaded PDF is empty.")

    digest = hashlib.sha256(data).hexdigest()[:12]
    document_id = f"pdf-{digest}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(data)
        temp_path = Path(temp.name)

    try:
        pages = extract_pdf_pages(temp_path)
        chunks = chunk_pages([(page.page, page.text) for page in pages])
        if not chunks:
            raise ValueError("PDF text was extracted but produced no chunks.")

        now = datetime.now(UTC).isoformat()
        document = {
            "id": document_id,
            "filename": filename,
            "source_type": "pdf",
            "status": "indexed",
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "sha256": hashlib.sha256(data).hexdigest(),
            "created_at": now,
            "updated_at": now,
        }
        chunk_records = [
            {
                "id": _chunk_id(document_id, filename, chunk.page, chunk.chunk_index),
                "document_id": document_id,
                "source": filename,
                "source_type": "pdf",
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "title": f"pdf:{filename} p.{chunk.page} c.{chunk.chunk_index}",
                "text": chunk.text,
                "token_estimate": max(1, len(chunk.text) // 4),
                "enabled": True,
                "tags": ["pdf", "uploaded"],
                "created_at": now,
                "updated_at": now,
            }
            for chunk in chunks
        ]
        saved = save_document_with_chunks(document, chunk_records, temp_path)
        return {
            "document": saved,
            "chunk_count": len(chunk_records),
            "status": "indexed",
        }
    finally:
        temp_path.unlink(missing_ok=True)


def _chunk_id(document_id: str, filename: str, page: int, chunk_index: int) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip("-")
    return f"{document_id}-p{page:03d}-c{chunk_index:03d}-{safe_name}"
