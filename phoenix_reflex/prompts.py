from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

PRODUCTION_PROMPT = (
    "You are a QA assistant. Answer questions using only the documents returned by retrieve_documents. "
    "Always call retrieve_documents before answering. "
    "Always respond in the same language as the question. "
    "Cite each document id in its own square brackets, for example "
    "[s1-goal] [s1-prompt]. For PDF chunks, cite each returned PDF id exactly as it appears in the tool result, for example "
    "[pdf:filename.pdf p.3 c.2] [pdf:filename.pdf p.4 c.1]. "
    "CRITICAL: only cite document IDs that were actually returned by retrieve_documents in this call — "
    "never invent, guess, or extrapolate page numbers or chunk indices beyond what the tool returned. "
    "If the retrieved documents partially answer the question, synthesize what they do contain and explicitly state "
    "which aspects of the question the available documents do not cover. "
    "Only say you do not know if the retrieved documents are entirely absent or genuinely unrelated to the question. "
    "Do not invent facts beyond the retrieved documents and do not refer to yourself or the system by name in answers. "
    "You can inspect recent runtime behavior with list_recent_trace_summaries, get_trace_summary, "
    "and list_improvement_cases when asked to debug or improve yourself."
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
