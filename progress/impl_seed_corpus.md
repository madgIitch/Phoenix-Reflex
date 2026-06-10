# impl_seed_corpus

## Resumen de cambios

Se añadio la funcion `_seed_demo_corpus()` en `phoenix_reflex/main.py` y se invoca desde el
`lifespan` async context manager, justo despues de `configure_tracing()` y antes del `yield`.

La funcion:
1. Llama a `list_documents()` — si ya hay documentos, retorna sin hacer nada.
2. Itera sobre `_DEMO_PDFS = ["BOE-A-2015-11430-consolidado.pdf", "lo_2-2007.pdf"]`.
3. Por cada PDF comprueba que existe via `Path(pdf_name).exists()`.
   - Si no existe: `print(f"[seed] {pdf_name} not found, skipping")`.
4. Si existe: lee bytes, genera `document_id = f"pdf-{sha256[:12]}"`, usa un
   `NamedTemporaryFile`, llama a `extract_pdf_pages` + `chunk_pages` +
   `save_document_with_chunks` (misma logica que `ingest_pdf` pero sin `UploadFile`).
   - Chunks llevan `tags: ["pdf", "seed"]`.
   - Imprime `f"[seed] ingested {pdf_name}: {N} chunks"`.
5. Cualquier excepcion es capturada e impresa; el startup no se interrumpe.

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `phoenix_reflex/main.py` | Nuevos imports (`hashlib`, `re`, `tempfile`, `Path`, `chunk_pages`, `save_document_with_chunks`, `extract_pdf_pages`); constante `_DEMO_PDFS`; funcion `_seed_demo_corpus()`; llamada en `lifespan`. |
| `tests/test_seed_corpus.py` | Nuevo archivo con 6 tests unitarios. |

## Comandos ejecutados

```
pytest tests/test_seed_corpus.py -v
# 6 passed — exit 0

pytest
# 43 passed — exit 0

python -c "import phoenix_reflex; import phoenix_reflex_agent"
# exit 0
```

## Trazabilidad de requisitos

| Requisito (spec inline) | Test |
|---|---|
| Si hay documentos, no hace nada | `test_seed_skips_when_documents_exist` |
| Si el PDF no existe en disco, lo omite y loggea | `test_seed_skips_missing_pdf` |
| Si el PDF existe, lo ingesta y loggea chunk_count | `test_seed_ingests_pdf_when_present` |
| document_id = `pdf-<sha256[:12]>` | `test_seed_document_id_uses_sha256_prefix` |
| Excepcion en un PDF no interrumpe el siguiente | `test_seed_continues_after_exception` |
| Chunks llevan tag `seed` | `test_seed_chunk_records_have_seed_tag` |

## Smoke test manual

- [ ] Colocar `BOE-A-2015-11430-consolidado.pdf` y `lo_2-2007.pdf` en la raiz del proyecto.
- [ ] Borrar o vaciar `data/documents.json` y `data/chunks.json`.
- [ ] Arrancar el servidor: `uvicorn phoenix_reflex.main:app --port 8080`.
- [ ] Verificar en stdout que aparecen las dos lineas `[seed] ingested ... chunks`.
- [ ] `GET /documents` debe devolver los 2 documentos recien ingestados.
- [ ] Reiniciar el servidor sin tocar los datos: las lineas `[seed]` NO deben aparecer
  (documentos ya existen).
- [ ] Si un PDF no esta en disco: debe aparecer `[seed] <nombre> not found, skipping` y el
  servidor debe arrancar igualmente.
