from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedPage:
    page: int
    raw_text: str
    text: str


def extract_pdf_pages(path: Path) -> list[ExtractedPage]:
    reader = PdfReader(str(path))
    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        text = normalize_text(raw_text)
        if text:
            pages.append(ExtractedPage(page=index, raw_text=raw_text, text=text))
    if not pages:
        raise ValueError("PDF has no extractable text. OCR is not supported in v1.")
    return pages


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()
