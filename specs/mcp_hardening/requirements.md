# mcp_hardening - Requirements

## R1
CUANDO la pregunta del usuario sea de observabilidad, trazas, fallos, regresiones o casos de mejora, el sistema DEBE preparar el primer turno del agente con una instruccion explicita para usar Phoenix MCP si esta disponible.

## R2
CUANDO Phoenix MCP este disponible y el agente use una herramienta Phoenix MCP en el primer turno, el sistema DEBE devolver `phoenix_mcp_called: true`, `phoenix_mcp_call_count` mayor que 0 y evidencia de la herramienta en la respuesta JSON de `/ask`.

## R3
El sistema DEBE eliminar el segundo turno forzado de introspeccion `_force_phoenix_mcp_introspection`.

## R4
MIENTRAS Phoenix MCP no este disponible, el sistema DEBE responder preguntas de introspeccion usando el contexto local de `reflex.py` sin fallar por ausencia de MCP.

## R5
SI Phoenix MCP esta deshabilitado por `ENABLE_PHOENIX_MCP=0`, ENTONCES el sistema DEBE mantener `phoenix_mcp_called: false` y no intentar crear herramientas MCP.

## R6
CUANDO se ejecute `pytest`, el sistema DEBE terminar con exit 0.

## R7
CUANDO se ejecute `python -c "import phoenix_reflex; import phoenix_reflex_agent"`, el sistema DEBE terminar sin `ImportError` ni `ModuleNotFoundError`.
