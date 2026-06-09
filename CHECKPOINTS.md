# CHECKPOINTS — Criterios de estado final para Phoenix Reflex

El reviewer recorre esta lista antes de emitir su veredicto.
Cada checkpoint debe marcarse `[x]` o `[ ]` en `progress/review_<name>.md`.

---

## C1 — El arnés SDD está completo

- [ ] Existen `AGENTS.md`, `CLAUDE.md`, `CHECKPOINTS.md`
- [ ] Existe `feature_list.json` con estructura válida
- [ ] Existen `docs/architecture.md`, `docs/conventions.md`, `docs/specs.md`, `docs/verification.md`
- [ ] Existen `.claude/agents/` con los 4 roles
- [ ] Existen `specs/` y `progress/` como directorios
- [ ] `.\init.ps1` termina con exit 0 (o `bash ./init.sh`)

---

## C2 — El estado es coherente

- [ ] Como máximo 1 feature en `in_progress` en `feature_list.json`
- [ ] Toda feature `done` tiene `progress/impl_<name>.md` y `progress/review_<name>.md`
- [ ] Toda feature SDD `done` tiene `specs/<name>/` con los 3 archivos
- [ ] `progress/current.md` describe la sesión activa o está vacío si no hay sesión

---

## C3 — El código respeta la arquitectura

- [ ] Los cambios al agente (`phoenix_reflex_agent/agent.py`) tienen spec explícito
- [ ] `PRODUCTION_PROMPT` en `prompts.py` no se modifica directamente; se usa el sistema de tagging
- [ ] Los evaluadores en `evaluator.py` no modifican el estado del agente (solo leen)
- [ ] Los endpoints nuevos en `main.py` delegan a módulos específicos, no contienen lógica de negocio
- [ ] Sin `print()` en código de producción — usar logging o spans OTel
- [ ] Sin dependencias nuevas no documentadas en el `design.md` del spec

---

## C4 — La verificación es real

- [ ] `pytest` termina con exit 0 (todos los tests verdes)
- [ ] `python -c "import phoenix_reflex; import phoenix_reflex_agent"` sin error
- [ ] `GET /health` → 200 (servidor arrancado)
- [ ] Todo módulo/feature SDD tiene tests que cubren sus requirements

---

## C5 — La sesión se cerró bien

- [ ] `progress/current.md` está vacío o actualizado a la sesión siguiente
- [ ] `progress/history.md` tiene una entrada con la sesión que se cierra
- [ ] La feature está en el estado correcto (`done`, `blocked`, o `spec_ready`)
- [ ] No hay archivos temporales sueltos

---

## C5b — Sign-off humano de smoke tests (obligatorio antes de `done`)

- [ ] El humano ha recibido la checklist del `## Smoke test manual` de `progress/impl_<name>.md`
- [ ] El humano ha confirmado explícitamente ("ok", "aprobado") todos los smoke tests
- [ ] Si algún smoke test falló, la feature vuelve a `in_progress` para corregir

---

## C6 — Spec Driven Development (solo para features con `"sdd": true`)

- [ ] `specs/<name>/requirements.md` existe y usa EARS estricto
- [ ] `specs/<name>/design.md` existe con todos sus apartados
- [ ] `specs/<name>/tasks.md` existe y todas las tasks están `[x]` (o justificadas)
- [ ] Cada `R<n>` aparece en la tabla de trazabilidad de `progress/impl_<name>.md`
- [ ] Cada `R<n>` tiene un test o comando que lo verifica
- [ ] El reviewer ha validado manualmente cada `R<n>` → test
