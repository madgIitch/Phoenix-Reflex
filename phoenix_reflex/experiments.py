from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from google import genai

from phoenix_reflex.evaluator import evaluate_faithfulness
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

GOOD_QUESTIONS = (
    "Que agrega el sprint 1 y que debe hacer si no hay contexto?",
    "Que diferencia hay entre Arize AX y Phoenix Cloud en este proyecto?",
)


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
            candidate = _fallback_candidate(current_prompt)

        record = upsert_prompt("candidate", candidate, source="regression_v1")
        span.set_attribute("prompt.candidate.version", record["version"])
        span.set_attribute("regression.case_count", len(cases))
        span.set_attribute("output.value", candidate[:4000])
        return {
            "candidate": record,
            "regression_case_count": len(cases),
        }


def run_prompt_experiment() -> dict[str, Any]:
    tracer = get_tracer()
    with tracer.start_as_current_span("prompt_experiment") as span:
        candidate = get_prompt("candidate")
        production = get_prompt("production")
        regression_cases = list_improvement_cases(limit=10)["cases"]

        regression_results = [
            _evaluate_regression_case(case, candidate["prompt"]) for case in regression_cases
        ]
        good_results = [_evaluate_good_question(question, production["prompt"], candidate["prompt"]) for question in GOOD_QUESTIONS]

        production_regression_avg = _avg(item["production_score"] for item in regression_results)
        candidate_regression_avg = _avg(item["candidate_score"] for item in regression_results)
        production_good_avg = _avg(item["production_score"] for item in good_results)
        candidate_good_avg = _avg(item["candidate_score"] for item in good_results)

        should_promote = (
            bool(regression_results)
            and candidate_regression_avg > production_regression_avg
            and candidate_good_avg >= production_good_avg
        )
        result = {
            "candidate_version": candidate["version"],
            "production_regression_avg": production_regression_avg,
            "candidate_regression_avg": candidate_regression_avg,
            "production_good_avg": production_good_avg,
            "candidate_good_avg": candidate_good_avg,
            "should_promote_to_staging": should_promote,
            "regression_results": regression_results,
            "good_results": good_results,
        }
        span.set_attribute("experiment.candidate_version", candidate["version"])
        span.set_attribute("experiment.should_promote_to_staging", should_promote)
        span.set_attribute("experiment.production_regression_avg", production_regression_avg)
        span.set_attribute("experiment.candidate_regression_avg", candidate_regression_avg)
        span.set_attribute("experiment.production_good_avg", production_good_avg)
        span.set_attribute("experiment.candidate_good_avg", candidate_good_avg)
        return result


def _evaluate_regression_case(case: dict[str, Any], candidate_prompt: str) -> dict[str, Any]:
    question = case["question"]
    production_eval = evaluate_faithfulness(question, case["bad_answer"])
    candidate_answer = _answer_with_prompt(question, candidate_prompt)
    candidate_eval = evaluate_faithfulness(question, candidate_answer)
    return {
        "case_id": case["case_id"],
        "question": question,
        "production_answer_source": "captured_failure",
        "production_score": float(production_eval["score"]),
        "candidate_score": float(candidate_eval["score"]),
        "candidate_label": candidate_eval["label"],
        "candidate_answer": candidate_answer,
    }


def _evaluate_good_question(question: str, production_prompt: str, candidate_prompt: str) -> dict[str, Any]:
    production_answer = _answer_with_prompt(question, production_prompt)
    candidate_answer = _answer_with_prompt(question, candidate_prompt)
    production_eval = evaluate_faithfulness(question, production_answer)
    candidate_eval = evaluate_faithfulness(question, candidate_answer)
    return {
        "question": question,
        "production_score": float(production_eval["score"]),
        "candidate_score": float(candidate_eval["score"]),
        "production_label": production_eval["label"],
        "candidate_label": candidate_eval["label"],
    }


def _answer_with_prompt(question: str, prompt: str) -> str:
    retrieved = retrieve_documents(question, top_k=5)
    context = "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['text']}" for doc in retrieved["documents"]
    ) or "No documents retrieved."
    return _generate_text(
        ANSWER_PROMPT.format(
            prompt=prompt,
            question=question,
            context=context,
        )
    ).strip()


def _generate_text(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    response = client.models.generate_content(model=model, contents=prompt)
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


def _fallback_candidate(current_prompt: str) -> str:
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
