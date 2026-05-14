# Phoenix Reflex Demo

Use any text-based PDF with content you can inspect and verify. The demo should show the generic loop, not a case-specific script:

1. Upload or select a prepared PDF.
2. Ask a question that is directly supported by enabled chunks.
3. Ask a question that is only partially supported.
4. **Show the in-session correction loop** (see section below — this is the agentic highlight).
5. Show faithfulness, document relevance, answer quality, and retrieved citations.
6. Show any generated improvement cases.
7. Generate a candidate prompt and run the prompt experiment.

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
