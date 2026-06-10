# About the project

## Inspiration

The failure mode that bothers me most in production RAG systems is not the dramatic one — the hallucination a user immediately catches and reports. It is the quiet one: an answer that is *mostly* right, confident in tone, and wrong in exactly the detail the user needed. The user moves on. The system logs nothing. The next user asks the same question and gets the same weak answer.

I kept seeing this pattern: teams would deploy a RAG agent, watch it work on the easy questions, and assume the hard ones were fine too. They were not fine — they were just failing silently. And because the failures were silent, there was no feedback loop. Nothing to iterate on.

The question that drove this project was: **what if the agent itself was the first line of observability?** What if, instead of waiting for a user to complain or a human reviewer to sample traces, every weak answer automatically became a regression test?

That is the idea behind Phoenix Reflex.

---

## What I built

Phoenix Reflex is a regression-driven QA agent built on Google ADK 2.x, FastAPI, and Arize Phoenix. It wraps a standard RAG pipeline — retrieve, answer, cite — with a loop that catches failures before they reach the user, scores the final answer, and converts low-quality responses into structured regression data.

### The in-session correction loop

The most distinctive piece is the phantom citation detector. RAG models on dense multi-article questions frequently invent citation IDs — references that look syntactically valid but point to chunks that were never retrieved. The system intercepts the model's raw output, extracts every citation ID, and checks each one against the actual retrieval results. If any ID is invalid, a correction turn fires **inside the same ADK session** — not a client retry, not a new request, but a second turn with the model in the same context window, instructed to fix only the broken references.

The correction runs up to twice. If both attempts fail, the system surfaces the remaining phantom citations honestly rather than hiding them. In practice, on the demo corpus (Spanish Workers' Statute + Statute of Autonomy for Andalusia), a single dense cross-article question produced 11 phantom citations — all corrected in one pass.

### Scoring and the regression flywheel

After correction, three evaluators run on the final answer:

- **Faithfulness** — does every claim in the answer have support in the retrieved chunks?
- **Document relevance** — did the retriever surface the right material?
- **Answer quality** — lightweight heuristics for language mismatch and over-abstention

The faithfulness evaluator uses a strict LLM-as-judge prompt at temperature 0 for reproducibility. When the score falls below $\tau = 0.75$, the question, answer, retrieved context, and score are captured as an *improvement case* — a named, queryable regression test.

Improvement cases feed a prompt optimization loop: a candidate prompt is generated from the accumulated failures, tested against production over $n$ runs, and the results compared. The comparison produces a score delta $\Delta s = \bar{s}_\text{candidate} - \bar{s}_\text{production}$ along with standard deviation across runs, so instability is visible alongside improvement. No prompt is promoted automatically — a human runs `promote_tag.py` to advance any tag to staging.

### Runtime observability via Phoenix MCP

The agent can also introspect its own operational traces at runtime. When asked an observability question — "what failed in the latest traces?" — the agent calls Phoenix MCP tools to retrieve live spans from Arize Phoenix Cloud, identifies spans where `failure_mode != none`, and creates improvement cases directly from what it finds. The MCP call, the tools invoked, and the resulting action are all surfaced in the `/ask` response and in the OTel trace, so the behavior is auditable end-to-end.

### Multi-agent architecture

Under the hood, a coordinator agent delegates to two subagents: a judge subagent that runs evaluation tools and a improvement subagent that handles regression case creation and prompt generation. Both are defined with Google ADK 2.x and run inside a single session graph. The coordinator returns plain-text answers; the subagents own the tool calls.

---

## How I built it

| Layer | Technology |
| --- | --- |
| Agent runtime | Google ADK 2.x (multi-agent graph) |
| LLM | Gemini 3.5 Flash |
| API | FastAPI + Pydantic |
| Retrieval | BM25 + hybrid BM25/Gemini embeddings |
| Tracing | OpenInference + Arize OTel (`otlp.eu-west-1a.arize.com`) |
| Runtime introspection | Phoenix MCP (`@arizeai/phoenix-mcp`) |
| UI | React 19 + TypeScript + Vite |
| Deploy | Google Cloud Run (europe-west1) |

The architecture separates concerns sharply: `retriever.py` owns chunk ranking, `qa.py` owns the correction loop and orchestration, `evaluator.py` owns scoring, `reflex.py` owns regression data, and `experiments.py` owns the prompt comparison loop. Each module is testable in isolation; the integration is thin.

I chose Google ADK 2.x specifically for the session graph model. The in-session correction loop requires that the correction turn share the exact same context window as the original turn — something that is trivial with ADK sessions but would require custom state management with a stateless API wrapper.

Instrumentation is attached via `openinference-instrumentation-google-adk`, which wraps every ADK session automatically. Custom span attributes (`eval.citation_correction_applied`, `eval.phantom_citation_count`, `phoenix_mcp.called`) are added at the OTel layer, not in application code, keeping the core logic clean.

---

## Challenges

**LLM-as-judge reliability.** Gemini evaluating Gemini output is the obvious attack vector. I addressed it by: (1) keeping the judge prompt deterministic (temperature 0, explicit scoring rubric with no wiggle room), (2) building a human validation table of 10 reviewed cases that documents confirmed false positives and false negatives, and (3) making the judge a *prioritization signal* rather than a *decision signal* — it scores, humans promote. The validated agreement rate on the demo set is 80%, with two documented failure modes: over-penalizing runtime MCP context when traces are empty (false positive) and missing a single unsupported subclaim inside an otherwise grounded mixed answer (false negative).

**Phantom citation variance.** The correction loop works reliably when the model produces structurally valid but wrong IDs. It is less reliable when the model omits citations entirely rather than inventing them — that case shows up as `failure_mode: retrieval` without triggered correction. The current system captures that failure as a regression case but does not attempt to recover the missing citations, which would require a second retrieval pass and is out of scope for this iteration.

**Cold corpus problem.** The regression flywheel only produces signal once there are enough improvement cases to generate a meaningful candidate prompt. With a fresh deployment and zero captured failures, `POST /prompts/candidate` returns a generic prompt. I solved this for the demo by pre-loading the corpus and pre-running the failure-inducing questions so there are improvement cases from the first session. The auto-seed mechanism in `lifespan` ensures Cloud Run starts with the demo corpus ready without manual upload.

**Retrieval quota under evaluation.** Gemini embeddings have per-minute rate limits. During load testing, `/ask` calls started failing with `429 RESOURCE_EXHAUSTED` when hybrid retrieval hit the embedding API too fast. The fallback is now explicit: if semantic or hybrid retrieval fails for any reason, the system transparently falls back to BM25-only and tags the response `retrieval_mode: bm25_fallback`. Quality degrades gracefully instead of returning a 500.
