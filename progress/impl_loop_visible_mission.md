# loop_visible_mission - Implementacion

## Estado
Implementacion completada.

## Archivos modificados
- `phoenix_reflex/qa.py`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `tests/test_loop_visible_mission.py`
- `tests/test_retriever_fallback.py`
- `pytest.ini`
- `specs/loop_visible_mission/design.md`
- `specs/loop_visible_mission/tasks.md`

## Cambios
- `/ask` ahora devuelve `loop` con pasos `correction`, `eval` e `improvement_case`.
- `AskView` renderiza el loop visible en la misma pantalla que la respuesta.
- La UI muestra el improvement case capturado y habilita `Generate Candidate` solo cuando hay caso.
- `Generate Candidate` llama a `POST /prompts/candidate` sin recargar.
- `Run Experiment` llama a `POST /experiments/prompt?n_runs=1` sin recargar.
- La UI muestra `should_promote_to_staging` como recomendacion, sin llamar a `/prompts/promote`.
- Se agrego `pytest.ini` para que `pytest` literal encuentre el paquete local.
- Tras smoke test, `AskView` captura errores de `/ask`, `/prompts/candidate` y `/experiments/prompt` para no dejar la UI bloqueada en estados de carga.
- Tras smoke test, retrieval degrada de `hybrid` a `bm25_fallback` si Gemini embeddings falla por cuota u otro error, evitando 500 en `/ask`.

## Guion de demo
1. Abrir el frontend.
2. En `Documents`, cargar `BOE-A-2015-11430-consolidado.pdf`.
3. En `Documents`, cargar `lo_2-2007.pdf`.
4. En `Ask`, usar preguntas ancladas a los textos:
   - `Segun los PDFs cargados, que texto refundido aprueba el Real Decreto Legislativo 2/2015 y que reforma la Ley Organica 2/2007?`
   - `Segun el Estatuto de los Trabajadores, que articulos tratan derechos laborales, jornada, vacaciones anuales y extincion del contrato?`
   - `Segun el Estatuto de Autonomia para Andalucia, como define el articulo 1 a Andalucia y de donde emanan sus poderes?`
   - `Segun estos PDFs, cual es el plazo exacto para renovar el DNI electronico?`
   - `Que dice el Estatuto de los Trabajadores sobre la jornada y que plazo da para renovar el DNI electronico?`
5. Cuando `/ask` capture `improvement_case`, pulsar `Generate Candidate`.
6. Tras generar candidato, pulsar `Run Experiment`.
7. Leer `should_promote_to_staging` como decision recomendada; no hay promocion automatica.

## Verificacion
- `pytest` -> 12 passed.
- `npm run build` en `frontend/` -> exit 0.
- Re-verificacion tras fix de errores UI: `npm run build` en `frontend/` -> exit 0.
- Re-verificacion tras fallback BM25: `pytest` -> 13 passed.
- Re-verificacion tras fallback BM25: `npm run build` en `frontend/` -> exit 0.
