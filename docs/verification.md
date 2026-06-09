# Verificación — Phoenix Reflex

Define cómo demostrar que una feature funciona correctamente.
Los niveles son escalonados: cada nivel superior requiere los inferiores.

---

## Nivel 1 — Tests automáticos (obligatorio para toda feature SDD)

```bash
pytest
# o con verbose:
pytest tests/ -v
```

- Todos los tests deben pasar (exit 0)
- Cada requirement `R<n>` del spec DEBE tener al menos un test que lo valide
- Tests ubicados bajo `tests/` en la raíz (no dentro de `phoenix_reflex/`)
- Sin llamadas reales a Gemini en tests unitarios — usar mocks

---

## Nivel 2 — Import check (obligatorio)

```bash
python -c "import phoenix_reflex; import phoenix_reflex_agent"
```

- Sin `ImportError` ni `ModuleNotFoundError`
- Valida que no se han roto dependencias entre módulos

---

## Nivel 3 — Health check del servidor (obligatorio para cambios en endpoints)

```bash
uvicorn phoenix_reflex.main:app --port 8080 &
sleep 2
curl -s http://localhost:8080/health
```

Respuesta esperada:

```json
{"status": "ok"}
```

---

## Nivel 4 — Smoke test manual (obligatorio para cambios de comportamiento del agente)

Documentado en `progress/impl_<name>.md` bajo la sección `## Smoke test manual`.

Formato:

```markdown
## Smoke test manual

- [ ] `uvicorn phoenix_reflex.main:app --port 8080` arranca sin errores
- [ ] `GET /health` → `{"status": "ok"}`
- [ ] `POST /ask {"question": "¿Qué dice el artículo 1?"}` devuelve answer no vacío
- [ ] La respuesta incluye `phantom_citations_detected_count` >= 0
- [ ] `GET /observability/mcp` devuelve `demo_ready`
- [ ] Frontend en localhost:5173 muestra la respuesta sin errores de consola
```

---

## Nivel 5 — Trazabilidad (obligatorio para toda feature SDD)

Documentado en `progress/impl_<name>.md` bajo la sección `## Trazabilidad`.

Formato:

```markdown
## Trazabilidad

- R1 → tests/test_mcp.py::test_natural_mcp_dispatch ✓
- R2 → tests/test_mcp.py::test_graceful_fallback_no_mcp ✓
- R3 → tests/test_mcp.py::test_mcp_called_flag_in_response ✓
- R4 → pytest (exit 0) ✓
```

Cada `R<n>` del spec DEBE aparecer con su test correspondiente.

---

## Comandos de referencia

| Comando | Propósito |
|---------|-----------|
| `pytest` | Tests unitarios (todos) |
| `pytest tests/test_X.py -v` | Tests de un módulo concreto |
| `python -c "import phoenix_reflex"` | Import check rápido |
| `uvicorn phoenix_reflex.main:app --reload --port 8080` | Servidor de desarrollo |
| `cd frontend && npm run dev` | Frontend (localhost:5173) |
| `.\init.ps1` | Verificación integral (Windows) |
| `bash ./init.sh` | Verificación integral (bash/WSL) |
| `python scripts/precompute_embeddings.py` | Pre-generar embeddings antes de demo |
