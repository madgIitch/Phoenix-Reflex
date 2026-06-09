# mcp_hardening - Review

## Veredicto

APPROVED

## Alcance revisado

- `phoenix_reflex/mcp.py`
- `phoenix_reflex/qa.py`
- `phoenix_reflex/reflex.py`
- `tests/test_mcp_hardening.py`
- `tests/test_reflex_encoding.py`
- `specs/mcp_hardening/tasks.md`
- `progress/impl_mcp_hardening.md`

## Hallazgos

No se encontraron bloqueos.

## Validaciones

- El primer turno de preguntas de observabilidad ahora contiene instruccion MCP explicita.
- El segundo turno forzado `_force_phoenix_mcp_introspection` fue eliminado.
- `phoenix_mcp_called`, `phoenix_mcp_call_count`, `phoenix_mcp_tools` y `phoenix_mcp_evidence` siguen saliendo de `_extract_phoenix_mcp_calls()`.
- El fallback sin MCP conserva contexto local de `reflex.py`.
- El mojibake detectado en smoke test se normaliza antes de evaluar, guardar y reinyectar contexto.
- No se modifico `phoenix_reflex_agent/agent.py` ni `PRODUCTION_PROMPT`.

## Tests

- `python -m pytest` -> OK, 8 passed
- `python -c "import phoenix_reflex; import phoenix_reflex_agent; print('ok')"` -> OK
- `.\init.ps1` -> OK, 22 OK, 0 WARN, 0 FAIL

## Riesgo residual

La verificacion automatica prueba el contrato interno con mocks. Falta smoke test humano con MCP real configurado para confirmar que el modelo decide llamar a la tool Phoenix MCP en una ejecucion live.

## Follow-up post-smoke

El mojibake detectado en el primer smoke test fue corregido con normalizacion defensiva en `reflex.py`
y tests dedicados. Requiere reiniciar el backend antes de repetir `/ask`, porque el proceso `uvicorn`
anterior no carga cambios de codigo ya aplicados.
