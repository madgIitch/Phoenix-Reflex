from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

PRODUCTION_PROMPT = (
    "You are a QA assistant and observability-aware improvement agent. "
    "Always respond in the same language as the question. "
    "If the question asks about observability, traces, spans, MCP, runtime introspection, debugging failures, "
    "what failed recently, or what improvement to make next, do not answer from PDF documents and do not call "
    "retrieve_documents first. For those observability questions, use Phoenix MCP tools first when they are available, "
    "then summarize what failed and recommend the next concrete improvement. If Phoenix MCP is unavailable, inspect "
    "improvement cases with list_improvement_cases and clearly say MCP evidence was not available. "
    "For observability answers only, it is acceptable to say that you inspected Phoenix traces via Phoenix MCP. "
    "For normal document QA questions, answer using only the documents returned by retrieve_documents. "
    "For normal document QA questions, always call retrieve_documents before answering. "
    "Cite each document id in its own square brackets. "
    "For PDF chunks, cite each returned PDF id exactly as it appears in the tool result, for example "
    "[pdf:filename.pdf p.3 c.2] [pdf:filename.pdf p.4 c.1]. "
    "CRITICAL: only cite document IDs that were actually returned by retrieve_documents in this call - "
    "never invent, guess, or extrapolate page numbers or chunk indices beyond what the tool returned. "
    "For compound questions, break the request into its distinct claims or subquestions before answering. "
    "Answer a subquestion only when the returned text directly supports it; otherwise say that the documents do not cover it. "
    "If the retrieved documents partially answer the question, synthesize what they do contain and explicitly state "
    "which aspects of the question the available documents do not cover. "
    "Do not bridge gaps with background knowledge or common-sense assumptions. "
    "If the question includes extra constraints, places, identities, relationships, categories, or applicability conditions "
    "that are not stated in the retrieved text, say which parts are not covered or irrelevant. "
    "A claim about the purpose, objective, or intended function of something is only supported if the retrieved text "
    "explicitly states that purpose — do not infer it from topic overlap or general relevance. "
    "Do not turn incomplete sentence fragments into standalone facts. "
    "Only say you do not know if the retrieved documents are entirely absent or genuinely unrelated to the question. "
    "Do not invent facts beyond the retrieved documents. Do not mention retrieval mechanics in the final answer; "
    "avoid wording such as retrieved, recuperado, context, contexto, tool, or system. "
    "and do not refer to yourself or the system by name in answers. "
    "You can inspect improvement cases with list_improvement_cases when asked to debug or improve answers."
)

LOCK = Lock()
CACHE_PATH = Path(os.getenv("PROMPT_CACHE_PATH", "/tmp/phoenix_reflex_prompt_cache.json"))
PROMPTS: dict[str, dict[str, Any]] = {
    "production": {
        "tag": "production",
        "version": "production-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": "static",
        "prompt": PRODUCTION_PROMPT,
    }
}
PROMOTIONS: list[dict[str, Any]] = []


def _load_cache() -> None:
    if not CACHE_PATH.exists():
        return
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        prompts = data.get("prompts", {})
        promotions = data.get("promotions", [])
        if isinstance(prompts, dict):
            PROMPTS.update(prompts)
        if isinstance(promotions, list):
            PROMOTIONS.extend(promotions)
    except Exception:
        return


def _save_cache() -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(
                {
                    "prompts": PROMPTS,
                    "promotions": PROMOTIONS,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        return


def get_prompt(tag: str = "production") -> dict[str, Any]:
    with LOCK:
        prompt = PROMPTS.get(tag)
        if prompt:
            return dict(prompt)
        return dict(PROMPTS["production"])


def list_prompts() -> dict[str, Any]:
    with LOCK:
        return {
            "prompts": [dict(prompt) for prompt in PROMPTS.values()],
            "promotions": list(PROMOTIONS),
            "cache_path": str(CACHE_PATH),
        }


def upsert_prompt(tag: str, prompt: str, source: str = "manual") -> dict[str, Any]:
    tag = tag.strip().lower()
    if not tag:
        raise ValueError("tag is required")

    with LOCK:
        version = f"{tag}-v{sum(1 for key in PROMPTS if key == tag) + 1}"
        record = {
            "tag": tag,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "source": source,
            "prompt": prompt,
        }
        PROMPTS[tag] = record
        _save_cache()
        return dict(record)


def promote_prompt_tag(source_tag: str = "candidate", target_tag: str = "staging") -> dict[str, Any]:
    with LOCK:
        source = PROMPTS.get(source_tag)
        if source is None:
            raise ValueError(f"No prompt found for tag {source_tag!r}")
        promoted = dict(source)
        promoted["tag"] = target_tag
        promoted["version"] = f"{target_tag}-from-{source['version']}"
        promoted["created_at"] = datetime.now(UTC).isoformat()
        promoted["source"] = f"promoted:{source_tag}"
        PROMPTS[target_tag] = promoted

        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "source_tag": source_tag,
            "target_tag": target_tag,
            "source_version": source["version"],
            "target_version": promoted["version"],
        }
        PROMOTIONS.append(event)
        _save_cache()
        return {
            "promoted_prompt": dict(promoted),
            "promotion": event,
        }


_load_cache()
