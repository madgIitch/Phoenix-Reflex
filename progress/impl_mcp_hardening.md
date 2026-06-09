# mcp_hardening - Implementacion

## Resumen

Implementado el hardening de Phoenix MCP para que las preguntas de observabilidad preparen el primer turno del agente con una instruccion explicita de uso MCP, sin el segundo turno forzado `_force_phoenix_mcp_introspection`.

## Cambios

- `phoenix_reflex/mcp.py`
  - Agregado `is_observability_question(question)`.
  - Agregado `build_observability_agent_message(question, reflex_context)`.
  - Mantenido `optional_phoenix_mcp_tools()` como path opcional/graceful.

- `phoenix_reflex/qa.py`
  - `ask_agent()` usa `is_observability_question()`.
  - Las preguntas de introspeccion usan `build_observability_agent_message()` antes de `Runner.run_async()`.
  - Eliminada la llamada al segundo turno forzado.
  - Eliminada `_force_phoenix_mcp_introspection`.
  - Eliminada la heuristica local `_is_introspection_question`.

- `tests/test_mcp_hardening.py`
  - Agregados tests unitarios sin red para dispatch natural, evidencia MCP, fallback local, ausencia del segundo turno forzado y MCP deshabilitado.

- `phoenix_reflex/reflex.py`
  - Agregada normalizacion defensiva de mojibake para respuestas, casos de mejora y contexto Reflex.

- `tests/test_reflex_encoding.py`
  - Agregados tests para mojibake simple, doble y contexto heredado corrupto.

## Trazabilidad

- R1 -> `tests/test_mcp_hardening.py::test_introspection_message_requests_mcp_on_first_turn` OK
- R2 -> `tests/test_mcp_hardening.py::test_ask_reports_mcp_call_from_first_turn` OK
- R3 -> `tests/test_mcp_hardening.py::test_no_forced_mcp_second_turn_exists` OK
- R4 -> `tests/test_mcp_hardening.py::test_introspection_falls_back_to_local_reflex_context_without_mcp` OK
- R5 -> `tests/test_mcp_hardening.py::test_optional_tools_disabled_when_env_false` OK
- R6 -> `python -m pytest` OK, 5 passed
- R7 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent; print('ok')"` OK

## Correccion post-smoke: mojibake

El smoke test humano detecto texto como `travÃ©s` y `RecuperaciÃ³n` en respuestas de introspeccion.
Se corrigio normalizando mojibake al recibir respuestas del agente, al guardar trace summaries,
al crear improvement cases y al formatear contexto Reflex heredado.

Tests agregados:

- `tests/test_reflex_encoding.py::test_repair_mojibake_single_pass` OK
- `tests/test_reflex_encoding.py::test_repair_mojibake_double_pass` OK
- `tests/test_reflex_encoding.py::test_format_reflex_context_repairs_legacy_mojibake` OK

## Verificacion

- `python -m py_compile phoenix_reflex\mcp.py phoenix_reflex\qa.py tests\test_mcp_hardening.py` -> OK
- `python -m pytest tests\test_mcp_hardening.py -v` -> OK, 5 passed
- `python -m pytest` -> OK, 8 passed
- `python -c "import phoenix_reflex; import phoenix_reflex_agent; print('ok')"` -> OK
- `.\init.ps1` -> OK, 22 OK, 0 WARN, 0 FAIL

## Smoke test manual

- Nota Windows/PowerShell: antes de imprimir JSON con acentos, ejecutar:
  `[Console]::InputEncoding = [System.Text.UTF8Encoding]::new(); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); $OutputEncoding = [System.Text.UTF8Encoding]::new()`
- [ ] `uvicorn phoenix_reflex.main:app --port 8080` arranca sin errores
- [ ] `GET /health` -> `{"status": "ok"}`
- [ ] `GET /observability/mcp` devuelve estado MCP esperado
- [ ] `POST /ask {"question": "Que fallo muestran las trazas recientes?"}` devuelve answer no vacio
- [ ] Si MCP esta configurado, la respuesta incluye `phoenix_mcp_called: true`
- [ ] Si `ENABLE_PHOENIX_MCP=0`, la respuesta usa contexto local y mantiene `phoenix_mcp_called: false`
