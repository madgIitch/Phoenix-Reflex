# AGENTS.md — Mapa de navegación para Phoenix Reflex

Este archivo es el **primer archivo que lee todo agente** al arrancar.
Define dónde está todo, cuándo leerlo, y el flujo SDD resumido.

---

## Mapa de archivos

| Ruta | Contenido | Cuándo leer |
|------|-----------|-------------|
| `AGENTS.md` | Este archivo — navegación global | Siempre, al empezar |
| `CLAUDE.md` | Instrucciones para Claude Code (rol leader) | Si usas Claude Code |
| `feature_list.json` | Lista de features con estado y prioridad | Siempre, al empezar |
| `progress/current.md` | Estado de la sesión activa | Siempre, al empezar |
| `progress/history.md` | Bitácora histórica | Si necesitas contexto de lo hecho |
| `specs/<name>/requirements.md` | QUÉ debe hacer la feature | Antes de implementar |
| `specs/<name>/design.md` | CÓMO se hará (decisiones técnicas) | Antes de implementar |
| `specs/<name>/tasks.md` | Checklist de tareas ejecutables | Durante implementación |
| `progress/impl_<name>.md` | Reporte del implementer | Para review / contexto |
| `progress/review_<name>.md` | Veredicto del reviewer | Para verificar estado |
| `docs/architecture.md` | Stack, módulos, principios de calidad | Antes de tocar código |
| `docs/conventions.md` | Estilo Python, nombres, estructura | Antes de escribir código |
| `docs/specs.md` | Proceso SDD completo (EARS, plantillas) | Antes de redactar/leer specs |
| `docs/verification.md` | Comandos de verificación y niveles | Antes de verificar |
| `CHECKPOINTS.md` | Criterios de estado final | Para autoevaluación del reviewer |
| `init.ps1` | Verificación integral (PowerShell/Windows) | Al arrancar sesión |
| `init.sh` | Verificación integral (bash) | Al arrancar sesión (bash/WSL) |

---

## Estructura del proyecto

```
phoenix_reflex/           ← módulo Python principal (backend)
  main.py                 ← FastAPI app + todos los endpoints
  agent.py                ← lógica de agente QA (tools, sessions)
  qa.py                   ← orquestación del loop: retrieval → correction → eval
  evaluator.py            ← LLM-as-Judge (faithfulness, relevance, quality)
  experiments.py          ← prompt optimization loop (generate → compare → promote)
  retriever.py            ← BM25 + hybrid ranking sobre chunks locales
  mcp.py                  ← integración Phoenix MCP (McpToolset + optional tools)
  reflex.py               ← captura improvement cases + trace summaries
  prompts.py              ← versioning y tagging de prompts
  observability.py        ← OTel + Arize AX / Phoenix tracing config
  document_store.py       ← almacenamiento JSON de docs y chunks
  ingestion.py            ← upload + chunking de PDFs
  embeddings.py           ← semántica (Gemini embeddings)
  chunking.py             ← text splitting
  pdf_loader.py           ← extracción de texto de PDFs

phoenix_reflex_agent/     ← definición del agente Google ADK
  agent.py                ← root_agent (Agent con tools y PRODUCTION_PROMPT)

frontend/                 ← React 19 + TypeScript + Vite (UI operador)
  src/main.tsx            ← SPA completa (6 vistas)

scripts/
  deploy-cloud-run.ps1    ← deploy a Google Cloud Run
  precompute_embeddings.py
  promote_tag.py          ← promoción manual de prompt tags

data/                     ← almacenamiento local (gitignored)
docs/                     ← documentación del workflow SDD
specs/                    ← un subdirectorio por feature con sus 3 archivos
progress/                 ← current.md, history.md, impl_*, review_*
```

---

## Flujo SDD resumido

```
1. Leader lee AGENTS.md + feature_list.json + progress/current.md
2. Leader ejecuta .\init.ps1 (PowerShell) o bash ./init.sh
3. Caso según status de la siguiente feature SDD:

   PENDING → leader lanza spec_author
             spec_author crea specs/<name>/{requirements,design,tasks}.md
             spec_author cambia status → spec_ready
             ⏸ PAUSA: leader espera aprobación humana

   SPEC_READY + aprobado → leader cambia status → in_progress
                            leader lanza implementer
                            implementer ejecuta tasks, escribe progress/impl_<name>.md
                            leader lanza reviewer
                            reviewer escribe progress/review_<name>.md
                            Si APPROVED → status → review_pending
                                          ⏸ PAUSA: smoke tests humanos
                                          Humano confirma "ok"
                                          status → done

   SPEC_READY sin aprobación → recuerda al humano que debe aprobar

   REVIEW_PENDING → smoke tests humanos pendientes

   IN_PROGRESS → sesión interrumpida; preguntar si reanuda o aborta

   BLOCKED → informar al humano y esperar instrucciones
```

---

## Reglas duras (aplican a todos los agentes)

- ❌ **NUNCA** marcar `done` sin `APPROVED` del reviewer y confirmación humana de smoke tests
- ❌ **NUNCA** saltar la aprobación humana (`spec_ready` → `in_progress`)
- ❌ **NUNCA** implementar sin spec aprobado
- ❌ **NUNCA** más de 1 feature `in_progress` simultáneamente
- ❌ **NUNCA** tocar `phoenix_reflex_agent/agent.py` (PRODUCTION_PROMPT) sin spec explícito
- ✅ Los subagentes escriben resultados en disco, devuelven solo referencias al leader
- ✅ `progress/current.md` se actualiza en tiempo real durante la sesión
- ✅ `.\init.ps1` DEBE pasar con exit 0 antes de dar la sesión por cerrada

---

## Comandos clave

```powershell
# Verificación integral
.\init.ps1                                   # PowerShell (Windows)
bash ./init.sh                               # bash / Git Bash / WSL

# Desarrollo
uvicorn phoenix_reflex.main:app --reload --port 8080   # backend
cd frontend && npm run dev                              # frontend (localhost:5173)

# Tests
pytest                                       # todos los tests
pytest tests/ -v                             # con verbose

# Despliegue
.\scripts\deploy-cloud-run.ps1
```
