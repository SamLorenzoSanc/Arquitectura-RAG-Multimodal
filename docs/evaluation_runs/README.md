# Corrida congelada del TFM

Esta carpeta es el capítulo 7. Si un número no sale de un `run_id` de aquí, no va a la memoria.

## Banco de oro

- Fuente única: `knowledge-base/gold_tests.jsonl`
- Copias idénticas: `knowledge-base/tests.jsonl`, `src/evaluation/tests.jsonl`, `gateway/core/tests.jsonl`, `gateway/routes/tests.jsonl`
- N = 35, siete categorías, 5 ítems cada una
- Corpus de retrieval de la corrida: `knowledge-base/asesor-canarias/**/*.md` (POSEI, GIP, cuarentena, dossiers de cultivo)
- Cada ítem tiene `source_file`, `page` (sección markdown) y `reference_answer`

Samuel debe rellenar `gold_validation.csv` **antes** de mirar al juez: `ok` o `corregir` + fecha, leyendo el markdown (y, si puede, la página del PDF consolidado POSEI 2026).

## Lanzar la corrida

Ollama tiene que servir `llama3.2:latest` y `nomic-embed-text`.

```
python scripts/freeze_eval_run.py
```

Escribe `docs/evaluation_runs/<run_id>/{config.json,results.csv,summary.json,failures.json}`.

Configuración que debe coincidir con el chat: chunk 1400/120, denso+BM25+RRF, `RAG_USE_RERANKER=false`, `final_k=8`, temperatura = default de Ollama (no se envía). RAGAS **no** se ejecuta: las columnas RAGAS quedan en blanco.

## Puntuación humana (ciega al juez)

Muestra fijada **antes** de la corrida: `human_sample_item_ids.json` (primeros 3 ítems de cada categoría = 21).

Cuando exista `results.csv`:

```
python scripts/make_author_scorecard.py docs/evaluation_runs/<run_id>/results.csv
```

Puntuar `author_rag_accuracy` y `author_vanilla_accuracy` (1–5, exactitud frente a la referencia) **sin abrir** las columnas del juez. Después:

```
python scripts/score_human_agreement.py docs/evaluation_runs/<run_id>/author_scorecard.csv docs/evaluation_runs/<run_id>/results.csv
```

Se informa porcentaje de acuerdo ±1 punto. Kappa solo si hay segundo anotador.

## Lo que no entra en la memoria

- MRR 0,7911 u otras cifras exploratorias sin este `run_id`
- H1/H2 inventados: salen de `failures.json` del mismo run
- 150 preguntas sintéticas, kappa, panel PAC, RAGAS si no corrió
