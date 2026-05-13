# Phoenix Reflex

Phoenix Reflex is a regression-driven PDF RAG system: weak answers become regression cases, improvement hypotheses, and prompt-candidate comparisons before a human promotes a change.

## Core Flow

1. Upload one or more text-based PDFs.
2. The backend extracts pages, chunks text, and stores local JSON records under `data/`.
3. Retrieval ranks enabled chunks with BM25 or hybrid BM25 + embeddings when Gemini credentials are available.
4. The QA agent answers from returned chunks only and cites returned PDF chunk IDs.
5. Evaluators score faithfulness, document relevance, and lightweight answer quality.
6. Low-scoring or suspicious answers become `improvement_case` records in `regression_v1`.
7. A candidate prompt can be generated from regression cases and compared against production.
8. Promotion to `staging` is manual.

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
GEMINI_MODEL=gemini-2.5-flash
```

Tracing is optional. If configured, the service can emit OpenTelemetry spans:

```env
ARIZE_API_KEY=...
ARIZE_SPACE_ID=...
ARIZE_PROJECT_NAME=phoenix-reflex
ARIZE_OTEL_ENDPOINT=https://otlp.eu-west-1a.arize.com/v1
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

## Demo Discipline

Use any text-based PDF whose contents you can verify. Precompute embeddings before a live demo:

```powershell
py scripts/precompute_embeddings.py
```

Avoid uploading a large new PDF live unless you have already timed ingestion and embedding generation.
