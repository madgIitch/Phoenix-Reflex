# Phoenix Reflex Demo

Use any text-based PDF with content you can inspect and verify. The demo should show the generic loop, not a case-specific script:

1. Upload or select a prepared PDF.
2. Ask a question that is directly supported by enabled chunks.
3. Ask a question that is only partially supported.
4. Show faithfulness, document relevance, answer quality, and retrieved citations.
5. Show any generated improvement cases.
6. Generate a candidate prompt and run the prompt experiment.

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

If asked about experiment statistics: the quick demo path can run once to save tokens, but `/experiments/prompt?n_runs=3` reports repeated candidate and baseline runs with mean and standard deviation. Promotion remains manual because marginal score differences are not enough.

If asked whether one model judging another is reliable: the demo uses a separate strict judge prompt with explicit scoring criteria. Production should add sampled human review or a second judge family.

If asked about `answer_quality`: it is a demo-grade heuristic layer for faithful but poor answers, currently limited to language mismatch and over-abstention. Replace it with a stronger classifier before production.
