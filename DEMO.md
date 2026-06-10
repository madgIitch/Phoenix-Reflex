# Phoenix Reflex Demo

Open with the product thesis: Phoenix Reflex is not a PDF chatbot. It is a
regression-driven agent for RAG systems that fail silently and repeat mistakes.
In the demo, weak answers become test cases and prompt candidates under human
control.

Use any text-based PDF with content you can inspect and verify. The demo should show the improvement loop, not a case-specific script:

1. Upload or select a prepared PDF as the failure surface for the agent.
2. Ask a question that is directly supported by enabled chunks.
3. Ask a question that is only partially supported so the system can expose a weak answer.
4. **Show the in-session correction loop** (see section below — this is the agentic highlight).
5. Show faithfulness, document relevance, answer quality, and retrieved citations.
6. Show the weak answer becoming an improvement case / regression test.
7. Generate a candidate prompt and run the prompt experiment.

## Demo Corpus & Script Questions

Upload both PDFs before starting:

| PDF                                  | Contenido                                          |
|--------------------------------------|----------------------------------------------------|
| `BOE-A-2015-11430-consolidado.pdf`   | Estatuto de los Trabajadores (RDL 2/2015)          |
| `lo_2-2007.pdf`                      | Estatuto de Autonomía para Andalucía (LO 2/2007)   |

### Paso 2 — Pregunta con respuesta bien soportada (faithfulness 1.0, relevance 1.0)

Demuestra que el sistema funciona correctamente cuando los chunks son correctos.

```text
¿Cuántas horas semanales fija el Estatuto de los Trabajadores como jornada ordinaria máxima?
```

Respuesta esperada: 40 horas semanales (Art. 34). Retriever encuentra el chunk exacto.

```text
Según el Estatuto de Autonomía para Andalucía, ¿cómo define el artículo 1 a Andalucía y de dónde emanan sus poderes?
```

Respuesta esperada: nacionalidad histórica, poderes emanan de la Constitución y del pueblo andaluz (Art. 1 LO 2/2007).

### Paso 3 — Pregunta fuera del corpus (abstención correcta)

Demuestra que el sistema no inventa cuando la información no está.

```text
¿Cuál es el plazo exacto para renovar el DNI electrónico?
```

Respuesta esperada: el sistema indica que los documentos no contienen esa información. `failure_mode: none`, `document_relevance: 0`.

### Paso 4 — Pregunta que dispara el loop de corrección ⭐

Esta es la pregunta de la demo principal. Produce `faithfulness: 0.5`, `failure_mode: "retrieval"` y genera `improvement_case`.

```text
Lista todos los permisos retribuidos a los que tiene derecho un trabajador según el Estatuto de los Trabajadores, indicando la duración exacta de cada uno.
```

Por qué falla: el retriever recupera chunks de conciliación y vacaciones (Art. 37-38) pero no el Art. 37.3 con la lista completa de permisos y sus días exactos. El agente referencia artículos no presentes en el contexto → juez: `partially_faithful`. Señales visibles en la respuesta:

```json
{
  "faithfulness": { "score": 0.5, "label": "partially_faithful" },
  "failure_mode": "retrieval",
  "phantom_citations_detected_count": 11,
  "phantom_citations_corrected_count": 11,
  "event_count": 38
}
```

El alto `event_count` y los 11 phantom citations corregidos hacen esta sesión especialmente rica para mostrar en el trace de Phoenix/Arize.

---

## Showing the In-Session Correction Loop

This is the most distinctive part of the system and should not be skipped.

**What to say:** "The agent doesn't just answer — it inspects its own output before returning it. If it invented a citation ID that doesn't match any retrieved chunk, the system catches it and sends a correction turn back to the same session, up to twice. Only the final, verified answer reaches the user."

**What to show:** After any `/ask` call, point to these fields in the JSON response:

```json
{
  "phantom_citations_detected_count": 1,
  "phantom_citations": [],
  "failure_mode": "none"
}
```

- `phantom_citations_detected_count: 1` + empty `phantom_citations` → loop fired and fixed an invented citation
- `phantom_citations_detected_count: 0` → the model was clean on first pass
- Non-empty `phantom_citations` → correction ran twice and still failed (rare; worth showing as an honest failure mode)

**How to trigger it reliably:** Ask a question that references specific details across multiple chunks simultaneously. Dense cross-chunk questions are where small models are most likely to hallucinate citation IDs.

**OTel evidence:** In the Phoenix/Arize trace, look for spans with `eval.citation_correction_applied = true` and `eval.phantom_citation_count`. Each correction turn increments `qa.event_count`, making the multi-turn nature visible in the trace timeline.

## Phoenix MCP Demo Beat

This is the rubric checkbox that proves the agent can inspect operational data at runtime through Phoenix MCP.

Prewarm the MCP server package before recording so the demo does not pause on the first `npx` download:

```powershell
npx -y @arizeai/phoenix-mcp@latest --help
```

Configure Phoenix Cloud credentials:

```env
ENABLE_PHOENIX_MCP=1
PHOENIX_HOST=https://app.phoenix.arize.com/s/your-space
PHOENIX_API_KEY=px_live_...
```

Verify readiness:

```powershell
Invoke-RestMethod "http://localhost:8080/observability/mcp"
```

Expected demo-ready response fields:

```json
{
  "enabled": true,
  "configured": true,
  "importable": true,
  "demo_ready": true
}
```

Ask the observability question:

```text
What failed in the latest traces, and what improvement should we make next?
```

What to show:

- The MCP tab says `Demo ready: yes`.
- The `/ask` response includes `phoenix_mcp_called: true`, a non-zero `phoenix_mcp_call_count`, and at least one `phoenix_mcp_tools` entry.
- The trace span includes `phoenix_mcp.called = true`.
- The answer connects observed trace failures to a concrete improvement, for example tightening prompt behavior, adding a regression case, or improving retrieval coverage.

## Before The Demo

Precompute embeddings:

```powershell
py scripts/precompute_embeddings.py
```

Start the backend and UI:

```powershell
uvicorn phoenix_reflex.main:app --reload --port 8080
cd frontend
npm run dev
```

Open:

- Backend health: `http://localhost:8080/health`
- UI: `http://127.0.0.1:5173`

## Commands

Inspect improvement cases:

```powershell
Invoke-RestMethod "http://localhost:8080/improvement-cases"
```

Generate and compare a candidate prompt:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/prompts/candidate" -Method Post
Invoke-RestMethod -Uri "http://localhost:8080/experiments/prompt?n_runs=3" -Method Post
```

Promote only after human review:

```powershell
py scripts/promote_tag.py --base-url http://localhost:8080 --source-tag candidate --target-tag staging
```

## Q&A Notes

If asked why phantom citation correction exists: small models can invent citation IDs when context is dense. Phoenix Reflex detects invalid IDs at runtime, corrects inside the same session, and reports how often it happened.

If asked about experiment statistics: the generator runs at temperature 0.4 during experiments so that n_runs > 1 produces real variance — if the same prompt gives different scores across runs, the std tells you how stable it is. The judge always runs at temperature 0.0 so scoring is reproducible. Promotion stays manual because a score delta without human review of the actual answers is not enough signal.

If asked whether one model judging another is reliable: the demo uses a separate strict judge prompt with explicit scoring criteria. Production should add sampled human review or a second judge family.

If asked about `answer_quality`: it is a demo-grade heuristic layer for faithful but poor answers, currently limited to language mismatch and over-abstention. Replace it with a stronger classifier before production.
