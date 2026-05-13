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

## Phoenix MCP

The Arize hackathon starter configures Phoenix MCP through Gemini CLI rather than inside the Python ADK service. This repo follows that pattern for sprint 0:

- Edit `.gemini/settings.json`.
- Replace `https://app.phoenix.arize.com/s/your-space` with the same Phoenix Cloud hostname used for tracing.
- Put the API key in the Gemini CLI environment or fill the `--apiKey` value locally.
- Start Gemini CLI from the repo root so it can load the MCP server config.

Once traces exist, Gemini CLI can inspect Phoenix traces, prompts, datasets, experiments, and sessions through `@arizeai/phoenix-mcp`.
