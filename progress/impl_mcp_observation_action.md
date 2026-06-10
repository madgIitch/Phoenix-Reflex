# mcp_observation_action - Implementation Report

## Resumen

Implementada la accion determinista MCP -> improvement case:

- `phoenix_reflex/reflex.py` ahora normaliza evidencia MCP rica, detecta `failure_mode != "none"`, consulta casos existentes y crea u omite una accion estable.
- `phoenix_reflex/qa.py` conserva el payload `response` de herramientas Phoenix MCP, construye `mcp_action` cuando hubo MCP y lo devuelve en `/ask`.
- `tests/test_mcp_observation_action.py` cubre creacion, deduplicacion, no-action y fallback sin MCP con mocks sin red.

## Archivos modificados

- `phoenix_reflex/reflex.py`
- `phoenix_reflex/qa.py`
- `tests/test_mcp_observation_action.py`
- `specs/mcp_observation_action/tasks.md`

## Verificacion

- `pytest tests/test_mcp_observation_action.py -v` -> 6 passed
- `pytest` -> 19 passed
- `python -c "import phoenix_reflex; import phoenix_reflex_agent"` -> exit 0
  - Warning observado: Google ADK `FeatureName.PLUGGABLE_AUTH` experimental.

## Trazabilidad

- R1 -> `tests/test_mcp_observation_action.py::test_mcp_failure_evidence_creates_action` OK
- R2 -> `tests/test_mcp_observation_action.py::test_mcp_action_checks_existing_cases_before_create` OK
- R3 -> `tests/test_mcp_observation_action.py::test_mcp_failure_evidence_creates_improvement_case` OK
- R4 -> `tests/test_mcp_observation_action.py::test_ask_returns_mcp_action_payload` OK
- R5 -> `tests/test_mcp_observation_action.py::test_mcp_action_no_action_without_failed_trace` OK
- R6 -> `tests/test_mcp_observation_action.py::test_ask_keeps_local_fallback_without_mcp_action` OK
- R7 -> `pytest` exit 0 OK
- R8 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent"` exit 0 OK

## Smoke test manual

### Setup

- [ ] `uvicorn phoenix_reflex.main:app --port 8080` arranca sin errores
- [ ] `GET /health` -> `{"status": "ok"}`

### A1 — MCP activo, trazas vacías → no_action

Pregunta:

```text
¿Cuáles son las últimas respuestas fallidas del agente según las trazas de Phoenix?
```

Espera: `phoenix_mcp_called: true`, `mcp_action.status: "no_action"`

- [x] `phoenix_mcp_called: true`
- [x] `mcp_action` presente en el JSON (no ausente ni null)
- [x] `mcp_action.status: "no_action"` (MCP devuelve trazas vacías)

### A2 — Misma pregunta repetida → sin case duplicado

Pregunta (exactamente igual que A1):

```text
¿Cuáles son las últimas respuestas fallidas del agente según las trazas de Phoenix?
```

Espera: `mcp_action.status: "no_action"`, sin improvement case nuevo creado por MCP

- [x] No se crea un segundo case por MCP

### A3 — Introspección de improvement cases

Pregunta:

```text
¿Qué casos de mejora hay registrados en el sistema ahora mismo?
```

Espera: lista de cases con `case_id`, `failure_mode`, `source_session_id`

- [x] El agente lista correctamente los cases existentes

### B1 — MCP activo, sin fallo → no_action

Pregunta:

```text
¿Hay trazas recientes registradas en Phoenix del agente?
```

Espera: `phoenix_mcp_called: true`, `mcp_action.status: "no_action"`, sin case creado

- [x] `mcp_action.status: "no_action"`
- [x] No se crea improvement case por esta llamada

### C1 — Sin MCP, RAG normal

Pregunta:

```text
¿Cuál es el producto interior bruto de España en 2024?
```

Espera: respuesta con citas PDF o abstención, `phoenix_mcp_called: false`, `mcp_action: null`

- [x] `phoenix_mcp_called: false`
- [x] `mcp_action: null`
- [x] Respuesta fiel (abstención correcta o citas PDF)

### D1 — Regresión feature 6: pipeline improvement_case activo

Verificado a través de A1 y A2: ambas sesiones produjeron `improvement_case` no nulo
(faithfulness 0.0 y 0.5 respectivamente). El pipeline `faithfulness → improvement_case`
no ha regresionado. Nota: preguntas fuera del corpus no activan el case porque el agente
abstiene correctamente (faithfulness=1); el trigger real son respuestas infieles.

- [x] `improvement_case` no nulo verificado en sesiones A1/A2
- [x] feature 6 no ha regresionado
