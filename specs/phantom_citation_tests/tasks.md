# phantom_citation_tests - Tasks

- [x] T1 - Crear `tests/test_qa_detection.py` importando `_find_phantom_citations` y `_classify_failure_mode` desde `phoenix_reflex.qa`. Cubre: R1, R2, R3, R4, R5, R6, R7, R8, R9.
- [x] T2 - Anadir tests de `_find_phantom_citations()` para 0 phantoms, 1 phantom, multiples phantoms con deduplicacion, IDs no `pdf:` y brackets anidados o malformados. Cubre: R1, R2, R3, R4, R5.
- [x] T3 - Anadir tests de `_classify_failure_mode()` para `none`, `retrieval`, `generation` y `answer_quality`. Cubre: R6, R7, R8, R9.
- [x] T4 - Ejecutar `pytest` y documentar resultado en `progress/impl_phantom_citation_tests.md`. Cubre: R10.
- [x] T5 - Ejecutar `python -c "import phoenix_reflex; import phoenix_reflex_agent"` y documentar resultado en `progress/impl_phantom_citation_tests.md`. Cubre: R11.
- [x] T6 - Escribir `progress/impl_phantom_citation_tests.md` con resumen de cambios, trazabilidad y comandos ejecutados. Cubre: R10, R11.
