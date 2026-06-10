# Implementacion - multi_agent_adk

## Resumen

Implementada la arquitectura multi-agente experimental detras de `ENABLE_MULTI_AGENT_ADK=1`.
El modo por defecto sigue usando el agente unico estable.

Cambios principales:

- Actualizado `requirements.txt` a `google-adk>=2.0.0,<3.0.0`.
- Extraida `build_single_agent()` en `phoenix_reflex_agent/agent.py`, preservando `root_agent`.
- Creado `phoenix_reflex_agent/multi_agent.py` con:
  - `is_multi_agent_enabled()`
  - `build_multi_agent()`
  - `build_root_agent()`
  - `COORDINATOR_INSTRUCTION`
  - judge subagent
  - improvement subagent
- Integrado `phoenix_reflex/qa.py` para construir el agent via `build_root_agent()`.
- Aniadidos tests unitarios en `tests/test_multi_agent_adk.py`.

## Dependencias

- T0: `pip index versions google-adk` confirmo versiones publicadas `2.2.0`, `2.1.0` y `2.0.0`.
- T1: `pip install -r requirements.txt` termino con exit 0.
- Resultado instalado: `google-adk-2.2.0`.
- `openinference-instrumentation-google-adk>=0.1.11` resolvio sin conflicto; el entorno tenia `0.1.15`.

## Verificacion

- `pytest` -> 37 passed.
- `python -c "import phoenix_reflex; import phoenix_reflex_agent"` -> exit 0.
  - Nota: ADK 2 emite un `UserWarning` interno sobre `FeatureName.PLUGGABLE_AUTH`; no rompe el import.
- `.\init.ps1` -> `RESULTADO: OK - listo para trabajar`.
- Health check local con FastAPI `TestClient`:
  - `GET /health` -> `200 {'status': 'ok'}`.
  - Nota: `TestClient` emitio un `StarletteDeprecationWarning`; no rompe el endpoint.

## Trazabilidad

- R1 -> `pip index versions google-adk` confirmo `>=2.0.0`.
- R2 -> `requirements.txt` y `tests/test_multi_agent_adk.py::test_google_adk_requirement_allows_v2`.
- R2b -> `pip install -r requirements.txt` exit 0; `openinference-instrumentation-google-adk` sin conflicto.
- R3 -> `phoenix_reflex_agent/multi_agent.py::COORDINATOR_INSTRUCTION` y `tests/test_multi_agent_adk.py::test_build_root_agent_preserves_root_agent_export`.
- R3b -> `phoenix_reflex/qa.py::_runner` usa `build_root_agent()`; `tests/test_multi_agent_adk.py::test_runner_uses_build_root_agent_in_qa`.
- R4 -> `tests/test_multi_agent_adk.py::test_multi_agent_builder_defines_judge_subagent`.
- R5 -> `tests/test_multi_agent_adk.py::test_multi_agent_builder_defines_improvement_subagent`.
- R6 -> `tests/test_multi_agent_adk.py::test_default_mode_uses_single_agent`.
- R7 -> `tests/test_multi_agent_adk.py::test_flag_builds_multi_agent_without_prompt_mutation`.
- R8 -> `tests/test_multi_agent_adk.py::test_ask_contract_keys_stay_stable_with_multi_agent_flag`.
- R9 -> `tests/test_multi_agent_adk.py::test_multi_agent_build_failure_falls_back_to_single_agent`.
- R10 -> `pytest` exit 0.
- R11 -> import check exit 0.
- R12 -> `.\init.ps1` exit 0.

## Smoke test manual - frontend

Preparacion:

- [ ] Arrancar el frontend con backend integrado desde `frontend/`: `npm run dev`.
- [ ] Abrir `http://127.0.0.1:5173`.
- [ ] Confirmar que la UI carga sin banner de error y que el rail lateral muestra `Documents`, `Chunks`, `Ask`, `Traces`, `Evaluations` y `MCP`.

Validacion modo default (single-agent):

- [ ] Dejar `ENABLE_MULTI_AGENT_ADK` sin definir o en valor distinto de `1`.
- [ ] En la vista `Ask`, enviar una pregunta sobre los PDFs cargados.
- [ ] Confirmar que aparece `Answer`.
- [ ] En el panel `Evaluations`, confirmar que se muestran `Faithfulness`, `Document relevance`, `Answer quality` y `Failure mode`.
- [ ] Confirmar que aparece el bloque `Regression loop` con pasos `Correction`, `Eval`, `Case`, `Candidate` y `Experiment`.
- [ ] Ir a `Traces` y pulsar `Refresh`; confirmar que la nueva traza aparece y muestra `Faithfulness`, `Quality`, `Failure` y `Corrections`.

Validacion modo multi-agent:

- [ ] Parar el servidor si estaba arrancado.
- [ ] Arrancar con `ENABLE_MULTI_AGENT_ADK=1` y volver a abrir `http://127.0.0.1:5173`.
- [ ] En `Ask`, enviar la misma pregunta usada en modo default.
- [ ] Confirmar que aparece `Answer` y que la UI no muestra `Ask failed`.
- [ ] En `Evaluations`, confirmar que siguen apareciendo `Faithfulness`, `Document relevance`, `Answer quality` y `Failure mode`.
- [ ] Confirmar que el bloque `Regression loop` sigue renderizando los 5 pasos.
- [ ] Ir a `Traces`, pulsar `Refresh` y confirmar que la traza nueva aparece con `Events` mayor que 0.

Validacion de caso de mejora desde UI:

- [ ] En `Ask`, usar una pregunta que produzca `Failure mode` distinto de `none` o un `Improvement case`.
- [ ] Confirmar que el panel muestra `Improvement case` cuando se captura uno.
- [ ] Confirmar que `Generate Candidate` se habilita solo cuando existe `Improvement case`.
- [ ] Pulsar `Generate Candidate` y confirmar que aparece `Candidate prompt`.
- [ ] Pulsar `Run Experiment` y confirmar que aparece `Experiment decision` con `Should promote to staging`.
- [ ] Confirmar visualmente que no se promociona automaticamente ningun prompt.

Validacion MCP desde UI (si MCP esta configurado):

- [ ] Ir a `MCP` y pulsar `Refresh`.
- [ ] Confirmar tiles `Demo ready`, `Enabled`, `Configured` e `Importable`.
- [ ] Pulsar `Use demo question`.
- [ ] En `Ask`, enviar la pregunta precargada.
- [ ] Volver a `MCP` y confirmar que `Last /ask MCP evidence` muestra `Called: yes` si MCP esta listo, o `Called: no` sin error si MCP no esta configurado.
- [ ] Ir a `Traces` y confirmar que la columna `MCP` muestra `used` solo cuando hubo llamada MCP real.

Validacion fallback:

- [ ] Con `ENABLE_MULTI_AGENT_ADK=1`, confirmar que una respuesta normal no devuelve pantalla rota ni `Ask failed`.
- [ ] Si se fuerza o se observa un fallo de construccion multi-agent, confirmar desde `Ask` que la UI sigue recibiendo `Answer` y los campos de evaluacion en lugar de un 500.

## Notas

- No se modifico `PRODUCTION_PROMPT`.
- El modo multi-agent queda opt-in; el default estable no cambia funcionalmente.
