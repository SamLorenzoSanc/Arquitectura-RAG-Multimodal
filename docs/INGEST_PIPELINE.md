# Pipeline de ingesta

## Flujo documental

```text
archivo
  -> almacenamiento y registro Document
  -> parser según extensión
  -> Markdown normalizado
  -> división por encabezados
  -> chunks de 1000 caracteres, overlap 150
  -> título/resumen generados por Ollama
  -> embeddings por lotes de 10
  -> Chunk + Embedding en PostgreSQL/pgvector
  -> reconstrucción BM25 del tenant
```

La factoría observada asigna:

- PDF, DOC/DOCX, PPT/PPTX, XLSX, EPUB y HTML a `LlamaParseParser`;
- Markdown a `MarkdownParser`;
- texto plano a `TextParser`;
- PNG, JPG/JPEG y WebP a `ImageParser`;
- formatos de vídeo reconocidos a un flujo específico anterior a la factoría.

`LlamaParseParser` puede depender de `LLAMA_CLOUD_API_KEY`. No afirme procesamiento completamente local para esos formatos sin verificar qué parser se ejecutó.

## Chunking y enriquecimiento

Primero se preservan encabezados `#`, `##` y `###` mediante `MarkdownHeaderTextSplitter`. Después, `RecursiveCharacterTextSplitter` aplica:

- `chunk_size=1000`;
- `chunk_overlap=150`.

La unidad es carácter, no token. Cada chunk se enriquece con un título de 3–5 palabras y un resumen de 1–2 frases mediante el modelo `RAG_GENERATION_MODEL` (`llama3` por defecto). Para embedding se concatena título, resumen y texto original.

El enriquecimiento de todos los chunks se lanzaba con `asyncio.gather` sin límite de concurrencia en la revisión; documentos grandes pueden saturar Ollama o memoria.

## Embeddings y persistencia

`RAG_EMBEDDING_MODEL` usa `qwen3-embedding:latest` por defecto. Los textos se envían en lotes de 10 a la API OpenAI-compatible de Ollama. Cada vector queda asociado al chunk y registra el nombre del modelo.

La dimensión no está codificada en el servicio y depende del modelo resuelto. Debe coincidir con la columna pgvector creada por el esquema de base de datos; verifíquese en la instancia usada para el experimento.

Tras guardar los chunks, se reconstruye todo el índice BM25 del tenant en un fichero temporal y se reemplaza atómicamente.

## Vídeo

El vídeo sigue:

1. FFmpeg extrae WAV mono PCM a 16 kHz.
2. faster-whisper transcribe en español con VAD y `beam_size=5`.
3. Ollama genera título, resumen y puntos clave.
4. Se crea Markdown con timestamps y transcripción completa.
5. Continúa el pipeline documental común.

Aunque existen variables `WHISPER_DEVICE` y `WHISPER_COMPUTE_TYPE`, el constructor revisado fuerza `device="cuda"` y `compute_type="float16"`. En CPU esa ruta puede fallar; documentar las variables como plenamente efectivas sería incorrecto hasta corregirlo.

## Imágenes y multimodalidad

La factoría admite imágenes y documentos complejos, pero el resultado indexado es Markdown/texto y la consulta RAG opera sobre embeddings textuales. El vídeo también se reduce a transcripción textual.

Por tanto, la descripción defendible en la memoria es:

> El prototipo dispone de ingesta multimodal que transforma documentos, imágenes y vídeo a representaciones textuales; la evaluación versionada mide retrieval y generación sobre texto. No se ha demostrado una evaluación separada de comprensión visual end-to-end.

## Trazabilidad y artefactos

Se conserva:

- el documento original bajo `storage/`;
- Markdown extraído bajo `gateway/services/extracted_md/`;
- `document_id`, `chunk_id`, `knowledge_base_id`, posición, fuente y MIME;
- embeddings en PostgreSQL;
- BM25 por tenant.

La página original no aparece garantizada de forma uniforme en los metadatos del pipeline revisado. No prometa cita de página automática para todos los formatos sin una prueba de parser y persistencia de esa metadata.

## Variables

| Variable | Predeterminado | Uso |
|---|---|---|
| `RAG_GENERATION_MODEL` | `llama3` | enriquecimiento y resumen |
| `RAG_EMBEDDING_MODEL` | `qwen3-embedding:latest` | embeddings |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | API Ollama |
| `OLLAMA_API_KEY` | `ollama` | clave ficticia requerida por cliente |
| `WHISPER_MODEL` | `small` | modelo de transcripción |
| `WHISPER_DEVICE` | `auto` | declarada, pero no respetada por el constructor revisado |
| `WHISPER_COMPUTE_TYPE` | `auto` | declarada, pero no respetada por el constructor revisado |
| `VIDEO_TMP_DIR` | `gateway/services/video_tmp` | WAV temporal |
| `LLAMA_CLOUD_API_KEY` | sin valor | parsing con LlamaParse |
