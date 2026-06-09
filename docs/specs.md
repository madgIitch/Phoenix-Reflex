# Proceso SDD — Phoenix Reflex

Este documento define el proceso Spec Driven Development (SDD) que todo agente DEBE seguir antes de escribir código.

---

## Regla de oro

> **No se toca código sin un spec aprobado por el humano.**

---

## Los tres archivos de un spec

Para cada feature con `"sdd": true` en `feature_list.json`, el `spec_author` redacta EXACTAMENTE tres archivos bajo `specs/<name>/`:

```
specs/<name>/
  requirements.md   ← QUÉ debe hacer el sistema (EARS)
  design.md         ← CÓMO se hará (decisiones técnicas)
  tasks.md          ← lista de tareas ejecutables con checkbox
```

---

## 1. requirements.md — EARS estricto

Cada requirement usa uno de estos cinco patrones:

| Patrón | Plantilla | Cuándo |
|--------|-----------|--------|
| **Ubicuo** | `El sistema DEBE <acción>.` | Siempre verdadero |
| **Evento** | `CUANDO <disparador>, el sistema DEBE <acción>.` | Respuesta a evento |
| **Estado** | `MIENTRAS <estado>, el sistema DEBE <acción>.` | Durante condición |
| **Opcional** | `DONDE <feature opcional>, el sistema DEBE <acción>.` | Feature condicional |
| **No deseado** | `SI <evento no deseado> ENTONCES el sistema DEBE <acción>.` | Manejo de errores |

### Reglas duras

- Cada requirement tiene id estable: `R1`, `R2`, `R3`...
- Un solo `DEBE` por requirement
- Sin verbos blandos: no "podría", "puede", "soporta", "considera"
- Cada requirement DEBE ser verificable por un test concreto o por un comando con exit 0

### Ejemplo

```markdown
## R1
El sistema DEBE detectar phantom citations comparando los IDs entre
corchetes en la respuesta del agente contra `valid_citation_ids` devueltos por `retrieve_documents`.

## R2
CUANDO se detecta al menos una phantom citation, el sistema DEBE
enviar un turno de corrección al agente con el mensaje de corrección canónico.

## R3
SI el agente sigue produciendo phantom citations después de 2 turnos de corrección,
ENTONCES el sistema DEBE devolver la respuesta con `phantom_citations` no vacío y
`failure_mode: "generation"`.

## R4
CUANDO se ejecuta `pytest`, el sistema DEBE terminar con exit 0.
```

---

## 2. design.md — Decisiones técnicas

Captura ANTES de tocar código:

- **Objetivo:** qué problema resuelve y por qué ahora
- **Archivos a crear o modificar:** lista completa con rutas relativas al repo
- **Firmas y funciones:** firmas de funciones/clases nuevas o modificadas
- **Dependencias previstas:** paquetes pip nuevos, cambios en requirements.txt, módulos internos afectados
- **Tests y trazabilidad:** qué test cubre cada `R<n>`
- **Alternativa descartada:** qué enfoque se consideró y por qué se rechazó

### Ejemplo

```markdown
## Objetivo
Hacer que el MCP dispare de forma natural ante preguntas de observabilidad,
sin depender del parche _force_phoenix_mcp_introspection.

## Archivos a crear o modificar
- phoenix_reflex/mcp.py              ← refactor de optional_phoenix_mcp_tools
- phoenix_reflex/qa.py               ← eliminar llamada a _force_phoenix_mcp_introspection
- tests/test_mcp.py                  ← tests del nuevo comportamiento

## Firmas y funciones
def is_observability_question(question: str) -> bool: ...
async def optional_phoenix_mcp_tools() -> list[Any]: ...  # sin cambios en firma

## Dependencias previstas
- Sin paquetes nuevos
- Módulos afectados: mcp.py, qa.py

## Tests y trazabilidad
- R1 → tests/test_mcp.py (test_natural_mcp_dispatch)
- R2 → tests/test_mcp.py (test_graceful_fallback_no_mcp)
- R3 → tests/test_mcp.py (test_mcp_called_flag_in_response)
- R4 → pytest (exit 0)

## Alternativa descartada
Se descartó inyectar el contexto MCP siempre (no solo en preguntas de observabilidad)
porque introduce latencia innecesaria en preguntas sobre PDFs.
```

---

## 3. tasks.md — Checklist ejecutable

Pasos discretos en orden. Cada paso:
- Tiene id `T<n>`
- Indica qué `R<n>` cubre
- Tiene checkbox `[ ]` → `[x]` cuando termina el implementer

### Ejemplo

```markdown
# mcp_hardening — Tasks

- [ ] T1 - Extraer `is_observability_question()` como función pura en `mcp.py`. Cubre: R1.
- [ ] T2 - Refactorizar `qa.py` para usar `is_observability_question()` en lugar de heurística inline. Cubre: R1.
- [ ] T3 - Eliminar `_force_phoenix_mcp_introspection` de `qa.py`. Cubre: R2.
- [ ] T4 - Añadir graceful fallback en `mcp.py` cuando npx no está disponible. Cubre: R2.
- [ ] T5 - Escribir `tests/test_mcp.py` con los 3 casos del spec. Cubre: R1, R2, R3.
- [ ] T6 - Verificar `pytest` y `python -c "import phoenix_reflex"`. Cubre: R4.
```

---

## Flujo de estados

```
pending
  ↓ spec_author redacta los 3 archivos
spec_ready
  ↓ ⏸ PAUSA — humano revisa y aprueba
in_progress
  ↓ implementer ejecuta tasks
  ↓ reviewer valida trazabilidad
review_pending
  ↓ ⏸ PAUSA — humano ejecuta smoke tests
done
```

### Reglas de transición

| De | A | Quién | Condición |
|----|---|-------|-----------|
| `pending` | `spec_ready` | spec_author | 3 archivos creados |
| `spec_ready` | `in_progress` | leader (humano aprobó) | Aprobación explícita |
| `spec_ready` | `pending` | leader (humano rechazó) | Cambios solicitados |
| `in_progress` | `review_pending` | leader | reviewer dice APPROVED |
| `review_pending` | `done` | leader | Humano confirma smoke tests |
| `in_progress` | `blocked` | implementer | No puede avanzar sin ayuda |

---

## Regla anti-teléfono-descompuesto

Los subagentes escriben resultados en **archivos de disco**, no en el chat.
El leader solo recibe referencias:

```
spec_ready  -> specs/<name>/
done        -> progress/impl_<name>.md
APPROVED    -> progress/review_<name>.md
BLOCKED     -> progress/impl_<name>.md (con sección "Bloqueo")
```

---

## Una feature por sesión

En cualquier momento, como máximo UNA feature puede estar en `in_progress`.
Si el leader encuentra dos, para y pide instrucciones al humano.
