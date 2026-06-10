# loop_visible_mission - Review

## Veredicto
APPROVED

## Trazabilidad
- R1: cubierto por `tests/test_loop_visible_mission.py::test_ask_returns_improvement_case_when_faithfulness_low`.
- R2: cubierto por `loop.correction` en `phoenix_reflex/qa.py` y `test_loop_summary_includes_correction_step`.
- R3: cubierto por `loop.eval` en `phoenix_reflex/qa.py` y `test_loop_summary_includes_eval_step`.
- R4: cubierto por `loop.steps` y `loop.improvement_case` en `/ask`.
- R5: `AskView` llama a `POST /prompts/candidate` desde `Generate Candidate` sin recargar.
- R6: `AskView` muestra version de candidate, prompt y numero de casos de regresion.
- R7: `AskView` llama a `POST /experiments/prompt?n_runs=1` y muestra `should_promote_to_staging`.
- R8: el flujo de `AskView` no llama a `/prompts/promote`.
- R9: el panel `Regression loop` renderiza correccion, improvement case y `Generate Candidate` en la vista `/ask`.
- R10: `pytest` termina con exit 0.
- R11: `npm run build` en `frontend/` termina con exit 0.

## Verificacion
- `pytest` -> 12 passed.
- `npm run build` en `frontend/` -> exit 0.
- `rg "/prompts/promote|promote_prompt|promote" frontend/src/main.tsx` confirma ausencia de llamada al endpoint de promocion; solo hay texto/estado de recomendacion.
- Re-verificacion tras smoke issue: `npm run build` en `frontend/` -> exit 0.
- Re-verificacion tras 429 de embeddings: `pytest` -> 13 passed.
- Re-verificacion tras 429 de embeddings: `npm run build` en `frontend/` -> exit 0.

## Riesgo residual
- Smoke test manual detecto que la UI podia quedarse en estado `Asking` si `/ask` devolvia error. Se corrigio mostrando el error en la barra de estado.
- Smoke test manual detecto `429 RESOURCE_EXHAUSTED` en embeddings de Gemini. Se corrigio retrieval para caer a BM25 cuando falla semantic retrieval.
- Queda pendiente repetir smoke test humano antes de marcar `done`.
