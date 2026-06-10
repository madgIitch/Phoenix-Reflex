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

| # | Source | Question (abbreviated) | Judge verdict | Judge score | Human verdict | Agreement | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `loop_visible_mission` | ¿Qué texto refundido aprueba el RDL 2/2015 y qué reforma la LO 2/2007? | faithful | 1.0 | **Agree** | ✓ | Based on the feature 6 demo corpus. Human review confirmed the answer separates the Estatuto de los Trabajadores from the Estatuto de Autonomía para Andalucía and cites only loaded PDFs. |
| 2 | `loop_visible_mission` | ¿Qué artículos tratan derechos laborales, jornada, vacaciones y extinción del contrato? | faithful | 1.0 | **Agree** | ✓ | Covers the visible loop's normal RAG path. Human review found the answer grounded in the worker statute chunks and suitable for candidate-generation demos when later cases fail. |
| 3 | `loop_visible_mission` | Según estos PDFs, ¿cuál es el plazo exacto para renovar el DNI electrónico? | faithful | 1.0 | **Agree** | ✓ | Abstention case from the feature 6 design. Human review confirmed the answer refuses to invent an external deadline because the loaded legal PDFs do not contain it. |
| 4 | `loop_visible_mission` | Jornada laboral y plazo para renovar el DNI electrónico. | faithful | 1.0 | **Disagree - false negative** | ✗ | Mixed-question case from the feature 6 script. Human review marked the answer partially unsupported when it handled the jornada from the PDF but also supplied a DNI-renewal detail outside the retrieved corpus; the judge missed that unsupported subclaim. |
| 5 | `loop_visible_mission` | Tras un `/ask` con `improvement_case`, generar candidate y ejecutar experiment. | faithful | 1.0 | **Agree** | ✓ | Human review checked the UI behavior implemented in feature 6: `Generate Candidate` calls `/prompts/candidate`, `Run Experiment` shows `should_promote_to_staging`, and there is no automatic `/prompts/promote`. |
| 6 | `mcp_observation_action` | ¿Cuáles son las últimas respuestas fallidas del agente según las trazas de Phoenix? | unfaithful | 0.0 | **Disagree - false positive** | ✗ | Based on the feature 7 smoke test A1. MCP was called and returned empty traces, so `mcp_action.status` was correctly `no_action`; the judge over-penalized runtime MCP context with no PDF chunks. |
| 7 | `mcp_observation_action` | Repetir la misma pregunta de trazas fallidas. | partially faithful | 0.5 | **Agree** | ✓ | Based on smoke test A2 and the dedup requirement. Human review confirmed no duplicate MCP improvement case was created and the partial score is acceptable because the answer mostly reports absence of actionable traces. |
| 8 | `mcp_observation_action` | Sin MCP: ¿cuál es el PIB de España en 2024? | faithful | 1.0 | **Agree** | ✓ | Based on smoke test C1. Human review confirmed fallback behavior: `phoenix_mcp_called: false`, `mcp_action: null`, and a clean abstention or PDF-cited answer instead of an MCP action. |
| 9 | `judge_validation_table` | Resume las competencias sobre empleo y añade su relación con prevención de riesgos laborales. | faithful | 1.0 | **Agree** | ✓ | Cross-article synthesis from EA Andalucía Art. 63 and Art. 173. Human review confirmed all 8 bullet points and the 4 PRL integration points are grounded in retrieved chunks. `document_relevance: 1.0`. Good example of the retriever handling a two-part question across non-adjacent articles. |
| 10 | `judge_validation_table` | ¿Puede el agente promover automáticamente un prompt candidato si mejora el score? | faithful | 1.0 | **Agree** | ✓ | Meta-question about the system itself. Retriever pulled labor law chunks about "promoción" (job promotion) rather than AI prompt promotion — correct out-of-scope retrieval failure. Model correctly abstained explaining the loaded PDFs are legal texts. `failure_mode: none`. |

**Agreement rate (validation set): 8 / 10 (80%).** Case 6 is a confirmed false positive where runtime MCP evidence with empty traces was over-penalized. Case 4 is a confirmed false negative where one unsupported external-detail claim was missed inside a mixed answer.

### What this does not cover yet

- High-recall questions with long answers where one unsupported claim in ten is easy to miss
- Non-Spanish / mixed-language questions

Add rows to this table as the system accumulates traces. The current demo set has 10 reviewed cases drawn from the three latest specs, with at least one confirmed false positive and one confirmed false negative.

## Demo Discipline

Use any text-based PDF whose contents you can verify. Precompute embeddings before a live demo:

```powershell
py scripts/precompute_embeddings.py
```

Avoid uploading a large new PDF live unless you have already timed ingestion and embedding generation.
