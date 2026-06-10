# Sesion actual

Feature completada: **ID 10** - `multi_agent_adk` (P3, SDD).

Cambios de esta fase:

- Aprobacion humana recibida con "aprobado".
- Ejecutado `.\init.ps1` con exit 0 antes de implementar.
- Marcado `multi_agent_adk` como `in_progress` en `feature_list.json`.
- T0 confirmado: `pip index versions google-adk` muestra `2.2.0`, `2.1.0` y `2.0.0`.
- Actualizado `requirements.txt` a `google-adk>=2.0.0,<3.0.0`.
- Verificado `pip install -r requirements.txt` con exit 0; `openinference-instrumentation-google-adk` sin conflicto.
- Extraida `build_single_agent()` preservando `root_agent`.
- Creado `phoenix_reflex_agent/multi_agent.py` con coordinador, judge subagent, improvement subagent y fallback a single-agent.
- Integrado `qa.py` para usar `build_root_agent()`.
- Aniadido `tests/test_multi_agent_adk.py`.
- Verificado `pytest` -> 37 passed.
- Verificado import check -> exit 0.
- Verificado `.\init.ps1` -> `RESULTADO: OK - listo para trabajar`.
- Escrito `progress/impl_multi_agent_adk.md`.
- Reviewer: APPROVED en `progress/review_multi_agent_adk.md`.
- Marcado `multi_agent_adk` como `review_pending`.

Cambios adicionales de cierre:

- Bug fix: COORDINATOR_INSTRUCTION corregida para devolver texto plano (no JSON).
- Bug fix: _find_answer_style_issues detecta json_wrapped_response como issue.
- Añadido *.pdf a .gitignore.
- Smoke tests 1, 2 y 3 superados con faithfulness: 1.0 y failure_mode: none.
- Marcado `multi_agent_adk` como `done` en `feature_list.json`.

Siguiente accion:

- Feature **ID 11** - `frontend_multi_agent_toggle` (P3, SDD) esta `pending`.
- Debe pasar por spec_author antes de implementar.

---

Feature desbloqueada y preparada: **ID 10** - `multi_agent_adk` (P3, SDD).

Cambios aplicados en esta fase:

- Recibida instruccion humana explicita: "desbloquea".
- Verificada documentacion oficial de ADK:
  - `https://adk.dev/` anuncia `ADK Python 2.0 GA` con graph workflows y collaborative agents.
  - `https://adk.dev/graphs/` indica soporte de graph-based workflows en `ADK Python v2.0.0`.
  - `https://adk.dev/workflows/` describe graph-based, dynamic y collaborative workflows para ADK 2.0+.
- Confirmado que P0/P1 ya estan `done` y que `.\init.ps1` pasaba antes de iniciar.
- Detectado que el repo actual tiene `google-adk>=1.32.0,<2.0.0`; la spec incluye migracion controlada a ADK 2.x.
- Detectado que `AGENTS.md` menciona `phoenix_reflex/agent.py`, pero el archivo real del agente es `phoenix_reflex_agent/agent.py`.
- Creados `specs/multi_agent_adk/requirements.md`, `specs/multi_agent_adk/design.md` y `specs/multi_agent_adk/tasks.md`.
- Marcado `multi_agent_adk` como `spec_ready` en `feature_list.json`.

Siguiente accion:

- Pausa obligatoria SDD: el humano debe aprobar la spec antes de implementar.
- Si el humano confirma aprobacion, cambiar `multi_agent_adk` a `in_progress` e implementar con fallback default al agente unico.

---

Feature preparada: **ID 9** - `phantom_citation_tests` (P2, SDD).

Cambios aplicados en esta fase:

- Ejecutado `.\init.ps1` con exit 0.
- Leidos `docs/specs.md`, `docs/architecture.md` y `docs/conventions.md`.
- Revisada la logica actual de `_find_phantom_citations()` y `_classify_failure_mode()` en `phoenix_reflex/qa.py`.
- Creados `specs/phantom_citation_tests/requirements.md`, `specs/phantom_citation_tests/design.md` y `specs/phantom_citation_tests/tasks.md`.
- Marcado `phantom_citation_tests` como `spec_ready` en `feature_list.json`.
- Aprobacion humana recibida con "adelante".
- Marcado `phantom_citation_tests` como `in_progress` en `feature_list.json`.
- Implementados tests unitarios en `tests/test_qa_detection.py`.
- Verificado `pytest` -> 28 passed.
- Verificado `python -c "import phoenix_reflex; import phoenix_reflex_agent"` -> exit 0.
- Escrito `progress/impl_phantom_citation_tests.md`.
- Reviewer: APPROVED en `progress/review_phantom_citation_tests.md`.
- Marcado `phantom_citation_tests` como `review_pending` en `feature_list.json`.
- Smoke test humano confirmado:
  - `pytest tests/test_qa_detection.py -v` -> 9 passed.
  - `.\init.ps1` -> `RESULTADO: OK - listo para trabajar`.
- Marcado `phantom_citation_tests` como `done` en `feature_list.json`.

Siguiente accion:

- Feature **ID 10** - `multi_agent_adk` esta `blocked`.
- No iniciar sin instrucciones explicitas: esta bloqueada hasta que P0/P1 esten completos y la demo sea estable.

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
