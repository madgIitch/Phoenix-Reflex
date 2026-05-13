from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    page: int
    chunk_index: int
    text: str


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page, text in pages:
        page_chunks = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for index, chunk in enumerate(page_chunks, start=1):
            chunks.append(TextChunk(page=page, chunk_index=index, text=chunk))
    return chunks


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_hard_chunks(paragraph, chunk_size=chunk_size, overlap=overlap))
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            current = _with_overlap(current, paragraph, overlap)

    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def _hard_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _with_overlap(previous: str, paragraph: str, overlap: int) -> str:
    suffix = previous[-overlap:].strip()
    return f"{suffix}\n\n{paragraph}".strip() if suffix else paragraph
