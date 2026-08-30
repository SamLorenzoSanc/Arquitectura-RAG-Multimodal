# Auditoría científica — Fase 1 (solo lectura)

**Proyecto:** AgroPS — Impacto de la Arquitectura RAG en las Alucinaciones de los LLMs  
**Fecha de auditoría:** 2026-08-20  
**Alcance:** repositorio completo (gateway, frontend, scripts, knowledge-base, memoria LaTeX, docs)  
**Regla:** no se inventan resultados; no se modificó código de producción/evaluación en esta fase.

---

## Pregunta experimental (reformulación)

> ¿En qué medida una arquitectura RAG híbrida (y, en su caso, agéntica) reduce las alucinaciones y mejora la calidad de las respuestas de un LLM local frente a un LLM sin recuperación, en un dominio normativo agrícola (PAC/POSEI / asesoría canaria)?

### Hipótesis (a contrastar, no a afirmar a priori)

| ID | Hipótesis | Estado actual de evidencia |
|----|-----------|----------------------------|
| H1 | RAG reduce alucinaciones vs LLM sin RAG | **SUGERIDO** (corrida N=35, juez LLM; no humano; leakage admitido) |
| H2 | Híbrido dense+BM25+RRF > solo dense o solo BM25 | **HIPÓTESIS** (código existe; ablación no ejecutada en corrida congelada) |
| H3 | Reranker mejora relevancia final | **HIPÓTESIS** (implementado; off por defecto; sin ablación) |
| H4 | Agentic mejora queries complejas vs híbrido fijo | **HIPÓTESIS** (LangGraph real; default = fast path heurístico; sin ablación) |
| H5 | La métrica de distancia afecta al retrieval | **HIPÓTESIS** (API contempla cosine/L2/IP/L1; sin experimento controlado) |
| H6 | Grounding/citas reduce contenido no sustentado | **SUGERIDO** (abstención + citas en producto; no cuantificado aparte de hall. rate del juez) |

---

## Arquitectura final REAL (fuente de verdad)

| Capa | Realidad |
|------|----------|
| UI | React + Vite + Tailwind (`frontend/agrops`) |
| API | FastAPI hexagonal (`gateway/`) |
| Persistencia | PostgreSQL + pgvector |
| Retrieve chat | Dense + BM25 + RRF (`hybrid_rrf`); reranker **off** por defecto |
| Generación | Ollama `llama3.2:latest` |
| Embedding (runtime) | `nomic-embed-text` |
| Agentic | LangGraph + `AgenticRAGService`; con `RAG_AGENT_FAST=true` es plan/grade heurístico |
| Eval congelada | `scripts/freeze_eval_run.py` → harness **local** sobre markdown (no el mismo proceso HTTP/pgvector) |

**No es el stack del MVP:** Django, ChromaDB (salvo legado `src/`), Qwen3 como embedding de la corrida oficial.

---

## 1. Implementado realmente

### Núcleo RAG hexagonal
- Ports: `ChunkRepository`, `LexicalIndexPort`, `EmbeddingPort`, `LlmPort`, `RerankerPort` — `gateway/rag/domain/ports.py`
- Use cases: `HybridRetrieve`, `AnswerQuestion`, `EvaluateRetrieval`/`EvaluateAnswer`, `IngestDocument` (parcial) — `gateway/rag/application/`
- Adapters: pgvector, BM25, Ollama, CrossEncoder — `gateway/rag/adapters/outbound/`
- Composition root: `gateway/rag/composition.py`
- Tests hexágono: `gateway/tests/unit/test_rag_hexagon.py`

### Retrieval
- Dense (pgvector), BM25, hybrid, RRF, estrategias `dense` / `bm25` / `hybrid_rrf` / `hybrid_*_rerank` / expansion
- Distances: cosine, euclidean/L2, inner_product; L1 con fallback a L2 si no hay operador
- Reranker CrossEncoder implementado (`BAAI/bge-reranker-v2-m3`)

### Agentic
- Grafo LangGraph real (`agent_graph.py` + `agentic_rag_service.py`)
- Tools: search KB, normas/diagnóstico (wrappers del híbrido), SQL cuaderno, inventario docs
- Modos chat: `hybrid` | `agentic` | `compare`
- Abstención rápida sin LLM (`RAG_FAST_ABSTAIN`)

### Evaluación (código)
- IR canónicas en `gateway/services/evaluation_metrics.py` (tests unitarios; nDCG acotado 0–1)
- LLM-as-a-Judge 1–5 en `rag/application/evaluate.py`
- Adaptador RAGAS + fallback heurístico (`ragas_service.py`, `/evaluation/ragas-run`)
- Lab configurable + auditoría UI (vanilla vs RAG + RAGAS en answer eval)
- API experimentos/estrategias/distancias bajo `/chat/evaluation/...`
- Harness congelado: `scripts/freeze_eval_run.py`
- Banco oro: `knowledge-base/gold_tests.jsonl` **N=35**, 7 categorías × 5

### Evidencia experimental existente (única corrida congelada citada)
- Path: `docs/evaluation_runs/run_20260819T165515Z/`
- N=35, 35/35 OK, 289,6 s
- MRR ≈ 0,8108; cobertura keywords ≈ 0,9643
- Exactitud juez RAG ≈ 4,46 vs vanilla ≈ 3,31
- Hallucination rate juez RAG ≈ 0,086 vs vanilla ≈ 0,314
- RAGAS: **not_run**
- nDCG del harness: **inválido** (global >1; no citar)

### Infra
- Docker Compose, CI, tests unitarios/API, Cypress E2E (según estado del repo)

---

## 2. Implementado parcialmente

| Área | Qué hay | Qué falta |
|------|---------|-----------|
| Hexágono evaluación | Carpetas + reexports | Domain/composition de evaluación vacíos; lógica en `services/` |
| Ingest hexagonal | Invalidación BM25 | Chunking/embeddings viven fuera del use case `IngestDocument` |
| Agentic “de libro” | LangGraph + tools | Default FAST: sin planner/grader/rewrite LLM |
| RAGAS | Wrapper + endpoint | Corrida oficial sin RAGAS; fallback puede parecer métrica oficial |
| Reranker | Código listo | Off por defecto; sin ablación publicada |
| Ground truth retrieval | Keywords + a veces chunk ids | Oro N=35 sin `relevant_chunk_ids` sistemáticos |
| Banco | Oro 35 + DB HITL | Drift con `knowledge-base/tests.jsonl` (150 sintéticas) y plantillas HITL |
| Distancia Manhattan | Pedida en API | Puede degradar a L2 |
| Multimodal | OCR/Whisper ingesta | Eval congelada solo texto |

---

## 3. Documentado / mencionado pero no demostrado

- GraphRAG operativo en el path de respuesta
- HyDE
- Ablaciones Dense vs BM25 vs Hybrid vs RRF vs Reranker vs Agentic (tabla completa)
- Experimento controlado de distancias (tabla vacía a rellenar)
- Experimento de chunking 500/1000/1400/2000
- RAGAS en resultados del TFM
- κ de Cohen / acuerdo humano cerrado
- Significancia estadística (Wilcoxon/bootstrap)
- “Misma receta que el chat” = mismo cableado gateway/pgvector (la corrida es script local)
- Qwen3 Embedding como embedding de la evaluación oficial
- Dataset de 150 ítems como evidencia principal

---

## 4. Documentado pero no implementado (o solo legado)

- Django como backend del MVP
- ChromaDB como almacén del MVP
- CLI unificado `evaluate.py` / `run_experiments.py` con `results/experiment_NNN/` (parcialmente hay scripts sueltos, no el harness de ablación pedido)
- Segundo anotador humano

---

## 5. Necesita experimento (Prioridades 5–16)

Orden alineado con el briefing del usuario:

1. Baseline LLM sin RAG  
2. Dense RAG  
3. BM25  
4. Hybrid (sin RRF explícito / legacy)  
5. Hybrid + RRF  
6. Hybrid + RRF + Reranker  
7. Agentic (`RAG_AGENT_FAST=false`)  
8. Distances (cosine / L2 / IP / L1 si compatible)  
9. Chunking  
10. RAGAS real (sin fallback silencioso)  
11. Validación juez vs humano (muestra 21)  
12. Estadística pareada  

**Sin ejecutar → celdas vacías.** No rellenar tablas de la memoria.

---

## 6. Necesita corrección (bugs / inconsistencias)

| Severidad | Problema | Acción prevista (Fase 2+) |
|-----------|----------|---------------------------|
| Alta | nDCG del harness `freeze_eval_run.py` > 1 | Corregir o eliminar; usar `evaluation_metrics.ndcg_at_k` |
| Alta | README / EVALUATION.md / RAG_PIPELINE con Qwen, N=21, run_9 | Alinear a nomic + N=35 + corrida congelada |
| Alta | `knowledge-base/tests.jsonl` (150) ≠ oro | Separar claramente banco sintético vs oro |
| Media | Eval congelada ≠ gateway HTTP | Documentar gap o repetir vía API |
| Media | Juez ve referencia → leakage (caso AGROIL) | Protocolo juez ciego / humano |
| Media | Afirmaciones “se demuestra” en conclusiones | Reformular a SUGERIDO donde proceda |
| Media | TOC LaTeX desactualizado / fecha portada | Recompilar + unificar |
| Baja | Padding embeddings 768→4096 | Declarar en metodología |

---

## 7. Dataset — estado

| Recurso | N | Uso |
|---------|---|-----|
| `knowledge-base/gold_tests.jsonl` | **35** | Oro canónico (7×5) |
| `gateway/core/tests.jsonl` | 35 | Runtime API (debe = oro) |
| `knowledge-base/tests.jsonl` | 150 | **No oro** (sintético / taxonomía distinta) |
| `retrieval_dataset` (Postgres) | variable | HITL + uploads (riesgo basura) |
| Corrida congelada | 35 | Única evidencia agregada publicada |

**Falta para gold standard completo:** `relevant_chunk_ids` / `relevant_document_ids` sistemáticos; `out_of_knowledge` etiquetado; validación humana rellena.

Categorías oro actuales (válidas):  
`direct_fact`, `temporal`, `relationship`, `spanning`, `regulatory_compliance`, `regulatory_fact`, `traceability`.  
Las pedidas `comparative` / `numerical` existen en el banco 150, **no** en el oro N=35.

---

## 8. Afirmaciones del TFM (muestra)

| Afirmación | Clasificación |
|------------|---------------|
| N=35, MRR≈0,81, corrida `run_20260819T165515Z` | **DEMOSTRADO** |
| Exactitud juez 3,31→4,46; hall. 0,314→0,086 | **DEMOSTRADO** (como scores del juez) |
| “RAG reduce alucinaciones” (general) | **SUGERIDO** |
| RAGAS mejora / se usó en resultados | **HIPÓTESIS / no aplica** (not_run) |
| Agentic aporta más que híbrido | **HIPÓTESIS** |
| Reranker mejora calidad | **HIPÓTESIS** |
| Embedding principal = Qwen3 (si aparece en docs) | **Contradicción** → runtime = nomic |
| Acuerdo humano / κ | **Pendiente** |

---

## 9. Entry points de evaluación existentes

- `scripts/freeze_eval_run.py`
- `scripts/make_author_scorecard.py` / `score_human_agreement.py`
- API: `/chat/evaluation/*`, `/evaluation/*`, `/datasets/*`, `/human-validation/*`
- UI: Lab auditoría, retrieval, métricas, workbench

**Falta:** harness único de ablación (`run_experiments.py`) que escriba `results/experiment_*/` con config+metrics+timings+figuras.

---

## 10. Plan inmediato (sin inventar datos)

Según prioridades del usuario:

| Prioridad | Acción | Estado |
|-----------|--------|--------|
| 1 | Auditoría | **HECHA** (este documento) |
| 2 | Corregir nDCG + tests | Siguiente |
| 3 | Consolidar dataset/GT | Después |
| 4 | Pipeline reproducible ablación | Después |
| 5–11 | Ejecutar experimentos 0–6 | Tras 4 |
| … | Resto | En orden |

---

## Criterio de cierre de Fase 1

Se puede responder al tribunal:

> “Hoy tenemos un MVP con retrieval hexagonal real y **una** corrida congelada N=35 (sin RAG / con híbrido + juez). **No** tenemos aún ablación publicada de Dense/BM25/RRF/Reranker/Agentic, ni RAGAS en esa corrida, ni acuerdo humano cerrado. El siguiente trabajo es construir el harness reproducible y rellenar tablas solo con resultados ejecutados.”

Eso es científicamente honesto y defendible.
