# Arquitectura de Phoenix Reflex

Este documento define el stack, la estructura de módulos y los principios que todo agente DEBE respetar.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.12 |
| Framework API | FastAPI + Uvicorn |
| Agente LLM | Google ADK (`google-adk`) + Gemini (`google-genai`) |
| Modelo | gemini-3.5-flash (default) |
| Observabilidad | OpenTelemetry + openinference-instrumentation-google-adk/genai |
| Backend tracing | Arize AX (principal) / Phoenix (fallback) |
| MCP partner | Arize Phoenix MCP (`@arizeai/phoenix-mcp`) via npx |
| Retrieval | BM25 (siempre) + embeddings semánticos (si GEMINI_API_KEY) |
| Almacenamiento | JSON local en `data/` (docs, chunks, embeddings) |
| Frontend | React 19 + TypeScript + Vite |
| Deploy | Docker + Google Cloud Run |

---

## Estructura de módulos

```
phoenix_reflex/           ← módulo Python principal
  main.py                 ← FastAPI app: define todos los endpoints, sin lógica de negocio
  agent.py                ← sessions de ADK, tool definitions, event stream parsing
  qa.py                   ← orquestación: retrieval → correction loop → evaluation → capture
  evaluator.py            ← LLM-as-Judge (faithfulness, document_relevance, answer_quality)
  experiments.py          ← generate candidate prompt → compare → should_promote decision
  retriever.py            ← BM25 + hybrid ranking, citation format pdf:{src} p.X c.Y
  mcp.py                  ← McpToolset opcional, optional_phoenix_mcp_tools()
  reflex.py               ← deques TRACE_SUMMARIES + IMPROVEMENT_CASES, format_reflex_context()
  prompts.py              ← PRODUCTION_PROMPT, sistema de tagging (production/candidate/staging)
  observability.py        ← TracerProvider config (Arize AX o Phoenix), span attributes
  document_store.py       ← JSON CRUD para documents.json, chunks.json, embeddings.json
  ingestion.py            ← PDF upload → extract → chunk → store
  embeddings.py           ← Gemini embeddings API
  chunking.py             ← text splitting por párrafo/tamaño
  pdf_loader.py           ← extracción de texto de PDFs via pypdf

phoenix_reflex_agent/
  agent.py                ← root_agent: Agent(model, instruction=PRODUCTION_PROMPT, tools=[...])
```

---

## Flujo de datos principal (`POST /ask`)

```
question
  ↓
¿Es pregunta de introspección? → format_reflex_context() inyectado en mensaje
  ↓
Turno 1 del agente (ADK):
  - retrieve_documents(query)         → BM25/hybrid sobre chunks locales
  - list_improvement_cases()          → contexto de fallos previos
  - phoenix_mcp_tools (si disponible) → trazas Arize en runtime
  ↓
Phantom citation detection (regex sobre event stream)
  ↓
Correction turns (hasta 2) si hay phantom citations
  ↓
Style correction si hay leaks internos ("retrieved", "context", "tool")
  ↓
Three-judge evaluation:
  - evaluate_faithfulness(question, answer, retrieved_docs)
  - evaluate_document_relevance(question, retrieved_docs)
  - _assess_answer_quality(question, answer)
  ↓
classify_failure_mode() → "none" | "retrieval" | "generation" | "answer_quality"
  ↓
maybe_create_improvement_case() si score < 0.75 o quality suspicious
  ↓
record_trace_summary()
  ↓
Respuesta JSON completa (answer + telemetría)
```

---

## Principios clave

### 1. main.py es solo routing

Los endpoints en `main.py` llaman a funciones de módulos específicos.
No contienen lógica de negocio, loops ni llamadas directas a Gemini.

### 2. PRODUCTION_PROMPT es inmutable en runtime

El prompt de producción vive en `prompts.py` bajo el tag `production`.
Solo se cambia a través del flujo de tagging: candidate → staging → production via `promote_tag.py`.
**NUNCA modificar directamente durante una sesión de agente.**

### 3. Los evaluadores son read-only

`evaluator.py` evalúa respuestas pero nunca modifica estado del agente, del prompt ni del store.
Solo `reflex.py` captura improvement cases como efecto secundario de `qa.py`.

### 4. Observabilidad como fuente de verdad

Los spans OTel en Arize AX son el registro canónico de qué hizo el agente.
Los deques locales en `reflex.py` son un caché rápido para introspección inmediata.
Ambos deben estar sincronizados: lo que `qa.py` registra en spans se refleja en `record_trace_summary()`.

### 5. Sin estado global mutable excepto en reflex.py

Las deques `TRACE_SUMMARIES` e `IMPROVEMENT_CASES` en `reflex.py` son el único estado global.
El resto de módulos son stateless entre llamadas.

### 6. MCP es opcional y graceful

Si `ENABLE_PHOENIX_MCP=0` o npx no está disponible, el sistema funciona con el contexto local de `reflex.py`.
El agente nunca debe fallar por ausencia de MCP; debe degradar limpiamente.

---

## Verificación mínima por feature

Antes de que el reviewer pueda aprobar:

```bash
pytest                      # todos los tests verdes
python -c "import phoenix_reflex; import phoenix_reflex_agent"  # sin ImportError
```

Para features con cambios en endpoints o flujo de agente, además:

```bash
uvicorn phoenix_reflex.main:app --port 8080 &
curl -s http://localhost:8080/health | python -m json.tool
```
