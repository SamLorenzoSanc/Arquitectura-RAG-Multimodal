# AgroRAG: asistente RAG agrícola multimodal

[![Coverage Status](https://coveralls.io/repos/github/SamLorenzoSanc/Arquitectura-RAG-Multimodal/badge.svg?branch=main)](https://coveralls.io/github/SamLorenzoSanc/Arquitectura-RAG-Multimodal?branch=main)

Prototipo funcional contenedorizado desarrollado como Trabajo Fin de Máster. Su objetivo es estudiar si una arquitectura Retrieval-Augmented Generation (RAG) puede **reducir o mitigar las alucinaciones en los casos evaluados**, no eliminarlas de forma general.

La interfaz React/Vite consume un monolito FastAPI. El gateway persiste usuarios y datos de negocio en PostgreSQL con pgvector; consulta fragmentos y embeddings documentales históricos; mantiene un índice BM25 por tenant; fusiona recuperación densa y léxica mediante Reciprocal Rank Fusion (RRF); reordena candidatos con un Cross-Encoder; y genera respuestas directamente con Ollama.

> Compatibilidad documental: se conserva el RAG y la visualización de fuentes existentes, pero el runtime ya no admite subida, almacenamiento, descarga, procesamiento o reindexado de archivos.

## Arquitectura real

```text
React 19 + Vite 8
        |
        | HTTP /api/v1
        v
FastAPI gateway
  |-- autenticación JWT y selección de tenant/knowledge base
  |-- retrieval: pgvector + BM25 -> RRF -> Cross-Encoder
  |-- generación y juez automático -> Ollama (API compatible OpenAI)
        |
        +--> PostgreSQL + pgvector
        +--> índices BM25 locales por tenant
```

Detalles: [arquitectura](docs/ARCHITECTURE.md), [pipeline RAG](docs/RAG_PIPELINE.md), [estado de ingesta](docs/INGEST_PIPELINE.md), [evaluación](docs/EVALUATION.md) y [Docker](docs/DOCKER.md).

## Configuración verificada en el código

| Parámetro | Valor por defecto o verificado | Observación |
|---|---|---|
| Generación RAG | `llama3`; chat web `llama3.2:latest`; evaluación `llama3.2` | Hay varios puntos de entrada; registrar el tag resuelto por Ollama en cada experimento. |
| Embedding | `qwen3-embedding:latest` | Tag móvil; la versión/peso exacto no queda fijado. |
| Cross-Encoder | `BAAI/bge-reranker-v2-m3` | `max_length=512`, lote 16. Revisión/peso exacto no fijado. |
| Chunking | 1000 caracteres, solapamiento 150 | `RecursiveCharacterTextSplitter`, después de dividir por encabezados Markdown. |
| Recuperación | dense top 10 + BM25 top 10 | RRF `k=60`, hasta 15 candidatos. |
| Top-k final | 3 en `RAGService`; 5 en simulador/evaluación por defecto | El requisito experimental `top-k=10` solo coincide con `retrieval_k`/`bm25_k`, no con los chunks finales. |
| Temperatura | No verificable en el pipeline principal | `ChatRequest` declara `0`, pero `RAGService` no la propaga a Ollama. No atribuir resultados a temperatura 0. |
| Python | `>=3.12`; imagen `python:3.12-slim` | Dependencias exactas se resuelven desde `gateway/uv.lock`. |
| PostgreSQL | imagen `pgvector/pgvector:pg18` | El tag menor no está fijado. |
| Ollama | imagen `ollama/ollama:latest` | Versión exacta no fijada. |

## Inicio con Docker (Windows)

Requisitos: Docker Desktop con Compose v2 y los modelos de Ollama disponibles. Cree `.env` en la raíz:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=agrops
DATABASE_URL=postgresql+asyncpg://postgres:change-me@postgres:5432/agrops
SECRET_KEY=change-me-with-a-long-random-value
OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_URL=http://ollama:11434
OLLAMA_API_KEY=ollama
RAG_GENERATION_MODEL=llama3
RAG_EMBEDDING_MODEL=qwen3-embedding:latest
```

La ruta de modelos de Ollama en `docker-compose.yaml` es actualmente específica de este equipo Windows. Ajústela antes de iniciar:

```powershell
docker compose build
docker compose up -d
docker compose ps
docker compose exec ollama ollama pull llama3
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull qwen3-embedding:latest
```

Servicios: frontend `http://localhost`, API `http://localhost:8000`, OpenAPI `http://localhost:8000/docs`, PostgreSQL `localhost:5432` y Ollama `localhost:11434`.

Consulte [docs/DOCKER.md](docs/DOCKER.md) para limitaciones conocidas y operación.

## Calidad (tests, cobertura, Doxygen)

- Guía: [docs/QUALITY.md](docs/QUALITY.md)
- Local: `.\scripts\run_quality.ps1` (pytest-cov + Doxygen si está instalado)
- CI: `.github/workflows/quality.yml` → Coveralls + artefacto Doxygen

## Despliegue VPS IONOS (CI/CD)

Flujo tipo Figura 4.2: GitHub Actions → Docker Hub → `docker compose` en el VPS.

- Guía: [docs/DEPLOY_IONOS.md](docs/DEPLOY_IONOS.md)
- Compose prod: `docker-compose.prod.yaml`
- Workflow: `.github/workflows/deploy-ionos.yml`

## Desarrollo local

Backend (PowerShell):

```powershell
cd gateway
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend\agrops
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

Para ejecutar el backend fuera de Docker, configure `DATABASE_URL` con `localhost` y `OLLAMA_BASE_URL=http://localhost:11434/v1`.

## Pruebas

```powershell
cd gateway
python -m pytest tests -q
```

La clasificación y los comandos unitarios, de integración y lentos están en [TESTING.md](TESTING.md). La configuración actual de `gateway/pyproject.toml` todavía indica `testpaths = ["test"]`; por eso los comandos documentados especifican `tests` explícitamente.

## Evaluación y evidencia disponible

El gateway implementa métricas propias de recuperación (Recall@1/@K, Precision@K, MRR, nDCG, cobertura de palabras clave, falsos positivos y latencia) y un LLM-as-a-Judge de precisión, exhaustividad y relevancia (1–5). `ragas` figura como dependencia, pero no hay imports ni ejecución RAGAS visible: **no se atribuyen resultados a RAGAS**.

El banco textual versionado contiene 21 filas, 19 preguntas únicas y siete categorías. El único artefacto comparativo incluido (`run_9`) contiene cuatro filas de categorías `general`/vacía y no respalda resultados para esas siete categorías ni una muestra de 150 preguntas. Véase [docs/EVALUATION.md](docs/EVALUATION.md).

## Estructura relevante

```text
frontend/agrops/       React/Vite
gateway/               API FastAPI, modelos, parsers, servicios y pruebas
gateway/services/      RAG, forecast, base de datos y lógica monolítica
postgres/              inicialización de PostgreSQL/pgvector
storage/               datos históricos conservados, fuera del runtime
docs/                  documentación técnica y auditoría de memoria
src/                   evaluador/prototipo legado; no es la fuente de verdad
```

La fuente de verdad operativa es `gateway/`. `src/` conserva un evaluador anterior y no debe mezclarse con resultados del gateway sin una migración metodológica explícita.

## Seguridad y madurez

El sistema puede ejecutarse localmente, pero eso no acredita por sí solo cumplimiento GDPR, AI Act ni preparación productiva. Cambie `SECRET_KEY`, no publique `.env`, restrinja CORS y puertos, proteja los datos históricos conservados y use secretos gestionados antes de cualquier despliegue compartido.

## Memoria TFM

No se encontró una fuente editable `.tex`, `.md` o `.docx` de la memoria en el workspace; sí existen PDF de corpus, que no se modificaron. Las correcciones editoriales, metodológicas y los campos bloqueados por falta de evidencia están en [docs/THESIS_REVISION_CHECKLIST.md](docs/THESIS_REVISION_CHECKLIST.md).
