# Estado de la ingesta documental

La ingesta está deshabilitada y retirada del runtime.

El monolito no acepta archivos nuevos ni proporciona almacenamiento, descarga,
procesamiento, progreso, reintentos o reindexado. También se retiraron los
workers, la cola Redis, los endpoints internos y los servicios de storage/ingesta.

## Compatibilidad histórica

Se conservan sin modificar los datos que ya existían:

- metadatos de documentos en PostgreSQL;
- chunks y embeddings usados por pgvector;
- fuentes vinculadas a conversaciones;
- artefactos locales bajo `storage/`, `extracted_md`, BM25 o Chroma.

El catálogo `GET /api/v1/documents?knowledge_base_id=...` solo devuelve metadata
autorizada. El RAG continúa consultando chunks y embeddings históricos, pero no
lee ni sirve el original.

## Funcionalidad retirada

- `POST /api/v1/documents`;
- `POST /api/v1/documents/{id}/index`;
- `GET /api/v1/documents/{id}/progress`;
- `DELETE /api/v1/documents/{id}`;
- rutas internas de procesamiento y eventos;
- backends local, Azure, S3/MinIO y sus variables;
- parsing de nuevas cargas, extracción a Markdown y creación de nuevos índices.

Para incorporar un corpus nuevo será necesario hacerlo fuera de esta aplicación
o diseñar explícitamente una nueva fuente de datos; no existe un mecanismo de
compatibilidad oculto.
