# loop_visible_mission - Requirements

## R1
CUANDO `/ask` termine con `faithfulness.score` menor que `0.75`, el sistema DEBE devolver `improvement_case` no nulo en la respuesta JSON.

## R2
CUANDO `/ask` detecte phantom citations y aplique correccion, el sistema DEBE devolver contadores de deteccion y correccion que permitan reconstruir el paso `correction`.

## R3
CUANDO `/ask` evalue una respuesta, el sistema DEBE devolver `faithfulness`, `document_relevance`, `answer_quality` y `failure_mode` para reconstruir el paso `eval`.

## R4
CUANDO `/ask` cree un improvement case, el sistema DEBE incluir en la respuesta JSON un resumen ordenado del loop con los pasos `correction`, `eval` e `improvement_case`.

## R5
CUANDO el operador pulse `Generate Candidate` despues de un `/ask` con `improvement_case`, la UI DEBE llamar a `/prompts/candidate` sin recargar la pagina.

## R6
CUANDO se genere un candidate prompt desde la UI, el sistema DEBE mostrar el candidate, el numero de casos de regresion usados y un control para ejecutar el experimento.

## R7
CUANDO el operador ejecute el experimento desde la UI, la UI DEBE llamar a `/experiments/prompt` sin recargar la pagina y mostrar `should_promote_to_staging`.

## R8
MIENTRAS el experimento indique `should_promote_to_staging`, el sistema DEBE no llamar a `/prompts/promote` desde este flujo.

## R9
CUANDO la UI muestre el resultado de `/ask`, el sistema DEBE renderizar en la misma vista el panel de correccion, el improvement case y el boton `Generate Candidate`.

## R10
CUANDO se ejecute `pytest`, el sistema DEBE terminar con exit 0.

## R11
CUANDO se ejecute `npm run build` en `frontend/`, el sistema DEBE terminar con exit 0.
