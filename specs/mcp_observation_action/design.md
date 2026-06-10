# mcp_observation_action - Design

## Objetivo

Conectar la introspeccion MCP con una mejora ejecutada. La feature convierte evidencia de Phoenix MCP sobre trazas fallidas en una accion explicita de `/ask`: crear un improvement case cuando el fallo es accionable y no duplicado, o explicar que no habia accion que ejecutar.

## Archivos a crear o modificar

- `phoenix_reflex/reflex.py` - alojar helpers puros para detectar duplicados y crear casos desde evidencia MCP.
- `phoenix_reflex/qa.py` - invocar la accion MCP despues de extraer `phoenix_mcp_evidence` y antes de construir la respuesta JSON.
- `phoenix_reflex/main.py` - no requiere endpoint nuevo; `/ask` seguira devolviendo el dict de `ask_agent`.
- `tests/test_mcp_observation_action.py` - cubrir MCP -> action, deduplicacion, no-action y fallback sin MCP con mocks sin red.
- `progress/impl_mcp_observation_action.md` - reporte del implementer.
- `progress/review_mcp_observation_action.md` - veredicto del reviewer.

## Firmas y funciones

```python
def build_mcp_action(
    *,
    question: str,
    phoenix_mcp_evidence: list[dict[str, object]],
) -> dict[str, object]:
    ...

def extract_mcp_failure_candidate(
    phoenix_mcp_evidence: list[dict[str, object]],
) -> dict[str, object] | None:
    ...

def find_duplicate_improvement_case(
    *,
    source_session_id: str,
    question: str,
    failure_mode: str,
    existing_cases: list[dict[str, object]],
) -> dict[str, object] | None:
    ...

def add_mcp_improvement_case(
    *,
    question: str,
    candidate: dict[str, object],
) -> dict[str, object]:
    ...
```

`build_mcp_action()` sera la unica funcion llamada desde `qa.py`. Debe consultar `list_improvement_cases()` internamente antes de llamar a `add_improvement_case()`.

## Modelo de `mcp_action`

```python
{
    "status": "created" | "duplicate" | "no_action" | "unavailable",
    "description": "improvement case #... captured from trace ...",
    "source_trace_id": "trace-id" | None,
    "failure_mode": "retrieval" | "generation" | "answer_quality" | "unknown" | None,
    "improvement_case": {...} | None,
}
```

## Extraccion de evidencia MCP

La implementacion debe aceptar la forma actual de `phoenix_mcp_evidence`:

```python
{"tool": "phoenix_list-traces", "summary": "..."}
```

y tambien payloads mas ricos que puedan aparecer en tests o en una futura mejora de `_extract_phoenix_mcp_calls()`:

```python
{
    "tool": "phoenix_get-spans",
    "response": {
        "spans": [
            {
                "trace_id": "trace-123",
                "failure_mode": "retrieval",
                "question": "...",
                "answer": "...",
                "explanation": "...",
            }
        ]
    },
}
```

Para que R1 sea verificable sin depender de red, los tests deben pasar evidencia rica directamente a los helpers. Si solo existe `summary` textual y no se puede extraer un `failure_mode` claro, la accion debe ser `no_action`.

## Dependencias previstas

- Sin paquetes nuevos.
- Sin cambios en `requirements.txt`.
- Sin tocar `phoenix_reflex_agent/agent.py` ni `PRODUCTION_PROMPT`.

## Tests y trazabilidad

- R1 -> `tests/test_mcp_observation_action.py::test_mcp_failure_evidence_creates_action`
- R2 -> `tests/test_mcp_observation_action.py::test_mcp_action_checks_existing_cases_before_create`
- R3 -> `tests/test_mcp_observation_action.py::test_mcp_failure_evidence_creates_improvement_case`
- R4 -> `tests/test_mcp_observation_action.py::test_ask_returns_mcp_action_payload`
- R5 -> `tests/test_mcp_observation_action.py::test_mcp_action_no_action_without_failed_trace`
- R6 -> `tests/test_mcp_observation_action.py::test_ask_keeps_local_fallback_without_mcp_action`
- R7 -> `pytest`
- R8 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent"`

## Alternativa descartada

Se descarta pedir al agente LLM que cree el improvement case mediante prompt o tool calling porque haria la accion dificil de verificar y vulnerable a variaciones del modelo. La decision de crear, omitir por duplicado o no actuar debe ser logica determinista en Python a partir de evidencia MCP normalizada.

Tambien se descarta crear candidate prompts automaticamente desde MCP en esta feature. El flujo existente ya mantiene la decision de prompts human-in-the-loop; esta feature debe cerrar primero el beat minimo y verificable: observacion MCP -> improvement case o no-action.
