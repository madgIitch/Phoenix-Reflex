# Sesion actual

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

Siguiente accion:

- Implementar `loop_visible_mission` segun `specs/loop_visible_mission/tasks.md`.
