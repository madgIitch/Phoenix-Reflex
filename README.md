# Phoenix Reflex

**Phoenix Reflex** is a self-improving RAG agent that not only answers questions, but also observes, evaluates, and improves itself through its own execution traces.

The project combines a RAG pipeline with **Arize Phoenix**, **Phoenix MCP**, and an **LLM-as-a-judge evaluation loop** to detect low-confidence answers, possible hallucinations, weak retrieval results, and reasoning failures.

## Core Idea

Most RAG agents answer and stop.

Phoenix Reflex closes the loop:

1. A user asks a question.
2. The RAG agent retrieves context and generates an answer.
3. Every step is traced in Phoenix.
4. The agent detects possible failure signals:
   - low confidence
   - weak retrieval
   - missing citations
   - possible hallucination
   - inconsistent reasoning
5. The agent queries its own traces through Phoenix MCP.
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
Phoenix Tracing
     |
     v
Failure Detection
     |
     v
Phoenix MCP Trace Query
     |
     v
LLM-as-a-Judge Evaluation
     |
     v
Improvement Case Generator