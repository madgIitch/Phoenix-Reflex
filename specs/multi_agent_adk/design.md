# multi_agent_adk - Design

## Objetivo

Introducir una arquitectura multi-agente con ADK 2.x sin poner en riesgo la demo estable. La implementacion debe quedar detras de `ENABLE_MULTI_AGENT_ADK=1`, mantener el contrato JSON de `/ask` y conservar el flujo actual como fallback.

El bloqueo original exigia confirmar si ADK 2.0 graph engine estaba en GA. La documentacion oficial actual indica:

- `https://adk.dev/` anuncia `ADK Python 2.0 GA` con graph workflows y collaborative agents.
- `https://adk.dev/graphs/` indica que graph-based workflows estan soportados en `ADK Python v2.0.0`.
- `https://adk.dev/workflows/` describe graph-based, dynamic y collaborative workflows como tipos disponibles en ADK 2.0 o superior.

## Estado actual del repo

- La dependencia actual es `google-adk>=1.32.0,<2.0.0`, por lo que la implementacion debe migrar a ADK 2.x.
- La definicion real del agente esta en `phoenix_reflex_agent/agent.py`.
- `AGENTS.md` menciona `phoenix_reflex/agent.py`, pero ese archivo no existe en el workspace actual.
- `phoenix_reflex/qa.py` contiene hoy la orquestacion principal y ya produce el contrato JSON estable de `/ask`.

## Archivos a crear o modificar

- `requirements.txt` - actualizar `google-adk` a un rango compatible con 2.x.
- `phoenix_reflex_agent/agent.py` - conservar `root_agent` y delegar su construccion a una factory, sin modificar `PRODUCTION_PROMPT`.
- `phoenix_reflex_agent/multi_agent.py` - nuevo modulo para construir coordinador, judge subagent, improvement subagent y fallback.
- `phoenix_reflex/qa.py` - integrar el modo multi-agente solo si hace falta para preservar el contrato `/ask`; mantener fallback al flujo actual.
- `tests/test_multi_agent_adk.py` - tests unitarios sin llamadas reales a Gemini.
- `progress/impl_multi_agent_adk.md` - reporte del implementer.
- `progress/review_multi_agent_adk.md` - veredicto del reviewer.

## Firmas y funciones

```python
def is_multi_agent_enabled() -> bool:
    ...

def build_single_agent() -> object:
    ...

def build_multi_agent() -> object:
    ...

def build_root_agent() -> object:
    ...
```

Si las APIs finales de ADK 2.x requieren clases concretas distintas, el implementer debe adaptar las firmas internas manteniendo estable `root_agent` como export publico de `phoenix_reflex_agent.agent`.

## Modelo de arquitectura

El modo default sigue siendo el agente unico actual:

```text
/ask -> qa.ask_agent -> Runner(root_agent single-agent) -> evaluadores/reflex existentes
```

El modo experimental queda detras del flag:

```text
ENABLE_MULTI_AGENT_ADK=1
  -> coordinator QA
      -> retrieval/tool step existente
      -> judge subagent
      -> improvement subagent
      -> qa.py normaliza salida al contrato JSON actual
```

La primera implementacion debe priorizar importabilidad, testabilidad y fallback. No debe intentar redisenar todo `qa.py` si eso aumenta el riesgo; puede encapsular subagentes como componentes ADK y seguir usando evaluadores deterministicos existentes para producir el JSON final.

## Pre-condicion obligatoria (T0)

Antes de tocar `requirements.txt`, el implementer ejecuta:

```powershell
pip index versions google-adk
```

Si no aparece ninguna version `>=2.0.0`, la feature se bloquea y se documenta. Solo se continua si la version existe en PyPI.

## Dependencias previstas

- Cambiar `google-adk>=1.32.0,<2.0.0` a `google-adk>=2.0.0,<3.0.0` **solo tras confirmar T0**.
- Tras el cambio, ejecutar `pip install -r requirements.txt` y verificar que `openinference-instrumentation-google-adk` instala sin `ResolutionImpossible`. Si falla, pinear la version compatible antes de continuar (documenta en `progress/impl_multi_agent_adk.md`).
- No cambiar `google-genai` salvo que `pip` lo exija.
- No tocar `PRODUCTION_PROMPT`.

## Instruccion del coordinador QA

El coordinador debe recibir una instruccion de sistema concreta. Ejemplo orientativo (el implementer puede ajustar el tono pero no el rol):

```text
You are the QA coordinator. Your job:
1. Retrieve context using the available retrieval tool.
2. Delegate evaluation (faithfulness, document_relevance, answer_quality, failure_mode) to the judge subagent.
3. If failure_mode != 'none', delegate improvement case creation to the improvement subagent.
4. Return a single JSON response that matches the /ask contract.
Do not modify the user query. Do not call Gemini directly for evaluation.
```

Esta instruccion va en `multi_agent.py` como constante `COORDINATOR_INSTRUCTION`, separada de `PRODUCTION_PROMPT`.

## Punto de integracion en qa.py

`qa.py` es el unico sitio que conoce el flag. El patron de integracion es:

```python
# phoenix_reflex/qa.py
from phoenix_reflex_agent.multi_agent import build_root_agent, is_multi_agent_enabled

def ask_agent(...):
    agent = build_root_agent()   # interno: single o multi segun flag
    runner = Runner(agent, ...)
    ...
```

Esto evita condicionales dispersos en `qa.py` y centraliza la decision en `build_root_agent()`.

## Tests y trazabilidad

- R1  -> T0: `pip index versions google-adk` documentado en `progress/impl_multi_agent_adk.md`
- R2  -> `tests/test_multi_agent_adk.py::test_google_adk_requirement_allows_v2`
- R2b -> T1: resultado de `pip install -r requirements.txt` documentado; test de import en R11
- R3  -> `tests/test_multi_agent_adk.py::test_build_root_agent_preserves_root_agent_export`
- R3b -> T5: integracion en `qa.py`; `tests/test_multi_agent_adk.py::test_ask_contract_keys_stay_stable_with_multi_agent_flag`
- R4  -> `tests/test_multi_agent_adk.py::test_multi_agent_builder_defines_judge_subagent`
- R5  -> `tests/test_multi_agent_adk.py::test_multi_agent_builder_defines_improvement_subagent`
- R6  -> `tests/test_multi_agent_adk.py::test_default_mode_uses_single_agent`
- R7  -> `tests/test_multi_agent_adk.py::test_flag_builds_multi_agent_without_prompt_mutation`
- R8  -> `tests/test_multi_agent_adk.py::test_ask_contract_keys_stay_stable_with_multi_agent_flag`
- R9  -> `tests/test_multi_agent_adk.py::test_multi_agent_build_failure_falls_back_to_single_agent`
- R10 -> `pytest`
- R11 -> `python -c "import phoenix_reflex; import phoenix_reflex_agent"`
- R12 -> `.\init.ps1`

## Alternativa descartada

Se descarta reemplazar inmediatamente todo `/ask` por un graph workflow obligatorio. Aunque ADK 2.0 ya documenta graph workflows, el repo tiene una demo estable, trazas y tests alrededor del flujo actual. Un cambio obligatorio tendria demasiado blast radius para una feature P3.

Tambien se descarta modificar `PRODUCTION_PROMPT`: la separacion de roles debe lograrse con subagentes, instrucciones especificas de cada subagente o wrappers de orquestacion, no editando el prompt de produccion.
