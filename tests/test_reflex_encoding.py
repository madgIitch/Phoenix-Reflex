from __future__ import annotations

from phoenix_reflex import reflex


def test_repair_mojibake_single_pass() -> None:
    text = "Al inspeccionar a travÃ©s de Phoenix MCP."

    assert reflex.repair_mojibake(text) == "Al inspeccionar a través de Phoenix MCP."


def test_repair_mojibake_double_pass() -> None:
    text = "RecuperaciÃƒÂ³n e introducciÃƒÂ³n de informaciÃƒÂ³n."

    assert reflex.repair_mojibake(text) == "Recuperación e introducción de información."


def test_format_reflex_context_repairs_legacy_mojibake() -> None:
    case = {
        "case_id": "case-test",
        "question": "Que fallo muestran las trazas recientes?",
        "bad_answer": "Respuesta con puntuaciÃƒÂ³n parcial.",
        "faithfulness_label": "partially_faithful",
        "faithfulness_score": 0.5,
        "failure_mode": "retrieval",
        "failure_report": "IntroducciÃƒÂ³n de informaciÃƒÂ³n no soportada.",
        "suggested_fix": "Improve corpus coverage.",
    }

    with reflex.LOCK:
        reflex.IMPROVEMENT_CASES.appendleft(case)
    try:
        context, _context_ids = reflex.format_reflex_context(limit=1)
    finally:
        with reflex.LOCK:
            reflex.IMPROVEMENT_CASES.remove(case)

    assert "puntuación parcial" in context
    assert "Introducción de información" in context
    assert "Ã" not in context
