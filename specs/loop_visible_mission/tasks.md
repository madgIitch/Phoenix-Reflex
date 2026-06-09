# loop_visible_mission - Tasks

- [x] T1 - Crear `_build_loop_summary()` en `phoenix_reflex/qa.py` y anadir `loop` a la respuesta de `ask_agent()`. Cubre: R2, R3, R4.
- [x] T2 - Asegurar que `improvement_case` sigue siendo no nulo cuando `faithfulness.score < 0.75` y documentar el caso en tests. Cubre: R1.
- [x] T3 - Escribir `tests/test_loop_visible_mission.py` con mocks sin red para low faithfulness, correction summary, eval summary e improvement case summary. Cubre: R1, R2, R3, R4.
- [x] T4 - Extender los tipos de `frontend/src/main.tsx` para `improvement_case`, `loop`, candidate prompt y resultado de experimento. Cubre: R5, R6, R7, R9.
- [x] T5 - Actualizar `AskView` para renderizar correction panel, improvement case y boton `Generate Candidate` en la misma vista despues de `/ask`. Cubre: R5, R9.
- [x] T6 - Implementar handlers frontend para `POST /prompts/candidate` y `POST /experiments/prompt?n_runs=1` sin recargar la pagina. Cubre: R5, R6, R7.
- [x] T7 - Mostrar `should_promote_to_staging` como decision recomendada sin invocar `/prompts/promote`. Cubre: R8.
- [x] T8 - Ajustar `frontend/src/styles.css` solo si hace falta para que el loop visible sea legible y no rompa layout. Cubre: R9.
- [x] T9 - Preparar en `progress/impl_loop_visible_mission.md` el guion de demo usando el frontend y los PDFs juridicos `BOE-A-2015-11430-consolidado.pdf` y `lo_2-2007.pdf`. Cubre: R5, R6, R7, R8, R9.
- [x] T10 - Ejecutar `pytest` y documentar resultado en `progress/impl_loop_visible_mission.md`. Cubre: R10.
- [x] T11 - Ejecutar `npm run build` en `frontend/` y documentar resultado en `progress/impl_loop_visible_mission.md`. Cubre: R11.
