# Pipeline de consulta RAG

## Flujo

1. FastAPI autentica al usuario y obtiene su tenant activo.
2. Se normalizan espacios de la pregunta.
3. Para consultas complejas o largas, Ollama puede reescribir la pregunta. Consultas directas o de hasta diez palabras omiten esta fase.
4. Se ejecutan en paralelo:
   - recuperación densa por distancia coseno en PostgreSQL/pgvector;
   - recuperación léxica BM25 desde el índice del tenant.
5. Si hubo reescritura, se repiten ambas recuperaciones con la consulta reescrita.
6. Reciprocal Rank Fusion suma `1 / (rrf_k + rango)` para cada lista.
7. Se conservan hasta `candidate_k` candidatos únicos.
8. `BAAI/bge-reranker-v2-m3` puntúa pares `(pregunta, chunk)` y reordena.
9. Los primeros `final_k` chunks se incorporan al prompt.
10. Ollama genera la respuesta y el gateway guarda respuesta y fuentes.

```text
pregunta ─┬─ dense original ──────┐
          ├─ BM25 original ───────┤
          └─ reescritura opcional ├─ RRF ─ Cross-Encoder ─ top final ─ Ollama
             ├─ dense reescrita ──┤
             └─ BM25 reescrita ───┘
```

## Parámetros

| Parámetro | Servicio por defecto | Evaluación/simulador |
|---|---:|---:|
| `retrieval_k` denso | 10 | 10 |
| `bm25_k` | 10 | 10 |
| `rrf_k` | 60 | 60 |
| `candidate_k` | 15 | 15 |
| `final_k`/`top_k` | 3 | 5 |
| reranker batch | 16 | 16 |
| reranker max length | 512 | 512 |

El feedback de memoria solicita `top-k=10`. El código usa 10 como profundidad inicial densa y BM25, pero entrega 3 o 5 chunks finales. Una tabla experimental debe nombrar cada profundidad y no etiquetar ambiguamente todas como “top-k”.

## Recuperación densa

La pregunta se vectoriza con `qwen3-embedding:latest`. La consulta une `Chunk`, `Embedding` y `Document`, filtra por `tenant_id` y, cuando recibe colecciones, por `knowledge_base_id`. Ordena por `cosine_distance` y limita a `retrieval_k`.

No se encontró evidencia versionada de que exista o se use un índice HNSW. Hasta verificarlo con la migración y `EXPLAIN (ANALYZE, BUFFERS)`, debe describirse como búsqueda pgvector por distancia coseno, no como búsqueda HNSW.

## BM25 y RRF

BM25 normaliza Unicode, pasa a minúsculas, elimina diacríticos y tokeniza palabras/números conservando guiones y barras. El fichero `tenant_<id>.pkl` contiene todos los chunks del tenant y metadatos de base de conocimiento. Los resultados con puntuación no positiva se descartan.

RRF fusiona rankings sin comparar directamente escalas heterogéneas de distancia densa y score BM25. Un mismo chunk se identifica por `(document_id, chunk_id)` y recibe contribución de cada ranking en el que aparece.

## Cross-Encoder

El reranker se carga de forma perezosa en CPU o CUDA y se reutiliza dentro de una instancia de `RAGService`. Puntúa hasta 15 candidatos y el trabajo síncrono se deriva a un thread para no bloquear el event loop.

## Generación, citas y abstención

El prompt exige español, precisión y no inventar fuera del contexto. Incluye el nombre de la fuente antes de cada fragmento, pero no impone un formato formal de citas ni valida automáticamente documento/página. Los metadatos de chunks se devuelven al frontend y se registran como fuentes.

No hay un umbral de score que fuerce abstención: incluso preguntas fuera de conocimiento pueden devolver los mejores vecinos disponibles. Por ello, “no inventes” en el prompt no demuestra una tasa de abstención segura.

La ruta de chat permite una respuesta sin RAG mediante `simple_chat` en evaluación, pero la comparación debe usar las mismas preguntas, modelo, temperatura efectiva y protocolo de juez.

## Caché

La caché en memoria usa SHA-256 de `tenant | pregunta | colecciones` y TTL `RETRIEVAL_CACHE_TTL` (120 s por defecto). En la revisión:

- no estaba acotada por tamaño;
- no se desactivaba explícitamente en evaluación;
- no requiere invalidación por ingesta porque el runtime no admite nuevas cargas;
- solo se comparte dentro del proceso.

Esto puede sesgar latencias de evaluación y devolver contexto obsoleto. Todo experimento debe declarar si la caché estaba fría, caliente o desactivada.

## Configuración no verificable

- Temperatura efectiva: `ChatRequest` define 0, pero el cliente principal no envía `temperature`.
- Digest/revisión exacta de modelos Ollama y Hugging Face.
- Dimensión efectiva de embeddings para el modelo instalado.
- Uso de HNSW.
- Filtro de knowledge base en la ruta de chat auditada.
