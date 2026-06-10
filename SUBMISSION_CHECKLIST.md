# Submission Checklist — Hackathon Arize

Lo que queda son tareas de persona, no de código. En orden de impacto.

---

## P0 — Sin esto no puntúas

- [ ] **Verificar repo público en GitHub.** Abre el repo y confirma que aparece "MIT License" en la cabecera (GitHub lo detecta automáticamente del archivo LICENSE). Si no aparece, comprueba que el fichero tiene exactamente el encabezado estándar MIT.

- [ ] **Verificar URL pública responde.** `GET https://phoenix-reflex-27208039935.europe-west1.run.app/health` debe devolver `{"status":"ok"}`. El corpus de demo se auto-carga en el primer arranque (seed_corpus implementado), así que las tres preguntas de "Try it in 60 seconds" del README deben funcionar sin upload manual.

- [ ] **Subir `min-instances` a 1 durante la ventana de evaluación.** Con `min-instances=0` el juez puede toparse con un cold start de 20–30s. Edita `scripts/deploy-cloud-run.ps1` → cambia `--min-instances 0` a `--min-instances 1` y redespliega solo para esos días. Recuerda bajarlo después para no gastar créditos.

- [ ] **Grabar el vídeo de 3 minutos.** Guion en `DEMO.md`. Timings sugeridos:
  - 0:00–0:20 Tesis ("not a PDF chatbot…")
  - 0:20–1:00 Phantom citation correction en vivo (pregunta de permisos retribuidos → 11 detected / 11 corrected)
  - 1:00–1:30 Traza en Arize/Phoenix mostrando timeline multi-turn
  - 1:30–2:15 Improvement case → Generate Candidate → Run Experiment → `should_promote`
  - 2:15–2:50 Beat MCP (`phoenix_mcp_called: true`, `mcp_action`)
  - 2:50–3:00 Checklist de rúbrica en pantalla

- [ ] **Sembrar trazas con fallos antes de grabar el beat MCP.** El smoke test A1 dio `no_action` porque Phoenix tenía trazas vacías. Antes de grabar, lanza 2–3 preguntas que produzcan `failure_mode != none` para que el agente encuentre trazas reales y muestre `mcp_action.status: "created"`. Si no lo consigues de forma fiable, muestra el `no_action` honestamente pero ten la sesión `created` capturada en `demo-assets/` lista como evidencia.

---

## P1 — Material de submission

- [ ] **Texto de Devpost.** Estructura en tres párrafos:
  1. Problema: los agentes RAG fallan en silencio y repiten errores.
  2. Solución: Phoenix Reflex convierte fallos observados en regression cases y experimentos de prompt.
  3. Diferenciador: usa sus propias trazas y evaluaciones para mejorar prompts con promoción humana; nunca autopromueve.
  
  Incluye la URL pública, el repo, y menciona explícitamente: Google ADK 2.x, OpenInference, Phoenix tracing, Phoenix MCP, LLM-as-judge, Gemini 3.5 Flash.

- [ ] **Capturas obligatorias para Devpost** (sácalas durante el dry run del vídeo para no hacer doble sesión):
  - UI con pregunta / respuesta / citas
  - Trace en Arize con el correction loop (`eval.citation_correction_applied`)
  - Panel de Improvement Cases
  - Tabla de Prompt Experiment (production vs candidate scores)
  - Beat MCP: respuesta con `phoenix_mcp_called: true`

- [ ] **Respuesta preparada sobre Agent Builder.** Si el juez pregunta: "Phoenix Reflex usa Google ADK 2.x, el framework open-source y code-first del mismo stack de Agent Builder. El runtime propio es una elección deliberada: es la única forma de adjuntar instrumentación OpenInference y emitir los atributos `eval.*` por span que requiere el track Arize. El deploy corre en Cloud Run con Gemini 3.5 Flash, 100% dentro del ecosistema Google Cloud."

---

## P2 — Solo si sobra tiempo

- [ ] Dry run cronometrado antes de la grabación final. Límite estricto: 3 minutos. Corta todo lo que no pruebe rúbrica o diferenciador.
- [ ] Mini vista "Human Review" en la UI (ya está en feature list como P3 — no implementar si pone en riesgo la estabilidad).
- [ ] Feature 11 (`frontend_multi_agent_toggle`) — dejarla en `pending`. El toggle no añade puntos de rúbrica y sí riesgo de regresión.

---

## Estado del repo al cerrar esta sesión

| Item | Estado |
| --- | --- |
| PDFs de demo en repo | ✅ (*.pdf eliminado de .gitignore) |
| Auto-seed corpus en startup | ✅ (lifespan en main.py) |
| Trace-session JSONs en demo-assets/ | ✅ |
| Arize Track Checklist en README | ✅ |
| Try it in 60 seconds en README | ✅ |
| Párrafo Agent Builder en README | ✅ |
| Tests | ✅ 43 passed |
| Cloud Run URL | ✅ europe-west1.run.app |
