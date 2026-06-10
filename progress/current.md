# Sesion actual

Feature preparada: **ID 9** - `phantom_citation_tests` (P2, SDD).

Cambios aplicados en esta fase:

- Ejecutado `.\init.ps1` con exit 0.
- Leidos `docs/specs.md`, `docs/architecture.md` y `docs/conventions.md`.
- Revisada la logica actual de `_find_phantom_citations()` y `_classify_failure_mode()` en `phoenix_reflex/qa.py`.
- Creados `specs/phantom_citation_tests/requirements.md`, `specs/phantom_citation_tests/design.md` y `specs/phantom_citation_tests/tasks.md`.
- Marcado `phantom_citation_tests` como `spec_ready` en `feature_list.json`.

Siguiente accion:

- Pausa obligatoria SDD: el humano debe aprobar la spec antes de implementar tests.
- Si el humano confirma aprobacion, cambiar `phantom_citation_tests` a `in_progress` e implementar `tests/test_qa_detection.py`.

---

Feature completada: **ID 8** - `judge_validation_table` (P2, no-SDD).

Cambios aplicados en esta fase:

- Ejecutado `.\init.ps1` con exit 0.
- Ampliada la tabla "Human Validation of the Judge" en `README.md` de 4 a 8 casos.
- Rehecha la tabla para basar los casos en las dos specs anteriores: `loop_visible_mission` y `mcp_observation_action`.
- Añadido al menos un falso positivo confirmado del juez: caso 6, MCP con trazas vacias penalizado como infiel.
- Añadido al menos un falso negativo confirmado del juez: caso 4, pregunta mixta con detalle externo no soportado que el juez no penalizo.
- Actualizado el agreement rate de la tabla a 6 / 8 (75%).
- Marcado `judge_validation_table` como `done` en `feature_list.json`.

Siguiente accion:

- Feature **ID 9** - `phantom_citation_tests` (P2, SDD) esta `pending`.
- Debe pasar por spec_author: crear `specs/phantom_citation_tests/{requirements,design,tasks}.md`, marcar `spec_ready`, y pausar por aprobacion humana antes de implementar.

---

Feature completada: **ID 5** - `cloud_run_deploy` (P0, no-SDD).

Cambios aplicados en esta fase:

- Creado `specs/mcp_hardening/requirements.md`.
- Creado `specs/mcp_hardening/design.md`.
- Creado `specs/mcp_hardening/tasks.md`.
- Marcado `mcp_hardening` como `spec_ready` en `feature_list.json`.
- Aprobacion humana recibida.
- Marcado `mcp_hardening` como `in_progress` en `feature_list.json`.
- Implementacion completada.
- Reviewer: APPROVED en `progress/review_mcp_hardening.md`.
- Marcado `mcp_hardening` como `review_pending` en `feature_list.json`.
- Smoke test humano detecto mojibake en respuestas de introspeccion.
- Reabierto a `in_progress` para corregir normalizacion de texto.
- Corregida normalizacion de mojibake en respuestas/contexto Reflex.
- Marcado `mcp_hardening` como `review_pending` en `feature_list.json`.
- Smoke test humano confirmado: ok.
- Marcado `mcp_hardening` como `done` en `feature_list.json`.

Cambios de esta fase:

- Marcado `cloud_run_deploy` como `in_progress` en `feature_list.json`.
- Actualizado `scripts/deploy-cloud-run.ps1` para desplegar `ENABLE_PHOENIX_MCP`, `PHOENIX_HOST` y secret `PHOENIX_API_KEY`.
- Creado secret `PHOENIX_API_KEY` en Google Secret Manager.
- Desplegado Cloud Run `phoenix-reflex` en `europe-west1`.
- Aplicado control de costes: `min-instances=0`, `max-instances=2`, CPU throttling activo.
- Verificado `GET /health` -> 200.
- Verificado `GET /observability/mcp` -> `demo_ready: true`.
- Agregada URL publica en primera linea de `README.md`.
- Marcado `cloud_run_deploy` como `done` en `feature_list.json`.

Estado:

- Feature **ID 6** - `loop_visible_mission` procesada por spec_author.
- Creados `specs/loop_visible_mission/requirements.md`, `specs/loop_visible_mission/design.md` y `specs/loop_visible_mission/tasks.md`.
- Ajustada la spec para que el loop de la demo use el frontend como superficie principal.
- Reemplazado el corpus recomendado por los PDFs concretos de demo: `BOE-A-2015-11430-consolidado.pdf` y `lo_2-2007.pdf`.
- Corregido el guion de preguntas tras verificar que `BOE-A-2015-11430-consolidado.pdf` es el Estatuto de los Trabajadores y `lo_2-2007.pdf` es el Estatuto de Autonomia para Andalucia.
- Marcado `loop_visible_mission` como `spec_ready` en `feature_list.json`.
- Aprobacion humana recibida.
- Marcado `loop_visible_mission` como `in_progress` en `feature_list.json`.
- Implementacion completada.
- Reviewer: APPROVED en `progress/review_loop_visible_mission.md`.
- Marcado `loop_visible_mission` como `review_pending` en `feature_list.json`.
- Smoke test humano detecto que la UI podia quedarse en `Asking` tras error de `/ask`.
- Corregido manejo de errores en `AskView`, `Generate Candidate` y `Run Experiment`.
- Re-verificado `npm run build` en `frontend/` con exit 0.
- Smoke test humano detecto `429 RESOURCE_EXHAUSTED` en embeddings de Gemini durante retrieval.
- Corregido fallback de retrieval: si falla semantic/hybrid por cuota u otro error, `/ask` usa BM25 (`bm25_fallback`) en lugar de devolver 500.
- Re-verificado `pytest` -> 13 passed.
- Re-verificado `npm run build` en `frontend/` con exit 0.

Siguiente accion:

- Feature **ID 7** - `mcp_observation_action` procesada por spec_author.
- Creados `specs/mcp_observation_action/requirements.md`, `specs/mcp_observation_action/design.md` y `specs/mcp_observation_action/tasks.md`.
- Marcado `mcp_observation_action` como `spec_ready` en `feature_list.json`.
- Aprobacion humana recibida.
- Marcado `mcp_observation_action` como `in_progress` en `feature_list.json`.
- Implementacion completada.
- Reviewer: APPROVED en `progress/review_mcp_observation_action.md`.
- Marcado `mcp_observation_action` como `review_pending` en `feature_list.json`.
- Pausa obligatoria SDD: smoke tests humanos pendientes con Phoenix MCP real.
