Public demo URL: https://phoenix-reflex-27208039935.europe-west1.run.app

# Phoenix Reflex

Phoenix Reflex is not a PDF chatbot. It is a regression-driven agent for the real
failure mode in RAG: agents fail silently, then repeat the same weak answers.

In Phoenix Reflex, weak answers become test cases and prompt candidates. The agent
retrieves evidence, corrects invalid citations before responding, scores the final
answer, captures failures as regression data, and compares candidate prompts before
a human promotes a change.

## Core Flow

1. Upload one or more text-based PDFs.
2. The backend extracts pages, chunks text, and stores local JSON records under `data/`.
3. Retrieval ranks enabled chunks with BM25 or hybrid BM25 + embeddings when Gemini credentials are available.
4. The QA agent answers from returned chunks only and cites returned PDF chunk IDs.
5. **In-session correction loop**: the agent's answer is inspected before it reaches the user. Phantom citations (IDs the model invented that do not correspond to any retrieved chunk) trigger up to two correction rounds inside the same ADK session. If the corrected answer then leaks internal retrieval mechanics, a second style-correction pass runs. All correction events are recorded as OTel span attributes.
6. Evaluators score faithfulness, document relevance, and lightweight answer quality on the final corrected answer.
7. Low-scoring or suspicious answers become test cases in `regression_v1`.
8. A candidate prompt can be generated from regression cases and compared against production.
9. Promotion to `staging` is manual.
10. For observability/debug questions, the agent can inspect Phoenix Cloud traces at runtime through Phoenix MCP and returns MCP evidence in `/ask`.

## Local Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn phoenix_reflex.main:app --reload --port 8080
```

Run the UI:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Environment

```env
GEMINI_API_KEY=...
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash
```

Tracing is optional. If configured, the service can emit OpenTelemetry spans:

```env
ARIZE_API_KEY=...
ARIZE_SPACE_ID=...
ARIZE_PROJECT_NAME=phoenix-reflex
ARIZE_OTEL_ENDPOINT=https://otlp.eu-west-1a.arize.com/v1
```

Phoenix MCP is used for the hackathon demo runtime introspection checkbox:

```env
ENABLE_PHOENIX_MCP=1
PHOENIX_HOST=https://app.phoenix.arize.com/s/your-space
PHOENIX_API_KEY=px_live_...
```

Check readiness:

```powershell
Invoke-RestMethod "http://localhost:8080/observability/mcp"
```

## API Checks

```powershell
Invoke-RestMethod "http://localhost:8080/health"
Invoke-RestMethod "http://localhost:8080/documents"
Invoke-RestMethod "http://localhost:8080/documents/search?query=your%20question&top_k=5"
```

Ask the agent:

```powershell
$body = @{ question = "Your question about the uploaded PDFs" } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://localhost:8080/ask" -Method Post -ContentType "application/json" -Body $body
```

Expected citations use the returned chunk IDs:

```text
[pdf:filename.pdf p.3 c.2]
```

The response also includes correction telemetry:

```json
{
  "answer": "...",
  "phantom_citations_detected_count": 1,
  "phantom_citations": [],
  "failure_mode": "none"
}
```

`phantom_citations_detected_count > 0` with an empty `phantom_citations` array means the loop caught and fixed an invented citation. A non-empty array means correction failed after two attempts.

## Prompt Loop

Create a candidate prompt from captured improvement cases:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/prompts/candidate" -Method Post
```

Compare candidate and production:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/experiments/prompt?n_runs=3" -Method Post
```

Promote manually:

```powershell
py scripts/promote_tag.py --base-url http://localhost:8080 --source-tag candidate --target-tag staging
```

## PDF Data

Local data is stored under `data/`, which is ignored by git:

- `data/documents.json`
- `data/chunks.json`
- `data/uploads/`
- `data/embeddings.json`

PDF chunks are retrieved only when `enabled=true`.

## Human Validation of the Judge

The faithfulness judge is Gemini evaluating Gemini output. The table below documents cases reviewed by a human reviewer to surface systematic biases, false positives, and blind spots before any judge score triggers a promotion.

**Key principle:** the judge never promotes automatically. It only assigns a priority score; a human must run `promote_tag.py` to advance any prompt to staging.

| # | Session (short) | Question (abbreviated) | Judge verdict | Judge score | Human verdict | Agreement | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `ee77466` | ¿Qué facultades asume el Estatuto de Autonomía para el pleno empleo? | unfaithful | 0.0 | **Agree** | ✓ | Answer included "Materia laboral" as a full-employment faculty. Source text (p.24 c.2) only describes scope of competence; the link to full employment is an inference, not stated. Judge correctly flagged it. |
| 2 | `ec334dbc` | What failed in the latest traces, and what improvement should we make next? | unfaithful | 0.0 | **Disagree** | ✗ → bug fixed | Answer was correct and grounded in Phoenix MCP evidence. Judge short-circuited to "unfaithful" because `retrieved_documents=[]` caused the context string to start with "No documents retrieved." — the LLM judge anchored on that and ignored the runtime traces that followed. Fixed by passing `extra_context` through `evaluate_document_relevance` and rewriting `_format_context` to not prepend that string when runtime context exists. |
| 3 | `94b797a2` | ¿Establece el Estatuto de los Trabajadores que las franjas verde y blanca de la bandera de Andalucía deben aprobarse mediante la jurisdicción de un despido colectivo? | faithful | 1.0 | **Agree** | ✓ | Absurd/trap question combining two unrelated legal texts. Answer correctly abstained and explained both texts separately. `document_relevance=0` is also correct: retrieved chunks are each only partially on-topic and none link the flag to dismissal jurisdiction. The system handled a hostile question cleanly. |
| 4 | `cbdbdf36` | What failed in the latest traces, and what improvement should we make next? | faithful | 1.0 | **Agree** | ✓ | Same question as case 2, after the evaluator fix. Agent called `phoenix_list-traces` twice, cited a specific `case_id` and `source_session_id`, described the exact failure, and proposed a concrete fix. Answer is fully grounded. `document_relevance=1` now correct because runtime context is passed to the evaluator. |

**Agreement rate (seed set): 3 / 4 (75%).** Case 2 was a judge pipeline bug (not a design choice), which was fixed. Excluding it, the seed agreement is 3 / 3.

### What this does not cover yet

- Questions where the judge scores 0.5 (partially faithful) — need cases where the human can assess borderline support
- High-recall questions with long answers where one unsupported claim in ten is easy to miss
- Non-Spanish / mixed-language questions

Add rows to this table as the system accumulates traces. Minimum recommended before a demo: 8–10 cases with at least one confirmed false positive and one confirmed false negative.

## Demo Discipline

Use any text-based PDF whose contents you can verify. Precompute embeddings before a live demo:

```powershell
py scripts/precompute_embeddings.py
```

Avoid uploading a large new PDF live unless you have already timed ingestion and embedding generation.
