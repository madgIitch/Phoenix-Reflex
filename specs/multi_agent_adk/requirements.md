# multi_agent_adk - Requirements

## R1
Antes de modificar `requirements.txt`, el implementer DEBE ejecutar `pip index versions google-adk` y confirmar que existe al menos una version publicada `>=2.0.0`. Si no existe, la feature queda bloqueada y se documenta en `progress/impl_multi_agent_adk.md`.

## R2
El sistema DEBE actualizar la dependencia `google-adk` a `>=2.0.0,<3.0.0` sin romper los imports existentes. El cambio solo se realiza si R1 confirma disponibilidad.

## R2b

El sistema DEBE verificar que `openinference-instrumentation-google-adk` instala sin error tras la actualizacion de `google-adk`. Si hay conflicto, se debe pinear la version de `openinference-instrumentation-google-adk` compatible o documentar el bloqueo antes de continuar.

## R3
El sistema DEBE definir un coordinador QA con instruccion de sistema explícita que describa su rol (orquesta retrieval, delega evaluacion al judge subagent y mejora al improvement subagent) y que conserve el contrato publico actual de `/ask`.

## R3b

El sistema DEBE integrar `build_root_agent()` en `phoenix_reflex/qa.py` de forma que: cuando `ENABLE_MULTI_AGENT_ADK=1` la funcion `ask_agent` llame a `build_root_agent()` del modulo `multi_agent`; en caso contrario use el `root_agent` existente sin cambios. El punto de integracion debe ser el unico lugar donde `qa.py` conoce el flag.

## R4
El sistema DEBE definir un subagente judge responsable de producir `faithfulness`, `document_relevance`, `answer_quality` y `failure_mode`.

## R5
El sistema DEBE definir un subagente improvement responsable de proponer o crear improvement cases usando las reglas existentes de `reflex.py`.

## R6
CUANDO `ENABLE_MULTI_AGENT_ADK` no este activo, el sistema DEBE usar el flujo actual de agente unico sin cambios funcionales.

## R7
CUANDO `ENABLE_MULTI_AGENT_ADK=1`, el sistema DEBE construir el flujo multi-agente usando APIs compatibles con ADK 2.x y sin modificar `PRODUCTION_PROMPT`.

## R8
CUANDO se ejecute `/ask` en modo multi-agente, el sistema DEBE devolver los mismos campos JSON estables que devuelve el modo actual, incluyendo `answer`, `faithfulness`, `document_relevance`, `answer_quality`, `failure_mode`, `loop` e `improvement_case`.

## R9
SI la construccion del flujo multi-agente falla en runtime, ENTONCES el sistema DEBE degradar al flujo actual de agente unico sin devolver 500 por esa causa.

## R10
CUANDO se ejecuta `pytest`, el sistema DEBE terminar con exit 0.

## R11
CUANDO se ejecuta `python -c "import phoenix_reflex; import phoenix_reflex_agent"`, el sistema DEBE terminar sin `ImportError`.

## R12
CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con `RESULTADO: OK - listo para trabajar`.
