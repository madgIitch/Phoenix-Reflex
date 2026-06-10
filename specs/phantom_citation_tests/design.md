# phantom_citation_tests - Design

## Objetivo

Anadir cobertura unitaria barata para dos puntos criticos del loop de QA: la deteccion de phantom citations y la clasificacion del `failure_mode`. La feature no cambia comportamiento productivo; congela el comportamiento actual para evitar regresiones durante la demo.

## Archivos a crear o modificar

- `tests/test_qa_detection.py` - nuevo archivo de tests unitarios para `_find_phantom_citations()` y `_classify_failure_mode()`.
- `progress/impl_phantom_citation_tests.md` - reporte del implementer.
- `progress/review_phantom_citation_tests.md` - veredicto del reviewer.

## Firmas y funciones

No se preven firmas nuevas ni cambios en produccion.

Funciones bajo test:

```python
def _find_phantom_citations(answer: str, valid_ids: set[str]) -> set[str]:
    ...

def _classify_failure_mode(
    faithfulness: dict[str, object],
    document_relevance: dict[str, object],
    answer_quality: dict[str, object] | None = None,
) -> str:
    ...
```

## Casos de prueba

`_find_phantom_citations()` debe cubrir:

- 0 phantoms: todas las citas `pdf:` estan en `valid_ids`.
- 1 phantom: una cita `pdf:` ausente de `valid_ids`.
- multiples phantoms: varias citas invalidas y una repetida para verificar deduplicacion por `set`.
- IDs malformados o no PDF: contenido entre corchetes sin prefijo `pdf:` ignorado.
- brackets anidados o malformados: el regex actual no debe lanzar excepciones y el test debe documentar la salida actual.

`_classify_failure_mode()` debe cubrir los 4 valores:

- `none`
- `retrieval`
- `generation`
- `answer_quality`

## Dependencias previstas

- Sin paquetes nuevos.
- Sin cambios en `requirements.txt`.
- Sin llamadas de red.
- Sin tocar `phoenix_reflex_agent/agent.py` ni `PRODUCTION_PROMPT`.

## Tests y trazabilidad

- R1 -> `tests/test_qa_detection.py::test_find_phantom_citations_none`
- R2 -> `tests/test_qa_detection.py::test_find_phantom_citations_one`
- R3 -> `tests/test_qa_detection.py::test_find_phantom_citations_multiple_deduplicates`
- R4 -> `tests/test_qa_detection.py::test_find_phantom_citations_ignores_non_pdf_brackets`
- R5 -> `tests/test_qa_detection.py::test_find_phantom_citations_nested_or_malformed_brackets`
- R6 -> `tests/test_qa_detection.py::test_classify_failure_mode_none`
- R7 -> `tests/test_qa_detection.py::test_classify_failure_mode_retrieval`
- R8 -> `tests/test_qa_detection.py::test_classify_failure_mode_generation`
- R9 -> `tests/test_qa_detection.py::test_classify_failure_mode_answer_quality`
- R10 -> `pytest`
- R11 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent"`

## Alternativa descartada

Se descarta probar estas rutas mediante `/ask` porque requeriria mocks mas amplios del agente ADK, retrieval y evaluadores. Para esta feature el riesgo esta en funciones puras ya extraidas; tests unitarios directos dan mejor senal, menor fragilidad y no dependen de Gemini ni de Phoenix MCP.
