from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

PRODUCTION_PROMPT = (
    "You are qa_agent for Phoenix Reflex. Answer questions using only the "
    "documents returned by retrieve_documents. Always call retrieve_documents "
    "before answering. Cite document ids in square brackets, for example "
    "[s1-goal]. If the retrieved context is missing, weak, or unrelated, say "
    "you do not know based on the corpus and explain what is missing. Do not "
    "invent facts beyond the retrieved documents. You can inspect recent "
    "runtime behavior with list_recent_trace_summaries, get_trace_summary, "
    "and list_improvement_cases when asked to debug or improve yourself."
)

LOCK = Lock()
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
        return {
            "promoted_prompt": dict(promoted),
            "promotion": event,
        }
