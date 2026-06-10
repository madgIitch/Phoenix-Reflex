# multi_agent_adk - Tasks

- [x] T0 - Ejecutar `pip index versions google-adk` y confirmar que existe una version `>=2.0.0` publicada. Si no existe, documentar bloqueo en `progress/impl_multi_agent_adk.md` y detener. Cubre: R1.
- [x] T1 - Actualizar `requirements.txt` a `google-adk>=2.0.0,<3.0.0`. Ejecutar `pip install -r requirements.txt` y verificar que `openinference-instrumentation-google-adk` instala sin conflicto; si falla, pinear version compatible y documentar. Cubre: R2, R2b, R11.
- [x] T2 - Extraer en `phoenix_reflex_agent/agent.py` una factory `build_single_agent()` que preserve el `root_agent` actual y no modifique `PRODUCTION_PROMPT`. Cubre: R3, R6.
- [x] T3 - Crear `phoenix_reflex_agent/multi_agent.py` con `is_multi_agent_enabled()`, `build_single_agent()` (delegando a agent.py), `build_multi_agent()` y `build_root_agent()`. Definir la constante `COORDINATOR_INSTRUCTION` segun el texto del design. Cubre: R3, R3b, R6, R7, R9.
- [x] T4 - Definir en `build_multi_agent()` un coordinador QA (con `COORDINATOR_INSTRUCTION`), un judge subagent con instruccion explicita de producir `faithfulness/document_relevance/answer_quality/failure_mode`, y un improvement subagent con instruccion de crear improvement cases usando reglas de `reflex.py`. Cubre: R3, R4, R5.
- [x] T5 - En `phoenix_reflex/qa.py` reemplazar la referencia directa a `root_agent` por una llamada a `build_root_agent()` importada de `multi_agent`. Este es el unico punto de integracion del flag en `qa.py`. Cubre: R3b, R6, R9.
- [x] T6 - Integrar fallback automatico en `build_root_agent()`: si `build_multi_agent()` lanza excepcion, loggear y retornar `build_single_agent()`. Cubre: R9.
- [x] T7 - Escribir `tests/test_multi_agent_adk.py` cubriendo: version ADK 2.x en requirements, factory single-agent preserva export, builder define judge y improvement con instrucciones no vacias, modo default usa single-agent, flag construye multi-agent sin mutar PRODUCTION_PROMPT, contrato JSON estable en ambos modos, fallback ante fallo del builder. Cubre: R2, R3, R4, R5, R6, R7, R8, R9.
- [x] T8 - Ejecutar `pytest` y documentar resultado en `progress/impl_multi_agent_adk.md`. Cubre: R10.
- [x] T9 - Ejecutar `python -c "import phoenix_reflex; import phoenix_reflex_agent"` y documentar resultado en `progress/impl_multi_agent_adk.md`. Cubre: R11.
- [x] T10 - Ejecutar `.\init.ps1` y documentar resultado en `progress/impl_multi_agent_adk.md`. Cubre: R12.
