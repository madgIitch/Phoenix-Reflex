# mcp_observation_action - Requirements

## R1
CUANDO una pregunta de introspeccion use Phoenix MCP y la evidencia MCP contenga al menos una traza o span con `failure_mode` distinto de `none`, el sistema DEBE crear una accion MCP concreta basada en esa evidencia.

## R2
CUANDO el sistema vaya a crear una accion MCP basada en una traza o span, el sistema DEBE consultar los improvement cases existentes antes de actuar para evitar duplicados por `source_session_id` o por una firma estable de pregunta/fallo.

## R3
CUANDO la accion MCP detecte un fallo no duplicado, el sistema DEBE crear un improvement case con `source_session_id` de la traza MCP, `failure_mode` del fallo encontrado y un reporte derivado de la evidencia MCP.

## R4
CUANDO la accion MCP cree, omita o no encuentre trabajo accionable, el sistema DEBE devolver `mcp_action` en la respuesta JSON de `/ask` con `status`, `description`, `source_trace_id` y `improvement_case`.

## R5
SI Phoenix MCP no devuelve trazas o spans con `failure_mode` distinto de `none`, ENTONCES el sistema DEBE devolver `mcp_action.status: "no_action"` sin crear improvement cases nuevos.

## R6
SI Phoenix MCP esta deshabilitado o no se usa en la sesion, ENTONCES el sistema DEBE mantener el comportamiento actual de fallback local sin crear acciones MCP.

## R7
CUANDO se ejecuta `pytest`, el sistema DEBE terminar con exit 0.

## R8
CUANDO se ejecuta `python -c "import phoenix_reflex; import phoenix_reflex_agent"`, el sistema DEBE terminar sin `ImportError`.
