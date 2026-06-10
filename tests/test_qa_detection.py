from phoenix_reflex.qa import _classify_failure_mode, _find_phantom_citations


def test_find_phantom_citations_none():
    answer = (
        "El articulo citado esta en el documento "
        "[pdf:boe.pdf p.1 c.0] y se confirma en [pdf:boe.pdf p.2 c.1]."
    )
    valid_ids = {"pdf:boe.pdf p.1 c.0", "pdf:boe.pdf p.2 c.1"}

    assert _find_phantom_citations(answer, valid_ids) == set()


def test_find_phantom_citations_one():
    answer = "La respuesta cita una pagina no recuperada [pdf:missing.pdf p.9 c.0]."
    valid_ids = {"pdf:boe.pdf p.1 c.0"}

    assert _find_phantom_citations(answer, valid_ids) == {"pdf:missing.pdf p.9 c.0"}


def test_find_phantom_citations_multiple_deduplicates():
    answer = (
        "Una parte esta soportada [pdf:boe.pdf p.1 c.0], "
        "pero esta no [pdf:missing.pdf p.9 c.0]. "
        "Tambien falta esta [pdf:other.pdf p.3 c.2] "
        "y se repite [pdf:missing.pdf p.9 c.0]."
    )
    valid_ids = {"pdf:boe.pdf p.1 c.0"}

    assert _find_phantom_citations(answer, valid_ids) == {
        "pdf:missing.pdf p.9 c.0",
        "pdf:other.pdf p.3 c.2",
    }


def test_find_phantom_citations_ignores_non_pdf_brackets():
    answer = (
        "La respuesta usa una nota [section:internal] y una cita valida "
        "[pdf:boe.pdf p.1 c.0]."
    )
    valid_ids = {"pdf:boe.pdf p.1 c.0"}

    assert _find_phantom_citations(answer, valid_ids) == set()


def test_find_phantom_citations_nested_or_malformed_brackets():
    answer = (
        "El regex actual captura hasta el primer cierre "
        "[pdf:outer [pdf:inner.pdf p.2 c.0] y deja este sin cerrar "
        "[pdf:broken.pdf p.7 c.1."
    )
    valid_ids: set[str] = set()

    assert _find_phantom_citations(answer, valid_ids) == {"pdf:outer [pdf:inner.pdf p.2 c.0"}


def test_classify_failure_mode_none():
    failure_mode = _classify_failure_mode(
        {"score": 0.9},
        {"score": 0.2},
        {"label": "ok"},
    )

    assert failure_mode == "none"


def test_classify_failure_mode_retrieval():
    failure_mode = _classify_failure_mode(
        {"score": 0.4},
        {"score": 0.3},
        {"label": "ok"},
    )

    assert failure_mode == "retrieval"


def test_classify_failure_mode_generation():
    failure_mode = _classify_failure_mode(
        {"score": 0.4},
        {"score": 0.9},
        {"label": "ok"},
    )

    assert failure_mode == "generation"


def test_classify_failure_mode_answer_quality():
    failure_mode = _classify_failure_mode(
        {"score": 0.9},
        {"score": 0.9},
        {"label": "suspicious"},
    )

    assert failure_mode == "answer_quality"
