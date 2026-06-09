from __future__ import annotations

import json
import os
from statistics import mean, pstdev
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from phoenix_reflex.evaluator import evaluate_faithfulness
from phoenix_reflex.document_store import list_chunks, list_documents
from phoenix_reflex.observability import get_tracer
from phoenix_reflex.prompts import get_prompt, upsert_prompt
from phoenix_reflex.reflex import list_improvement_cases
from phoenix_reflex.retriever import retrieve_documents

load_dotenv()

PROMPT_CANDIDATE_INSTRUCTION = """You improve a RAG agent prompt.

Create a revised prompt that preserves the original behavior but fixes the
failures in the regression examples. The prompt must remain concise and must
reinforce abstention when retrieved context is missing or weak.

Return the prompt text only.

[Current Prompt]
{current_prompt}

[Regression Cases]
{cases}
"""

ANSWER_PROMPT = """{prompt}

Use the retrieved context below. If the context is empty, weak, or unrelated,
abstain instead of inventing details.

[Question]
{question}

[Retrieved Context]
{context}
"""

def generate_prompt_candidate() -> dict[str, Any]:
    tracer = get_tracer()
    with tracer.start_as_current_span("generate_prompt_candidate") as span:
        cases = list_improvement_cases(limit=10)["cases"]
        current_prompt = get_prompt("production")["prompt"]
        cases_text = _format_cases(cases)
        candidate = _generate_text(
            PROMPT_CANDIDATE_INSTRUCTION.format(
                current_prompt=current_prompt,
                cases=cases_text,
            )
        ).strip()
        if not candidate:
            candidate = _safety_net_candidate(current_prompt)

        record = upsert_prompt("candidate", candidate, source="regression_v1")
        span.set_attribute("prompt.candidate.version", record["version"])
        span.set_attribute("regression.case_count", len(cases))
        span.set_attribute("output.value", candidate[:4000])
        return {
            "candidate": record,
            "regression_case_count": len(cases),
        }


def run_prompt_experiment(n_runs: int = 1) -> dict[str, Any]:
    n_runs = max(1, min(n_runs, 5))
    tracer = get_tracer()
    with tracer.start_as_current_span("prompt_experiment") as span:
        candidate = get_prompt("candidate")
        production = get_prompt("production")
        regression_cases = list_improvement_cases(limit=10)["cases"]

        regression_results = [
            _evaluate_regression_case(case, candidate["prompt"], n_runs=n_runs)
            for case in regression_cases
        ]
        good_results = [
            _evaluate_good_question(
                question,
                production["prompt"],
                candidate["prompt"],
                n_runs=n_runs,
            )
            for question in _good_questions()
        ]

        production_regression_avg = _avg(item["production_score"] for item in regression_results)
        candidate_regression_avg = _avg(item["candidate_score"] for item in regression_results)
        production_good_avg = _avg(item["production_score"] for item in good_results)
        candidate_good_avg = _avg(item["candidate_score"] for item in good_results)
        production_regression_stats = _score_stats(
            item["production_score"] for item in regression_results
        )
        candidate_regression_stats = _run_score_stats(regression_results, "candidate_runs")
        production_good_stats = _run_score_stats(good_results, "production_runs")
        candidate_good_stats = _run_score_stats(good_results, "candidate_runs")

        should_promote = (
            bool(regression_results)
            and candidate_regression_avg > production_regression_avg
            and candidate_good_avg >= production_good_avg
        )
        result = {
            "candidate_version": candidate["version"],
            "n_runs": n_runs,
            "generator_temperature": EXPERIMENT_GENERATOR_TEMPERATURE,
            "production_regression_avg": production_regression_avg,
            "production_regression_std": production_regression_stats["std"],
            "candidate_regression_avg": candidate_regression_avg,
            "candidate_regression_std": candidate_regression_stats["std"],
            "production_good_avg": production_good_avg,
            "production_good_std": production_good_stats["std"],
            "candidate_good_avg": candidate_good_avg,
            "candidate_good_std": candidate_good_stats["std"],
            "should_promote_to_staging": should_promote,
            "regression_results": regression_results,
            "good_results": good_results,
        }
        span.set_attribute("experiment.candidate_version", candidate["version"])
        span.set_attribute("experiment.n_runs", n_runs)
        span.set_attribute("experiment.generator_temperature", EXPERIMENT_GENERATOR_TEMPERATURE)
        span.set_attribute("experiment.should_promote_to_staging", should_promote)
        span.set_attribute("experiment.production_regression_avg", production_regression_avg)
        span.set_attribute("experiment.candidate_regression_avg", candidate_regression_avg)
        span.set_attribute("experiment.production_good_avg", production_good_avg)
        span.set_attribute("experiment.candidate_good_avg", candidate_good_avg)
        span.set_attribute("experiment.candidate_regression_std", candidate_regression_stats["std"])
        span.set_attribute("experiment.candidate_good_std", candidate_good_stats["std"])
        return result


def _evaluate_regression_case(
    case: dict[str, Any],
    candidate_prompt: str,
    n_runs: int,
) -> dict[str, Any]:
    question = case["question"]
    production_eval = evaluate_faithfulness(question, case["bad_answer"])
    candidate_runs = [
        _evaluate_generated_answer(question, candidate_prompt)
        for _ in range(n_runs)
    ]
    candidate_stats = _score_stats(run["score"] for run in candidate_runs)
    return {
        "case_id": case["case_id"],
        "question": question,
        "production_answer_source": "captured_failure",
        "production_score": float(production_eval["score"]),
        "candidate_score": candidate_stats["mean"],
        "candidate_score_std": candidate_stats["std"],
        "candidate_label": candidate_runs[-1]["label"],
        "candidate_answer": candidate_runs[-1]["answer"],
        "candidate_runs": candidate_runs,
    }


def _evaluate_good_question(
    question: str,
    production_prompt: str,
    candidate_prompt: str,
    n_runs: int,
) -> dict[str, Any]:
    production_runs = [
        _evaluate_generated_answer(question, production_prompt)
        for _ in range(n_runs)
    ]
    candidate_runs = [
        _evaluate_generated_answer(question, candidate_prompt)
        for _ in range(n_runs)
    ]
    production_stats = _score_stats(run["score"] for run in production_runs)
    candidate_stats = _score_stats(run["score"] for run in candidate_runs)
    return {
        "question": question,
        "production_score": production_stats["mean"],
        "production_score_std": production_stats["std"],
        "candidate_score": candidate_stats["mean"],
        "candidate_score_std": candidate_stats["std"],
        "production_label": production_runs[-1]["label"],
        "candidate_label": candidate_runs[-1]["label"],
        "production_runs": production_runs,
        "candidate_runs": candidate_runs,
    }


def _evaluate_generated_answer(question: str, prompt: str) -> dict[str, Any]:
    answer = _answer_with_prompt(question, prompt)
    evaluation = evaluate_faithfulness(question, answer)
    return {
        "answer": answer,
        "score": float(evaluation["score"]),
        "label": evaluation["label"],
        "explanation": evaluation["explanation"],
    }


EXPERIMENT_GENERATOR_TEMPERATURE = 0.4


def _answer_with_prompt(question: str, prompt: str) -> str:
    # Uses non-zero temperature so that n_runs > 1 produces real variance.
    # Judge calls always use temperature=0.0 for reproducibility.
    retrieved = retrieve_documents(question, top_k=5)
    context = "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['text']}" for doc in retrieved["documents"]
    ) or "No documents retrieved."
    return _generate_text(
        ANSWER_PROMPT.format(
            prompt=prompt,
            question=question,
            context=context,
        ),
        temperature=EXPERIMENT_GENERATOR_TEMPERATURE,
    ).strip()


ADVERSARIAL_QUESTION_PROMPT = """You are building a regression test suite for a RAG system.
Given the document chunks below, generate exactly {n_answerable} questions that:
- Have a specific, verifiable answer found in the chunks (NOT a summarization request)
- Test comprehension of concrete facts, figures, names, or relationships

Then generate exactly {n_abstain} questions that:
- Sound plausible given the document's topic
- Are about details NOT present anywhere in the chunks
- Would require the system to abstain rather than hallucinate

Return a JSON array of strings, questions in order: answerable ones first, then abstention-forcing ones.
No explanations, no labels — just the array.

[Document Chunks]
{chunks_text}
"""


def _good_questions(limit: int = 6) -> list[str]:
    """Return operator-defined anchor questions if available; otherwise generate adversarial ones.

    Operator-defined questions (set via PUT /documents/{id}/anchor-questions) are the
    authoritative source. Auto-generated fallback mixes answerable + abstention-forcing
    questions so the guard is never trivially satisfied by summarization prompts.
    """
    anchor_qs: list[str] = []
    for doc in list_documents():
        anchor_qs.extend(doc.get("anchor_questions") or [])
    if anchor_qs:
        return anchor_qs[:limit]
    return _generate_adversarial_questions(limit=limit)


def _generate_adversarial_questions(limit: int = 4) -> list[str]:
    chunks = list_chunks(enabled_only=True)[:12]
    if not chunks:
        return []
    chunks_text = "\n\n".join(
        f"[{chunk['title']}]\n{chunk['text'][:400]}" for chunk in chunks
    )
    n_answerable = max(1, limit // 2)
    n_abstain = limit - n_answerable
    raw = _generate_text(
        ADVERSARIAL_QUESTION_PROMPT.format(
            n_answerable=n_answerable,
            n_abstain=n_abstain,
            chunks_text=chunks_text,
        )
    ).strip()
    try:
        questions = json.loads(raw)
        if isinstance(questions, list):
            return [str(q) for q in questions if isinstance(q, str)][:limit]
    except Exception:
        pass
    # Fallback: extract lines that look like questions if JSON parse fails
    lines = [line.strip().strip('"').strip("'") for line in raw.splitlines()]
    return [line for line in lines if line.endswith("?")][:limit]


def _generate_text(prompt: str, temperature: float = 0.0) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return response.text or ""


def _format_cases(cases: list[dict[str, Any]]) -> str:
    if not cases:
        return "No regression cases yet. Preserve the current prompt."
    return "\n\n".join(
        (
            f"Case {case['case_id']}\n"
            f"Question: {case['question']}\n"
            f"Bad answer: {case['bad_answer']}\n"
            f"Failure report: {case['failure_report']}\n"
            f"Suggested fix: {case['suggested_fix']}"
        )
        for case in cases
    )


def _safety_net_candidate(current_prompt: str) -> str:
    """Only used when the LLM candidate generator returns empty text."""
    return (
        current_prompt
        + " Before answering, explicitly check whether retrieved context supports "
        "each factual claim. If any requested detail is absent, abstain and name "
        "the missing field instead of guessing."
    )


def _avg(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(float(value) for value in values) / len(values), 4)


def _score_stats(values: Any) -> dict[str, float]:
    scores = [float(value) for value in values]
    if not scores:
        return {"mean": 0.0, "std": 0.0}
    return {
        "mean": round(mean(scores), 4),
        "std": round(pstdev(scores), 4),
    }


def _run_score_stats(results: list[dict[str, Any]], run_key: str) -> dict[str, float]:
    return _score_stats(
        run["score"]
        for result in results
        for run in result.get(run_key, [])
    )
