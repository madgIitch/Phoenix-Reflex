# phantom_citation_tests - Requirements

## R1
El sistema DEBE verificar que `_find_phantom_citations()` devuelve un conjunto vacio cuando todas las citas `pdf:` de la respuesta pertenecen a `valid_ids`.

## R2
CUANDO una respuesta contiene una cita `pdf:` que no pertenece a `valid_ids`, el sistema DEBE verificar que `_find_phantom_citations()` devuelve esa cita como phantom citation.

## R3
CUANDO una respuesta contiene varias citas `pdf:` no validas, el sistema DEBE verificar que `_find_phantom_citations()` devuelve todas las citas fantasma sin duplicados.

## R4
CUANDO una respuesta contiene texto entre corchetes que no empieza por `pdf:`, el sistema DEBE verificar que `_find_phantom_citations()` ignora ese texto aunque no pertenezca a `valid_ids`.

## R5
CUANDO una respuesta contiene brackets anidados o malformados, el sistema DEBE verificar el comportamiento actual de `_find_phantom_citations()` sin lanzar excepciones.

## R6
CUANDO `faithfulness.score` es mayor o igual que `0.75` y `answer_quality.label` no es `suspicious`, el sistema DEBE verificar que `_classify_failure_mode()` devuelve `none`.

## R7
CUANDO `faithfulness.score` es menor que `0.75` y `document_relevance.score` es menor que `0.75`, el sistema DEBE verificar que `_classify_failure_mode()` devuelve `retrieval`.

## R8
CUANDO `faithfulness.score` es menor que `0.75` y `document_relevance.score` es mayor o igual que `0.75`, el sistema DEBE verificar que `_classify_failure_mode()` devuelve `generation`.

## R9
CUANDO `faithfulness.score` es mayor o igual que `0.75` y `answer_quality.label` es `suspicious`, el sistema DEBE verificar que `_classify_failure_mode()` devuelve `answer_quality`.

## R10
CUANDO se ejecuta `pytest`, el sistema DEBE terminar con exit 0.

## R11
CUANDO se ejecuta `python -c "import phoenix_reflex; import phoenix_reflex_agent"`, el sistema DEBE terminar sin `ImportError`.
