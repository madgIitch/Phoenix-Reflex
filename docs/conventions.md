# Convenciones de código — Phoenix Reflex

Sigue estas convenciones para que el agente prediga correctamente el estilo existente.

---

## Python

### Formato y estilo

- Python 3.12, type hints en todas las funciones públicas
- Sin `print()` en código de producción — usar logging o atributos de span OTel
- Sin `# type: ignore` salvo en imports de librerías sin stubs (documentar por qué)
- Longitud de línea: 100 caracteres máximo
- Trailing comma en estructuras multi-línea

### Imports — orden obligatorio

```python
# 1. Stdlib
import os
import json
from typing import Optional

# 2. Terceros
import fastapi
from google.adk.agents import Agent
from opentelemetry import trace

# 3. Módulos del propio proyecto
from phoenix_reflex.evaluator import evaluate_faithfulness
from phoenix_reflex.reflex import maybe_create_improvement_case
```

### Nombres

| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Función | `snake_case` | `evaluate_faithfulness` |
| Clase | `PascalCase` | `DocumentStore` |
| Constante global | `UPPER_SNAKE` | `PRODUCTION_PROMPT`, `IMPROVEMENT_CASES` |
| Variable local | `snake_case` | `trace_summary` |
| Parámetro | `snake_case` | `question`, `top_k` |
| Módulo / archivo | `snake_case.py` | `document_store.py` |

### Funciones asíncronas

- Los endpoints FastAPI son `async def`
- Las funciones que llaman a Gemini API son `async def`
- Las funciones de evaluación son `async def` (llamadas concurrentes en `qa.py`)
- Las funciones puramente locales (BM25, deques, parsing) pueden ser `def`

---

## FastAPI

### Estructura de un endpoint

```python
@app.post("/ask")
async def ask_question(body: AskRequest) -> AskResponse:
    """Un párrafo máximo describiendo qué hace el endpoint."""
    result = await ask_agent(body.question)
    return AskResponse(**result)
```

### Reglas de endpoints

- Los modelos Pydantic van en `main.py` (junto al endpoint) si son pequeños,
  o en un archivo `models.py` si hay más de 5
- Cada endpoint delega a una función en el módulo correspondiente
- Los errores de negocio se devuelven como `HTTPException` con código semántico (400, 404, 422)
- El endpoint nunca llama directamente a Gemini ni a Supabase — solo orquesta

---

## Agente ADK

### Definición de tools

```python
async def retrieve_documents(query: str, top_k: int = 4) -> dict:
    """
    Busca chunks relevantes en los PDFs indexados.
    Devuelve: {query, valid_citation_ids, documents, retrieval_method}
    """
    return await _retrieve(query, top_k)
```

### Reglas del agente

- `root_agent` en `phoenix_reflex_agent/agent.py` solo referencia tools definidas en `phoenix_reflex/`
- `PRODUCTION_PROMPT` se importa desde `phoenix_reflex.prompts`, nunca se hardcodea en `agent.py`
- Las tools son funciones async con docstring que describe su contrato de entrada/salida
- El agente no tiene estado persistente entre sesiones; `runner.run_async` crea un contexto fresco

---

## Tests

### Ubicación

- Tests bajo `tests/` en la raíz del proyecto (no bajo `phoenix_reflex/`)
- Archivo por módulo: `tests/test_retriever.py`, `tests/test_evaluator.py`, etc.
- Fixtures compartidas en `tests/conftest.py`

### Estructura de un test

```python
import pytest
from phoenix_reflex.qa import _find_phantom_citations

def test_find_phantom_citations_none():
    answer = "La respuesta es correcta [pdf:doc.pdf p.1 c.0]."
    valid = {"pdf:doc.pdf p.1 c.0"}
    assert _find_phantom_citations(answer, valid) == []

def test_find_phantom_citations_one():
    answer = "Ver [pdf:missing.pdf p.2 c.1] para más detalles."
    valid = {"pdf:doc.pdf p.1 c.0"}
    assert len(_find_phantom_citations(answer, valid)) == 1
```

### Reglas de tests

- Sin llamadas reales a Gemini en tests unitarios — mockear con `unittest.mock.AsyncMock`
- Sin dependencias de red en `tests/` — todo lo que necesite red va a `tests/integration/`
- Un test = una sola aserción lógica (pueden ser múltiples `assert` si son del mismo comportamiento)
- Nombres: `test_<función>_<escenario>` — e.g., `test_find_phantom_citations_malformed_id`

---

## Observabilidad (OTel / Arize)

- Atributos de span en `snake_case` con prefijo de dominio: `eval.faithfulness.score`, `qa.event_count`
- No loggear PII (preguntas del usuario) directamente; el span de ADK ya lo captura
- Si añades un nuevo atributo, documenta en `docs/architecture.md` bajo "Span attributes tracked"

---

## Strings y mensajes

- Mensajes de error en inglés (API JSON)
- Docstrings en inglés
- Comentarios solo cuando el POR QUÉ no es obvio (no describir qué hace el código)
