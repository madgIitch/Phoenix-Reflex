from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any

from phoenix_reflex.corpus import CORPUS, Document
from phoenix_reflex.observability import get_tracer

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


@lru_cache(maxsize=1)
def _index() -> dict[str, Any]:
    doc_tokens = [_tokenize(f"{doc.title} {doc.text} {' '.join(doc.tags)}") for doc in CORPUS]
    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens:
        doc_freq.update(set(tokens))

    avg_len = sum(len(tokens) for tokens in doc_tokens) / len(doc_tokens)
    return {
        "doc_tokens": doc_tokens,
        "doc_freq": doc_freq,
        "avg_len": avg_len,
    }


def retrieve_documents(query: str, top_k: int = 4) -> dict[str, Any]:
    """Retrieve relevant Phoenix Reflex corpus documents for a user question."""
    top_k = max(1, min(top_k, 8))
    tracer = get_tracer()
    with tracer.start_as_current_span("retrieve_documents") as span:
        span.set_attribute("input.value", query)
        span.set_attribute("retrieval.top_k", top_k)

        results = _rank(query, top_k)
        max_score = results[0]["score"] if results else 0.0
        span.set_attribute("retrieval.result_count", len(results))
        span.set_attribute("retrieval.max_score", max_score)
        span.set_attribute("output.value", ", ".join(item["id"] for item in results))
        return {
            "query": query,
            "top_k": top_k,
            "max_score": max_score,
            "documents": results,
        }


def _rank(query: str, top_k: int) -> list[dict[str, Any]]:
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    indexed = _index()
    doc_tokens: list[list[str]] = indexed["doc_tokens"]
    doc_freq: Counter[str] = indexed["doc_freq"]
    avg_len: float = indexed["avg_len"]
    total_docs = len(CORPUS)

    scored: list[tuple[float, Document]] = []
    for doc, tokens in zip(CORPUS, doc_tokens, strict=True):
        score = _bm25_score(query_terms, tokens, doc_freq, total_docs, avg_len)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [_serialize(doc, score) for score, doc in scored[:top_k]]


def _bm25_score(
    query_terms: list[str],
    tokens: list[str],
    doc_freq: Counter[str],
    total_docs: int,
    avg_len: float,
) -> float:
    counts = Counter(tokens)
    score = 0.0
    k1 = 1.5
    b = 0.75
    doc_len = len(tokens) or 1

    for term in query_terms:
        tf = counts[term]
        if tf == 0:
            continue
        df = doc_freq[term]
        idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
        denom = tf + k1 * (1 - b + b * doc_len / avg_len)
        score += idf * (tf * (k1 + 1) / denom)
    return round(score, 4)


def _serialize(doc: Document, score: float) -> dict[str, Any]:
    return {
        "id": doc.id,
        "title": doc.title,
        "text": doc.text,
        "tags": list(doc.tags),
        "score": round(score, 4),
    }
