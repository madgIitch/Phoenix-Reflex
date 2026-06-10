# mcp_observation_action - Tasks

- [x] T1 - Definir el contrato estable de `mcp_action` y helpers puros en `phoenix_reflex/reflex.py`. Cubre: R1, R4, R5.
- [x] T2 - Implementar extraccion determinista de candidatos de fallo desde evidencia MCP rica, aceptando `trace_id`, `failure_mode`, `question`, `answer` y `explanation`. Cubre: R1, R3, R5.
- [x] T3 - Implementar deduplicacion consultando `list_improvement_cases()` antes de crear casos nuevos. Cubre: R2.
- [x] T4 - Implementar creacion de improvement case desde evidencia MCP con `add_improvement_case()`. Cubre: R3.
- [x] T5 - Integrar `build_mcp_action()` en `qa.py` solo cuando `phoenix_mcp_called` sea true, y devolver `mcp_action` en el JSON de `/ask`. Cubre: R4, R6.
- [x] T6 - Escribir `tests/test_mcp_observation_action.py` con mocks sin red para creacion, duplicado, no-action y fallback sin MCP. Cubre: R1, R2, R3, R4, R5, R6.
- [x] T7 - Ejecutar `pytest` y documentar resultado en `progress/impl_mcp_observation_action.md`. Cubre: R7.
- [x] T8 - Ejecutar `python -c "import phoenix_reflex; import phoenix_reflex_agent"` y documentar resultado en `progress/impl_mcp_observation_action.md`. Cubre: R8.
