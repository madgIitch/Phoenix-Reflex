# Phoenix Reflex

**Phoenix Reflex** is a self-improving RAG agent that not only answers questions, but also observes, evaluates, and improves itself through its own execution traces.

The project combines a RAG pipeline with **Arize AX tracing**, OpenInference instrumentation for Google/Gemini, Phoenix MCP-style runtime introspection, and an **LLM-as-a-judge evaluation loop** to detect low-confidence answers, possible hallucinations, weak retrieval results, and reasoning failures.

## Core Idea

Most RAG agents answer and stop.

Phoenix Reflex closes the loop:

1. A user asks a question.
2. The RAG agent retrieves context and generates an answer.
3. Every step is traced in Arize AX.
4. The agent detects possible failure signals:
   - low confidence
   - weak retrieval
   - missing citations
   - possible hallucination
   - inconsistent reasoning
5. The agent queries its own traces through MCP-backed observability tools.
6. An LLM-as-a-judge evaluates the answer.
7. If the answer is weak, the system automatically creates an improvement case.

## What It Generates

When a problematic answer is detected, Phoenix Reflex can automatically create:

- a new regression test question
- a dataset example for future evaluation
- a supervised correction
- a GitHub issue
- a failure report
- a prompt or retrieval improvement suggestion

## Why It Matters

RAG systems usually fail silently.

Phoenix Reflex makes failures visible, traceable, and actionable.

Instead of treating observability as a dashboard only for humans, this project turns observability into a runtime tool that the agent itself can use to improve.

## Architecture

```text
User Question
     |
     v
RAG Agent
     |
     v
Retriever + Generator
     |
     v
Arize AX Tracing
     |
     v
Failure Detection
     |
     v
MCP Trace Query
     |
     v
LLM-as-a-Judge Evaluation
     |
     v
Improvement Case Generator
```

## Sprint 0

Sprint 0 sets up the empty deployment path before adding RAG logic:

- FastAPI service with public health check at `/health`.
- Hello-world trace endpoint at `/hello`.
- Minimal Google ADK `qa_agent` placeholder in `phoenix_reflex_agent/agent.py`.
- Arize AX tracing through `arize.otel.register()`.
- Google ADK and Google GenAI OpenInference instrumentation.
- Dockerfile with Python and Node, ready for Cloud Run and the later Phoenix MCP `npx` dependency.
- Gemini CLI MCP config in `.gemini/settings.json` for Phoenix runtime introspection.

## Local Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn phoenix_reflex.main:app --reload --port 8080
```

Then open:

- `http://localhost:8080/health`
- `http://localhost:8080/hello`

The `/hello` request emits a `hello_world` span when `ARIZE_API_KEY` and `ARIZE_SPACE_ID` are set.

Use Arize AX credentials from your space:

- `ARIZE_API_KEY`: key from Arize AX.
- `ARIZE_SPACE_ID`: space ID from Arize AX.
- `ARIZE_PROJECT_NAME`: `phoenix-reflex`.
- `ARIZE_OTEL_ENDPOINT`: `https://otlp.eu-west-1a.arize.com/v1` for the EU region.
- `GEMINI_API_KEY`: your Gemini API key.

Your `.env` should include:

```env
ARIZE_API_KEY=...
ARIZE_SPACE_ID=...
ARIZE_PROJECT_NAME=phoenix-reflex
ARIZE_OTEL_ENDPOINT=https://otlp.eu-west-1a.arize.com/v1
GEMINI_API_KEY=...
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

## Cloud Run

Create Secret Manager secrets named `ARIZE_API_KEY`, `ARIZE_SPACE_ID`, and `GEMINI_API_KEY`, then deploy:

```powershell
.\scripts\deploy-cloud-run.ps1 `
  -ProjectId your-gcp-project-id `
  -Region europe-west1
```

The service should expose:

- `/health` for Cloud Run readiness checks.
- `/hello` for validating that a trace reaches Arize AX.

## Sprint 1

Sprint 1 adds the smallest useful RAG loop:

- Curated corpus of 12 short documents in `phoenix_reflex/corpus.py`.
- Intentional failure cases: Phoenix naming ambiguity, partially supported questions, and unsupported topics.
- BM25-style retriever in `phoenix_reflex/retriever.py`.
- `retrieve_documents` tool connected to `qa_agent`.
- `/retrieve` endpoint for inspecting retrieval directly.
- `/ask` endpoint for running the ADK agent with retrieval and cited answers.

Try retrieval directly:

```powershell
Invoke-RestMethod "http://localhost:8080/retrieve?query=que%20hace%20sprint%201&top_k=2"
```

Ask the agent:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8080/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Que agrega el sprint 1 y que debe hacer si no hay contexto?"}'
```

The answer should cite corpus document ids such as `[s1-goal]` and `[s1-prompt]`. In Arize AX, the trace should show the top-level ask span, retrieval span, ADK invocation, tool call, and model generation activity.

## Sprint 2

Sprint 2 adds inline faithfulness evaluation:

- LLM-as-a-judge evaluator in `phoenix_reflex/evaluator.py`.
- Every `/ask` response is checked against retrieved documents.
- The API response includes `faithfulness.label`, `faithfulness.score`, and `faithfulness.explanation`.
- Arize AX traces include a `faithfulness_eval` span and `eval.faithfulness.*` attributes on `qa_agent.ask`.

Example response shape:

```json
{
  "question": "...",
  "answer": "...",
  "faithfulness": {
    "label": "faithful",
    "score": 1.0,
    "explanation": "...",
    "context_doc_ids": ["s1-goal", "s1-prompt"]
  }
}
```

Useful validation questions:

```text
Que agrega el sprint 1 y que debe hacer si no hay contexto?
Cual es el presupuesto exacto del equipo y la biografia de cada miembro?
```

The first should be answered with citations and a high faithfulness score. The second should abstain and still receive a high score because the abstention is supported by the missing context.

To demonstrate an intentionally unfaithful answer without weakening the normal agent behavior, use the manual eval endpoint:

```powershell
$body = @{
  question = "Cual es el presupuesto exacto del equipo?"
  answer = "El presupuesto exacto del equipo es 50000 euros."
} | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://localhost:8080/eval/faithfulness" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

This should return `unfaithful` because the corpus does not support the budget claim.

## Sprint 3

Sprint 3 adds self-introspection and improvement-case generation:

- `list_recent_trace_summaries`: lets the agent inspect recent `/ask` runs.
- `get_trace_summary`: fetches one stored trace summary by session id.
- `list_improvement_cases`: exposes generated regression candidates.
- `add_improvement_case`: records low-faithfulness answers into the local `regression_v1` queue.
- Optional Phoenix MCP toolset in `phoenix_reflex/mcp.py`, enabled only with `ENABLE_PHOENIX_MCP=1` and Phoenix credentials.

The local improvement queue is intentionally lightweight for the hackathon demo. It proves the self-correction loop without requiring a database:

```text
answer -> faithfulness eval -> low score -> improvement case -> regression_v1
```

Generate a failing case:

```powershell
$body = @{
  question = "Cual es el presupuesto exacto del equipo?"
  answer = "El presupuesto exacto del equipo es 50000 euros."
} | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://localhost:8080/eval/faithfulness" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Inspect generated cases:

```powershell
Invoke-RestMethod "http://localhost:8080/improvement-cases"
```

Ask the agent to inspect itself:

```powershell
$body = @{ question = "Resume tus ultimas trazas y casos de mejora" } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://localhost:8080/ask" -Method Post -ContentType "application/json" -Body $body
```

To enable the official Phoenix MCP server later:

```env
ENABLE_PHOENIX_MCP=1
PHOENIX_HOST=https://app.phoenix.arize.com/s/your-space
PHOENIX_API_KEY=px_live_...
```

When enabled, the ADK agent adds MCP tools for Phoenix traces, spans, datasets, and prompts through `@arizeai/phoenix-mcp`.

## Phoenix MCP

The Arize hackathon starter configures Phoenix MCP through Gemini CLI rather than inside the Python ADK service. This repo follows that pattern for sprint 0:

- Edit `.gemini/settings.json`.
- Replace `https://app.phoenix.arize.com/s/your-space` with the same Phoenix Cloud hostname used for tracing.
- Put the API key in the Gemini CLI environment or fill the `--apiKey` value locally.
- Start Gemini CLI from the repo root so it can load the MCP server config.

Once traces exist, Gemini CLI can inspect Phoenix traces, prompts, datasets, experiments, and sessions through `@arizeai/phoenix-mcp`.
