# loop_visible_mission - Design

## Objetivo
Hacer visible el loop principal de Phoenix Reflex en una sola demo operable desde el frontend: una respuesta debil pasa por correccion, evaluacion, captura de improvement case, generacion de candidate prompt y experimento. La decision final queda human-in-the-loop: la app puede recomendar promocion, pero no promociona automaticamente.

## Corpus de demo
La demo debe ejecutarse desde el frontend usando los dos PDFs juridicos disponibles en la raiz del repo y cargados desde la vista `Documents`:

- `BOE-A-2015-11430-consolidado.pdf`
- `lo_2-2007.pdf`

El objetivo del corpus es mezclar normativa laboral estatal con una ley organica estatutaria autonomica para que el operador pueda demostrar respuestas soportadas, abstenciones y fallos de mezcla entre documentos. Para fines juridicos se debe consultar siempre la publicacion oficial, no la salida del agente.

Contenido base verificado localmente:

- `BOE-A-2015-11430-consolidado.pdf` contiene el Real Decreto Legislativo 2/2015, de 23 de octubre, por el que se aprueba el texto refundido de la Ley del Estatuto de los Trabajadores.
- `lo_2-2007.pdf` contiene la Ley Organica 2/2007, de 19 de marzo, de reforma del Estatuto de Autonomia para Andalucia.

Preguntas utiles para forzar el loop:

- Pregunta answerable: `Segun los PDFs cargados, que texto refundido aprueba el Real Decreto Legislativo 2/2015 y que reforma la Ley Organica 2/2007?`
- Pregunta answerable: `Segun el Estatuto de los Trabajadores, que articulos tratan derechos laborales, jornada, vacaciones anuales y extincion del contrato?`
- Pregunta answerable: `Segun el Estatuto de Autonomia para Andalucia, como define el articulo 1 a Andalucia y de donde emanan sus poderes?`
- Pregunta de abstencion: `Segun estos PDFs, cual es el plazo exacto para renovar el DNI electronico?`
- Pregunta mixta: `Que dice el Estatuto de los Trabajadores sobre la jornada y que plazo da para renovar el DNI electronico?`
- Pregunta de mezcla: `Compara el ambito laboral del Estatuto de los Trabajadores con el autogobierno andaluz de la Ley Organica 2/2007 sin usar informacion externa.`

## Archivos a crear o modificar
- `phoenix_reflex/qa.py` - anadir un resumen estructurado del loop en la respuesta de `/ask`.
- `frontend/src/main.tsx` - extender tipos y UI de `AskView` para mostrar improvement case, candidate prompt y experimento sin cambiar de pagina; esta vista sera la superficie principal de demo.
- `frontend/src/styles.css` - estilos para el panel del loop visible si la UI lo requiere.
- `tests/test_loop_visible_mission.py` - tests backend para respuesta `/ask` con improvement case y loop summary.
- `pytest.ini` - configura `pythonpath = .` para que `pytest` literal encuentre el paquete local.
- `BOE-A-2015-11430-consolidado.pdf` - corpus juridico de demo, cargado manualmente desde el frontend.
- `lo_2-2007.pdf` - corpus juridico de demo, cargado manualmente desde el frontend.
- `frontend` build - verificacion TypeScript/Vite.
- `progress/impl_loop_visible_mission.md` - reporte del implementer cuando se ejecute la implementacion.
- `progress/review_loop_visible_mission.md` - veredicto del reviewer cuando se revise la implementacion.

No se debe modificar `phoenix_reflex_agent/agent.py`. Esta feature no requiere tocar `PRODUCTION_PROMPT`; usa endpoints y telemetria existentes.

## Firmas y funciones
Funciones previstas:

```python
def _build_loop_summary(
    *,
    correction_rounds: int,
    phantom_citations_detected_count: int,
    phantom_citations_corrected_count: int,
    style_correction_applied: bool,
    faithfulness: dict[str, object],
    document_relevance: dict[str, object],
    answer_quality: dict[str, object],
    failure_mode: str,
    improvement_case: dict[str, object] | None,
) -> dict[str, object]: ...
```

Cambios previstos en la respuesta de `ask_agent(question)`:

```python
{
    "loop": {
        "steps": ["correction", "eval", "improvement_case"],
        "correction": {...},
        "eval": {...},
        "improvement_case": {...} | None,
    },
    ...
}
```

Tipos previstos en frontend:

```ts
type LoopSummary = {
  steps: string[];
  correction: {
    attempted: boolean;
    rounds: number;
    phantom_citations_detected_count: number;
    phantom_citations_corrected_count: number;
    style_correction_applied: boolean;
  };
  eval: {
    faithfulness?: AskResponse['faithfulness'];
    document_relevance?: AskResponse['document_relevance'];
    answer_quality?: AskResponse['answer_quality'];
    failure_mode?: string;
  };
  improvement_case: ImprovementCase | null;
};
```

El frontend debe reutilizar los endpoints existentes:

```txt
POST /prompts/candidate
POST /experiments/prompt?n_runs=1
```

El flujo no debe llamar a:

```txt
POST /prompts/promote
```

## Dependencias previstas
- Sin paquetes Python nuevos.
- Sin paquetes npm nuevos.
- Sin cambios en dependencias; `pytest.ini` solo fija el import path local para tests.
- Tests backend con mocks sin red para `Runner.run_async`, evaluadores y `maybe_create_improvement_case`.
- El build frontend debe usar la configuracion existente de Vite/TypeScript.

## Tests y trazabilidad
- R1 -> `tests/test_loop_visible_mission.py::test_ask_returns_improvement_case_when_faithfulness_low`
- R2 -> `tests/test_loop_visible_mission.py::test_loop_summary_includes_correction_step`
- R3 -> `tests/test_loop_visible_mission.py::test_loop_summary_includes_eval_step`
- R4 -> `tests/test_loop_visible_mission.py::test_loop_summary_includes_improvement_case_step`
- R5 -> `npm run build` y revision de `AskView` con handler `generateCandidate`
- R6 -> `npm run build` y revision de render de candidate result
- R7 -> `npm run build` y revision de handler `runExperiment`
- R8 -> `npm run build` y ausencia de llamada a `/prompts/promote` en el flujo de `AskView`
- R9 -> `npm run build` y render condicional en `AskView`
- R10 -> `pytest`
- R11 -> `npm run build` en `frontend/`

## Alternativa descartada
Se descarta crear un endpoint monolitico que ejecute `/ask`, `/prompts/candidate` y `/experiments/prompt` en una sola llamada porque mezclaria una respuesta al usuario con operaciones caras y controladas por el operador. La demo necesita mostrar el encadenamiento en una sola pantalla del frontend, pero la promocion y los experimentos deben seguir siendo acciones explicitas.

Se descarta promocionar automaticamente el candidate cuando `should_promote_to_staging` sea verdadero porque las reglas del proyecto mantienen el cambio de prompt bajo control humano.
