# Guión del vídeo — Phoenix Reflex (3 min)

> **Formato:** narración en voz alta + acotaciones `[PANTALLA: ...]` para lo que se muestra.  
> Graba primero el flujo completo, luego añade voz en postproducción si lo necesitas.  
> Ensaya hasta que cada sección encaje en el tiempo marcado sin pausas.

---

## 00:00 – 00:20 · Tesis

`[PANTALLA: README abierto en el navegador, primera línea visible: "Phoenix Reflex is not a PDF chatbot."]`

> "RAG agents fail silently. They give a weak answer, the user moves on, and the same mistake happens again tomorrow. Phoenix Reflex fixes that: every weak answer becomes a regression test and a prompt candidate. The agent inspects its own output, captures failures, and compares prompt changes — before a human decides whether to promote anything."

`[PANTALLA: desplaza suavemente el README hasta la sección "Arize Track Checklist" para que las casillas ✅ sean visibles al final de la intro — no te detengas, es solo un flash de dos segundos]`

---

## 00:20 – 01:00 · Phantom citation correction

`[PANTALLA: abre la UI en http://127.0.0.1:5173, vista Ask, corpus ya cargado — debe verse "2 documents" o similar en la barra lateral]`

> "I have two legal PDFs pre-loaded: the Spanish Workers' Statute and the Statute of Autonomy for Andalusia. Let me ask a question that forces the model to synthesize across multiple non-adjacent articles."

`[PANTALLA: escribe en el campo de pregunta — lento, que se lea:]`

```
Lista todos los permisos retribuidos a los que tiene derecho un trabajador
según el Estatuto de los Trabajadores, indicando la duración exacta de cada uno.
```

> "I'll send this now."

`[PANTALLA: pulsa Send. Mientras carga, no digas nada — deja que el spinner sea visible dos o tres segundos]`

`[PANTALLA: cuando llega la respuesta, centra el zoom en el panel de métricas. Deben verse estos campos:]`

```json
"phantom_citations_detected_count": 11,
"phantom_citations": [],
"failure_mode": "retrieval",
"faithfulness": { "score": 0.5, "label": "partially_faithful" }
```

> "Eleven phantom citations detected — citation IDs the model invented that don't correspond to any retrieved chunk. But the array is empty. That means the correction loop ran inside the same session and fixed all eleven before this response reached me. The model tried to invent references; the system caught every one."

`[PANTALLA: señala con el cursor primero "phantom_citations_detected_count: 11", luego "phantom_citations: []"]`

> "Faithfulness is 0.5 — the answer is partially grounded. That's enough to trigger the next beat."

---

## 01:00 – 01:30 · La traza en Arize

`[PANTALLA: abre Phoenix/Arize en el navegador, proyecto phoenix-reflex, vista de trazas. Busca la traza de la pregunta anterior — debería ser la más reciente]`

> "Here's the trace for that request in Arize Phoenix."

`[PANTALLA: haz clic en la traza. Muestra el timeline con varios spans — el multi-turn es visible como spans anidados o consecutivos]`

> "You can see the multi-turn structure. The first turn is the model's raw answer. The correction turn fires inside the same ADK session — same session ID, new event. Each turn is a separate span."

`[PANTALLA: haz clic en uno de los spans de corrección. Muestra los atributos. Señala:]`

```
eval.citation_correction_applied = true
eval.phantom_citation_count = 11
```

> "The correction is not a retry from the client. It happens inside the agent session before the response is returned. The user never sees the broken draft."

---

## 01:30 – 02:15 · Improvement case → candidate → experiment

`[PANTALLA: vuelve a la UI. El panel de la respuesta anterior debe mostrar un botón o sección "Improvement Case" con estado activo — señálalo]`

> "Because faithfulness is below 0.75, this answer was automatically captured as an improvement case — a regression test."

`[PANTALLA: si la UI muestra el improvement_case inline, señala el campo. Si no, navega a la vista Improvement Cases y muestra el caso recién creado]`

> "Now I generate a candidate prompt from this regression data."

`[PANTALLA: pulsa el botón "Generate Candidate" o llama al endpoint — que se vea la acción]`

`[PANTALLA: cuando responde, muestra el candidate prompt generado — puede ser un texto largo, no hace falta leerlo todo, solo que se vea que es un prompt nuevo]`

> "The system proposes a new prompt optimized against the captured failure. Now I run the experiment to compare it against production."

`[PANTALLA: pulsa "Run Experiment" — que se vea que arranca]`

`[PANTALLA: cuando llega el resultado, centra en la tabla de scores. Deben verse dos filas: production vs candidate, con columnas de faithfulness media y std]`

> "Three runs. Production scores 0.5. Candidate scores…"

`[PANTALLA: señala el score del candidate — sea cual sea, coméntalo]`

> "…and here is the key part."

`[PANTALLA: señala el campo should_promote_to_staging]`

> "The system gives a recommendation, but it does not promote automatically. A human runs promote_tag.py to advance any prompt to staging. No blind auto-promotion."

---

## 02:15 – 02:50 · Beat MCP

`[PANTALLA: vuelve a la UI, vista Ask. Asegúrate de que el toggle MCP está activo — debe verse "MCP: enabled" o similar]`

> "Last beat. Phoenix Reflex can inspect its own operational traces at runtime through Phoenix MCP."

`[PANTALLA: escribe en el campo de pregunta:]`

```
What failed in the latest traces, and what improvement should we make next?
```

`[PANTALLA: pulsa Send]`

`[PANTALLA: cuando llega la respuesta, centra en:]`

```json
"phoenix_mcp_called": true,
"phoenix_mcp_call_count": 1,
"mcp_action": { "status": "created", ... }
```

> "The agent called Phoenix MCP, retrieved the latest failure spans, and created a new improvement case from what it found — without me specifying which trace to look at."

`[PANTALLA: si mcp_action.status es "no_action" porque no había trazas de fallo nuevas, di:]`
> "No new failure traces since the last run — so no duplicate case is created. The system only acts when there is something actionable."

`[PANTALLA: señala el campo phoenix_mcp_tools con los nombres de las herramientas llamadas]`

> "The MCP tool calls are visible in the response and in the trace span."

---

## 02:50 – 03:00 · Cierre

`[PANTALLA: vuelve al README en el navegador, sección "Arize Track Checklist" — todas las filas deben mostrar ✅]`

> "Code-owned runtime. OpenInference instrumentation. Phoenix tracing. Phoenix MCP. LLM-as-judge. And observability data driving continuous improvement — with a human in the loop for every promotion. That's Phoenix Reflex."

`[PANTALLA: mantén el checklist visible hasta que cortes]`

---

## Notas de producción

**Antes de grabar:**
1. Lanza backend: `uvicorn phoenix_reflex.main:app --reload --port 8080`
2. Lanza frontend: `cd frontend && npm run dev`
3. Verifica que el corpus está cargado: `GET /documents` debe devolver 2 docs. Si no, el auto-seed arranca en el primer request.
4. Pre-genera 2–3 respuestas infieles para poblar trazas en Arize antes del beat MCP:
   ```
   ¿Cuáles son las últimas respuestas fallidas del agente según las trazas de Phoenix?
   ```
   Lanza esta pregunta 2 veces desde la UI antes de empezar a grabar.
5. Prewarm del MCP: `npx -y @arizeai/phoenix-mcp@latest --help`
6. Verifica readiness: `GET /observability/mcp` → `demo_ready: true`
7. Ten `demo-assets/` abierto en una carpeta por si necesitas mostrar una traza de backup.

**Si algo falla en vivo:**
- `phantom_citations: []` vacío pero `detected_count: 0` → la pregunta no disparó el loop; intenta con: *"Lista todos los artículos del ET sobre extinción del contrato indicando el número exacto de artículo y apartado."*
- MCP devuelve `no_action` → muéstralo como honestidad del sistema y señala el caso `created` que tienes en `demo-assets/`.
- El experimento tarda → reduce a `n_runs=1` si el tiempo aprieta; lo importante es mostrar el campo `should_promote_to_staging`.
