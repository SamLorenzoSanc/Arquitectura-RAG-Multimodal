# Arquitectura del sistema

## Alcance

AgroRAG es un prototipo funcional contenedorizado con cuatro servicios principales: frontend React/Vite, gateway FastAPI, PostgreSQL/pgvector y Ollama. Además, el gateway usa almacenamiento local para originales y Markdown extraído, y ficheros pickle BM25 por tenant.

```text
Navegador
  -> frontend React/Vite (puerto 80 en Docker; 5173 en desarrollo)
  -> /api/v1 del gateway FastAPI (8000)
       -> PostgreSQL 15 + extensión pgvector (5432)
       -> Ollama, API OpenAI /v1 (11434)
       -> storage/ y gateway/services/extracted_md/
       -> gateway/services/bm25_indexes/tenant_<id>.pkl
```

## Componentes

### Frontend

`frontend/agrops` usa React 19, Vite 8, TypeScript, Axios y React Query. Gestiona autenticación, conversaciones, selección de organización/base de conocimiento, carga documental y visualización de fuentes/evaluación. El frontend no ejecuta retrieval ni modelos.

### Gateway

`gateway/main.py` crea `AgroRAG Gateway` y registra rutas bajo `/api/v1`. Las responsabilidades relevantes son:

- autenticación JWT y resolución de usuario/organización/tenant;
- conversaciones, mensajes y fuentes;
- carga, almacenamiento, parsing e ingesta asíncrona;
- recuperación híbrida y generación;
- simulador y evaluación;
- funcionalidades auxiliares agrícolas, geográficas, logísticas y de voz.

El gateway es la fuente de verdad actual. `src/` conserva un prototipo/evaluador legado con contratos y orquestación distintos.

### Persistencia

PostgreSQL almacena entidades de identidad, organizaciones/tenants, bases de conocimiento, documentos, chunks, embeddings, conversaciones y ejecuciones de evaluación. Los embeddings se consultan por distancia coseno mediante pgvector. El índice BM25 no está en PostgreSQL: se serializa por tenant y se reconstruye tras ingesta.

### Modelos

Ollama se consume mediante clientes compatibles con OpenAI:

- generación/enriquecimiento: por defecto `llama3`, con selección `llama3.2:latest` en chat;
- embeddings: `qwen3-embedding:latest`;
- reranking local: SentenceTransformers `BAAI/bge-reranker-v2-m3`;
- vídeo: faster-whisper `small` tras extracción de audio con FFmpeg.

Los tags `latest` y las imágenes Docker flotantes impiden conocer el peso/binario exacto solo a partir del repositorio.

## Multitenancy

El usuario se relaciona con una organización activa y esta con un tenant activo. Las consultas densas filtran `Document.tenant_id`; opcionalmente filtran `knowledge_base_id`. El índice BM25 se construye por tenant y conserva `knowledge_base_id` en cada entrada.

La conversación almacena `tenant_id`, `user_id` y `knowledge_base_id`. No obstante, en la ruta de chat revisada la llamada a `rag_service.answer` pasa el tenant pero no la base seleccionada; por tanto, el aislamiento por tenant está implementado en retrieval, mientras que el filtrado por knowledge base debe verificarse después de los cambios del otro worker.

La caché de retrieval usa tenant, pregunta y colecciones como clave. Su TTL por defecto es 120 segundos. La implementación revisada no tiene límite LRU ni invalidación explícita de esta caché tras ingesta.

## Seguridad y privacidad

La ejecución local evita enviar datos a un proveedor cloud cuando todos los endpoints apuntan a servicios locales. No equivale a certificación de cumplimiento. Riesgos verificados:

- `SECRET_KEY` tiene un valor inseguro por defecto si no se configura;
- `DATABASE_URL` se imprime al iniciar, lo que puede exponer credenciales en logs;
- CORS admite cuatro orígenes localhost;
- PostgreSQL y Ollama están publicados al host en Compose;
- LlamaParse puede requerir `LLAMA_CLOUD_API_KEY`, por lo que el parsing de determinados formatos no es necesariamente local.

## Despliegue y madurez

La denominación justificable es **prototipo funcional contenedorizado**. No hay evidencia versionada de alta disponibilidad, backup/restauración, observabilidad operativa completa, hardening, pruebas de carga sostenida, SLO, gestión de secretos o validación productiva.

## Limitaciones estructurales observadas

- Las rutas de evaluación de `gateway/routes/chat.py` estaban duplicadas en la instantánea auditada.
- El endpoint duplicado antiguo invocaba un método `search_with_scores` no visible en `RAGService`.
- La configuración de pytest apuntaba a `test/`, pero la suite está en `tests/`.
- No se verificó que PostgreSQL use HNSW; documentar pgvector no implica documentar HNSW.
- Los modelos y versiones de imágenes no están fijados por digest.

Estas observaciones describen el estado auditado el 10-08-2026 y pueden cambiar con el trabajo paralelo de código.
