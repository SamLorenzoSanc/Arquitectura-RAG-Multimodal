# Arquitectura del sistema

AgroRAG se ejecuta como un monolito de aplicación con cuatro servicios principales:

```text
Navegador
  -> React/Vite servido por Nginx
  -> FastAPI (/api/v1)
       -> PostgreSQL + pgvector
       -> Ollama (/v1)
```

El job `migrate` de Docker solo aplica migraciones SQL; no es un servicio de negocio.

## Responsabilidades del gateway

El gateway concentra autenticación JWT, multitenancy, documentos, chat,
evaluación y RAG híbrido. Auth, organizaciones y el resto de rutas HTTP no se
reescriben: el hexágono se aplica **solo al bounded context RAG** (ingesta,
recuperación, generación y evaluación).

## Hexágono del núcleo RAG

El dominio RAG no depende de FastAPI, SQLAlchemy ni Ollama. El desarrollo sigue
el orden de Cockburn (de dentro hacia fuera): entidades y reglas → puertos →
casos de uso → adaptadores de salida → adaptadores de entrada.

```text
Adaptadores de entrada (FastAPI: /api/v1/chat, documentos, evaluación)
        |
        v
Casos de uso (AnswerQuestion, IngestDocument, EvaluateRetrieval, EvaluateAnswer)
        |
        v
Dominio RAG (Chunk, Query, RRF, expansión léxica) + puertos
        |
        +--> pgvector (ChunkRepository)
        +--> índice BM25 (LexicalIndexPort)
        +--> Ollama (EmbeddingPort, LlmPort)
        +--> Cross-Encoder (RerankerPort)
```

El composition root vive en `gateway/rag/composition.py` (importado desde
`gateway/main.py`). `RAGService` queda como fachada para no reescribir de golpe
las rutas HTTP; el contrato `/api/v1` y el frontend no cambian.

No existen proxies de inferencia o retrieval, workers de ingesta, Redis, MQTT ni
endpoints internos entre servicios.

## Documentos históricos

PostgreSQL conserva metadatos, chunks y embeddings ya existentes para que el RAG y
las citas continúen funcionando. El endpoint `GET /api/v1/documents` es de solo
lectura y no abre el fichero original.

El sistema ya no ofrece subida, almacenamiento, descarga, eliminación física,
procesamiento ni reindexado documental. Los directorios históricos `storage/`,
`gateway/services/extracted_md/`, BM25 y Chroma no se borran, pero el runtime no
los usa para aceptar documentos nuevos.

## Aislamiento

Las consultas densas filtran por `tenant_id` y opcionalmente por base de
conocimiento. La autorización del catálogo documental valida la membresía activa
de la organización antes de devolver metadatos.

## Límites

Es un prototipo funcional contenedorizado. Los modelos e imágenes con tags
flotantes, la ausencia de alta disponibilidad y la descarga inicial del reranker
impiden considerarlo un despliegue productivo endurecido.
