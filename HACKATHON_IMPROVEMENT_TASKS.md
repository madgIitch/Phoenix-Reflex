# Hackathon Improvement Tasks

Objetivo: subir Phoenix Reflex de una submission tecnicamente fuerte a una submission facil de puntuar alto por la rubrica de Arize. La prioridad no es perfeccionar el producto; es cerrar requisitos explicitos, hacer visible el loop de auto-mejora y reducir dudas del juez.

## P0 - Cerrar Rubrica Antes Del Submit

- [x] Encender Phoenix MCP en la demo.
  - Riesgo actual: `ENABLE_PHOENIX_MCP=0` puede hacer que un juez marque el requisito MCP como no cumplido.
  - Resultado esperado: el agente puede consultar datos operativos via Phoenix MCP durante runtime.
  - Demo minima: preguntar algo como "que fallo en las ultimas trazas?" y mostrar una tool MCP consultando trazas o spans.
  - Evidencia a mostrar: llamada MCP visible, datos de traza usados por el agente y respuesta que conecte esos datos con una mejora.

- [x] Actualizar el modelo por defecto a Gemini 3.
  - Resultado actual: README, defaults, deploy y `.env.example` apuntan a `gemini-3.5-flash`.
  - Resultado esperado: `.env.example`, documentacion y codigo usan el modelo Gemini 3 disponible para la region/proyecto.
  - Verificacion: correr una pregunta `/ask`, generar un candidate prompt y ejecutar un experimento corto.

- [x] Preparar validacion humana del judge.
  - Riesgo actual: la narrativa depende de "Gemini judging Gemini", que es el agujero tecnico mas facil de atacar.
  - Resultado esperado: una slide o seccion del README con una muestra de trazas revisadas manualmente.
  - Formato recomendado: 5-10 casos, score del judge, veredicto humano, acuerdo/desacuerdo y notas.
  - Mensaje clave: el judge no promueve automaticamente; solo prioriza casos y la promocion sigue siendo manual.

- [x] Reposicionar el producto como agente de regression cases, no como PDF chatbot.
  - Resultado actual: README y DEMO abren con Phoenix Reflex como agente regression-driven, no chatbot PDF.
  - Frase de apertura: "Phoenix Reflex is not a PDF chatbot; it is a regression-driven agent that turns its own weak answers into test cases and prompt candidates."
  - Todo el material de submit debe repetir esta idea: README, Devpost, video y demo script.

## P1 - Video De 3 Minutos

- [ ] Abrir el video con la tesis en los primeros 20 segundos.
  - Decir: el agente no solo responde; inspecciona sus fallos, crea regression cases, propone prompts y deja promocion al humano.
  - Evitar empezar con arquitectura, setup local o upload de PDFs.

- [ ] Mostrar el beat de phantom citation correction.
  - Accion: hacer una pregunta densa que fuerce o muestre correccion de cita inventada.
  - Evidencia: `phantom_citations_detected_count > 0`, `phantom_citations: []`, `failure_mode: "none"`.
  - Evidencia extra: trace con `eval.citation_correction_applied = true` y `eval.phantom_citation_count`.

- [ ] Mostrar la traza como prueba de comportamiento agentic.
  - Accion: abrir Phoenix/Arize y ensenar el timeline multi-turn.
  - Mensaje: la correccion ocurre dentro de la misma sesion antes de responder al usuario.

- [ ] Mostrar generation de improvement case.
  - Accion: hacer una pregunta parcialmente soportada o usar un caso ya preparado.
  - Evidencia: endpoint o UI con el `improvement_case` creado.
  - Mensaje: una respuesta debil se convierte en regression data reutilizable.

- [ ] Mostrar candidate prompt vs production.
  - Accion: llamar `/prompts/candidate` y luego `/experiments/prompt?n_runs=3`.
  - Evidencia: tabla con scores production vs candidate.
  - Mensaje: el sistema compara cambios antes de promover.

- [ ] Mostrar promocion manual a staging.
  - Accion: ejecutar o ensenar `scripts/promote_tag.py`.
  - Mensaje: no hay autopromocion ciega; el humano revisa y decide.

## P1 - Material De Submission

- [ ] Ajustar README para que la primera pantalla venda el loop de auto-mejora.
  - Incluir una frase fuerte arriba: "weak answers become regression cases, prompt candidates, and scored experiments."
  - Mencionar explicitamente OpenInference, Phoenix tracing, Phoenix MCP y LLM-as-judge.

- [ ] Crear una seccion "Arize Track Checklist".
  - [ ] Code-owned runtime.
  - [ ] OpenInference instrumentation.
  - [ ] Phoenix tracing.
  - [ ] Phoenix MCP runtime introspection.
  - [ ] LLM-as-judge evaluation.
  - [ ] Bonus: agent uses observability data to improve over time.

- [ ] Preparar texto corto para Devpost.
  - Problema: los RAG fallan de forma silenciosa y repiten errores.
  - Solucion: Phoenix Reflex convierte fallos observados en regression cases y experimentos.
  - Diferenciador: usa sus propias trazas y evaluaciones para mejorar prompts con promocion humana.

- [ ] Preparar capturas obligatorias.
  - UI con pregunta/respuesta/citas.
  - Trace con correction loop.
  - Improvement cases.
  - Prompt experiment production vs candidate.
  - Phoenix MCP introspection.

## P1 - Despliegue Para El Juez

- [ ] Desplegar a Cloud Run (Opcion A).
  - Riesgo actual: el juez clona el repo pero `.env` esta en `.gitignore`; sin claves el agente no arranca y la demo MCP no funciona.
  - Resultado esperado: una URL publica funcional donde el juez puede mandar preguntas sin instalar nada.
  - Pasos:
    - [ ] Hacer build y push de la imagen Docker a Google Artifact Registry.
    - [ ] Crear servicio Cloud Run con las variables de entorno configuradas en el panel (no en el repo): `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, `ENABLE_PHOENIX_MCP`, `PHOENIX_HOST`, `PHOENIX_API_KEY`, `ARIZE_API_KEY`, `ARIZE_SPACE_ID`, `ARIZE_PROJECT_NAME`, `ARIZE_OTEL_ENDPOINT`.
    - [ ] Verificar que `GET /health` devuelve 200 desde la URL publica.
    - [ ] Verificar que `GET /observability/mcp` devuelve `demo_ready: true`.
    - [ ] Anadir la URL publica al README como primera linea de "Local Run" o en una seccion "Live Demo".
  - Mensaje clave: el juez no debe necesitar Python, npm ni ningun fichero local para evaluar la funcionalidad principal.

## P2 - Robustez Tecnica Para La Demo

- [ ] Preparar un PDF y preguntas de demo fijas.
  - No improvisar con un PDF nuevo durante la grabacion.
  - Tener una pregunta soportada, una parcialmente soportada y una que tienda a provocar phantom citations.

- [ ] Precomputar embeddings antes de grabar.
  - Comando: `py scripts/precompute_embeddings.py`.
  - Objetivo: evitar esperas o fallos por latencia durante el video.

- [ ] Guardar trazas buenas antes de grabar.
  - Objetivo: si una ejecucion live no dispara el caso ideal, tener evidencia reciente lista para mostrar.
  - Archivo de apoyo: export JSON de trazas con correction loop e improvement cases.

- [ ] Hacer un dry run cronometrado del video.
  - Limite: 3 minutos.
  - Cortar todo lo que no pruebe rubrica o diferenciador.

- [ ] Verificar comandos de demo en limpio.
  - Backend: `uvicorn phoenix_reflex.main:app --reload --port 8080`.
  - Frontend: `cd frontend` y `npm run dev`.
  - Health: `http://localhost:8080/health`.
  - UI: `http://127.0.0.1:5173`.

## P2 - Reducir Objeciones De Jueces

- [ ] Preparar respuesta sobre Agent Builder.
  - Riesgo: el brief general menciona Google Cloud Agent Builder.
  - Respuesta: el track Arize requiere code-owned runtime para tracing e instrumentation; Phoenix Reflex usa runtime propio precisamente para cumplir esa parte.

- [ ] Preparar respuesta sobre LLM-as-judge.
  - Respuesta: el judge es deterministic, tiene rubrica explicita, crea senales para priorizacion y no promueve cambios sin revision humana.
  - Mostrar la validacion humana como mitigacion.

- [ ] Preparar respuesta sobre "es solo RAG".
  - Respuesta: el RAG es el entorno donde se observan fallos; el producto principal es el loop regression-driven de mejora continua.
  - Evidencia: improvement cases, prompt candidates, experiments y manual promotion.

- [ ] Preparar respuesta sobre fallos honestos.
  - Respuesta: si una cita inventada no se corrige tras dos intentos, el sistema lo expone como `failure_mode` en vez de ocultarlo.
  - Mensaje: observabilidad y control antes que falsa confianza.

## P3 - Mejoras Si Queda Tiempo

- [ ] Anadir una mini vista de "Human Review" en la UI.
  - Mostrar casos, score del judge, decision humana y notas.
  - No necesita ser complejo; basta con hacer visible que el humano esta en el loop.

- [ ] Anadir un endpoint/resumen de "rubric evidence".
  - Devolver estado de tracing, MCP, modelo, evaluadores y ultimos experimentos.
  - Util para demo y para jueces tecnicos.

- [ ] Mejorar `answer_quality`.
  - Actualmente es demo-grade.
  - Prioridad baja salvo que el video dependa de esa metrica.

- [ ] Anadir una segunda familia de judge o modo cross-check.
  - Mitiga la critica de auto-evaluacion con el mismo modelo.
  - Solo hacerlo si no pone en riesgo estabilidad de la demo.

## Orden Recomendado

1. Encender y demostrar Phoenix MCP.
2. Cambiar defaults/documentacion a Gemini 3 y verificar flujo minimo.
3. Preparar validacion humana en una slide o tabla.
4. Reescribir pitch/README/Devpost alrededor de "regression-driven self-improvement".
5. Grabar dry run de 3 minutos.
6. Pulir solo lo que haga mas clara la demo.

## Criterio De Exito

La submission debe permitir a un juez marcar estas casillas sin inferir nada:

- El agente corre en runtime propio.
- Tiene instrumentation OpenInference.
- Emite trazas Phoenix/Arize.
- Usa Phoenix MCP para introspeccion runtime.
- Evalua con LLM-as-judge.
- Usa datos de observabilidad para generar regression cases y mejorar prompts.
- La promocion de cambios queda bajo control humano.
