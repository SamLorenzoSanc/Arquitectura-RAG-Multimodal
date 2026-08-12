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

El gateway concentra autenticación JWT, multitenancy, CRUD agrícola, logística,
forecast, chat, evaluación y RAG híbrido. La recuperación se ejecuta en proceso:
dense sobre pgvector, BM25 por tenant, fusión RRF y reranking opcional. Generación y
embeddings consumen Ollama directamente mediante `OLLAMA_BASE_URL`.

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
