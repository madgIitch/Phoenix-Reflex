# mcp_hardening - Tasks

- [x] T1 - Extraer `is_observability_question(question: str) -> bool` a `phoenix_reflex/mcp.py` y usarlo desde `qa.py`. Cubre: R1.
- [x] T2 - Crear `build_observability_agent_message(question, reflex_context)` para construir el primer mensaje de introspeccion con instruccion de uso MCP y fallback local. Cubre: R1, R4.
- [x] T3 - Refactorizar `ask_agent()` para enviar el mensaje enriquecido antes de `Runner.run_async()` y preservar la inyeccion de `format_reflex_context()`. Cubre: R1, R4.
- [x] T4 - Eliminar `_force_phoenix_mcp_introspection` y cualquier llamada que ejecute un segundo turno solo para forzar MCP. Cubre: R3.
- [x] T5 - Mantener `_extract_phoenix_mcp_calls()` como fuente de verdad de `phoenix_mcp_called`, `phoenix_mcp_call_count`, `phoenix_mcp_tools` y `phoenix_mcp_evidence`. Cubre: R2.
- [x] T6 - Asegurar que `optional_phoenix_mcp_tools()` devuelve `[]` cuando `ENABLE_PHOENIX_MCP` no esta activo o faltan dependencias/configuracion. Cubre: R5.
- [x] T7 - Escribir `tests/test_mcp_hardening.py` con mocks sin red para dispatch natural, evidencia MCP, fallback local y ausencia del segundo turno forzado. Cubre: R1, R2, R3, R4, R5.
- [x] T8 - Ejecutar `pytest` y documentar resultado en `progress/impl_mcp_hardening.md`. Cubre: R6.
- [x] T9 - Ejecutar `python -c "import phoenix_reflex; import phoenix_reflex_agent"` y documentar resultado en `progress/impl_mcp_hardening.md`. Cubre: R7.
