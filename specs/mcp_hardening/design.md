# mcp_hardening - Design

## Objetivo
Hacer que las preguntas de observabilidad disparen Phoenix MCP en el primer turno del agente de forma natural y verificable, sin depender del parche `_force_phoenix_mcp_introspection`. Si MCP no esta listo, `/ask` debe degradar a la introspeccion local de `reflex.py`.

## Archivos a crear o modificar
- `phoenix_reflex/mcp.py` - alojar heuristica compartida de preguntas de observabilidad y mantener la creacion opcional de herramientas.
- `phoenix_reflex/qa.py` - usar la heuristica compartida, enriquecer el primer mensaje de introspeccion y eliminar el fallback forzado.
- `tests/test_mcp_hardening.py` - cubrir dispatch natural, fallback sin MCP y parsing de evidencia MCP.
- `progress/impl_mcp_hardening.md` - reporte del implementer cuando se ejecute la implementacion.
- `progress/review_mcp_hardening.md` - veredicto del reviewer cuando se revise la implementacion.

No se debe modificar `phoenix_reflex_agent/agent.py` salvo que una revision tecnica demuestre que no hay otra forma de cumplir la spec. El prompt de produccion no se toca.

## Firmas y funciones
Funciones previstas:

```python
def is_observability_question(question: str) -> bool: ...
def build_observability_agent_message(question: str, reflex_context: str | None) -> str: ...
```

Cambios previstos:

```python
async def ask_agent(question: str) -> dict[str, object]: ...
async def _extract_phoenix_mcp_calls(session_id: str) -> list[dict[str, object]]: ...
def optional_phoenix_mcp_tools() -> list[object]: ...
```

El primer mensaje para introspeccion debe incluir una instruccion operacional breve: usar Phoenix MCP si esta disponible para inspeccionar trazas/spans antes de responder, y usar el contexto local inyectado solo como fallback o complemento.

## Dependencias previstas
- Sin paquetes nuevos.
- Sin red en tests unitarios.
- Los tests deben mockear `Runner.run_async`, `_session_service()` o helpers internos segun convenga.
- `optional_phoenix_mcp_tools()` debe seguir devolviendo `[]` cuando MCP esta deshabilitado o no importable.

## Tests y trazabilidad
- R1 -> `tests/test_mcp_hardening.py::test_introspection_message_requests_mcp_on_first_turn`
- R2 -> `tests/test_mcp_hardening.py::test_ask_reports_mcp_call_from_first_turn`
- R3 -> `tests/test_mcp_hardening.py::test_no_forced_mcp_second_turn_exists`
- R4 -> `tests/test_mcp_hardening.py::test_introspection_falls_back_to_local_reflex_context_without_mcp`
- R5 -> `tests/test_mcp_hardening.py::test_optional_tools_disabled_when_env_false`
- R6 -> `pytest`
- R7 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent"`

## Alternativa descartada
Se descarta mantener `_force_phoenix_mcp_introspection` con una condicion mas estricta porque seguiria ocultando si el agente no usa MCP de forma natural en el primer turno. La demo necesita evidenciar el comportamiento real del agente, no una reparacion posterior.

Tambien se descarta modificar directamente `PRODUCTION_PROMPT` o `phoenix_reflex_agent/agent.py` porque las reglas del repo requieren spec explicito para tocar el prompt de produccion, y esta feature puede resolverse desde la construccion del mensaje en `qa.py` y helpers de `mcp.py`.
