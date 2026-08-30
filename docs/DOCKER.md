# Ejecución con Docker

## Servicios

Ambos Compose definen únicamente:

- `frontend`: React compilado y servido por Nginx;
- `api`: monolito FastAPI;
- `postgres`: PostgreSQL con pgvector;
- `ollama`: inferencia local;
- `migrate`: job puntual de migraciones.

No se despliegan Redis, Mosquitto, workers ni microservicios de inferencia,
retrieval, telemetría o notificaciones.

## Variables

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=agrops
DATABASE_URL=postgresql+asyncpg://postgres:change-me@postgres:5432/agrops
SECRET_KEY=replace-with-a-long-random-secret
OLLAMA_API_KEY=ollama
RAG_GENERATION_MODEL=llama3.2:latest
RAG_EMBEDDING_MODEL=nomic-embed-text
FRONTEND_HOST_PORT=80
```

Compose fija internamente `OLLAMA_BASE_URL=http://ollama:11434/v1` y
`OLLAMA_URL=http://ollama:11434` para el contenedor API. Fuera de Docker use
`http://localhost:11434/v1`.

No configure variables `STORAGE_*`, `AWS_*`, `AZURE_*`, `REDIS_URL`,
`INFERENCE_URL`, `RETRIEVAL_URL` ni tokens internos: ya no forman parte del
runtime.

## Desarrollo

```powershell
Copy-Item .env.example .env
.\scripts\demo_up.ps1
# Detecta GPU NVIDIA sola y activa docker-compose.gpu.yaml.
# Forzar CPU:
.\scripts\demo_up.ps1 -NoGpu
# Forzar GPU:
.\scripts\demo_up.ps1 -Gpu
```

O a mano:

```powershell
docker compose config
docker compose build
# Con GPU (si hay NVIDIA Container Toolkit):
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
# Solo CPU:
docker compose up -d
```

El servicio `ollama-init` descarga `nomic-embed-text` (embeddings) y
`llama3.2:latest` (generación) y deja la generación caliente. El gateway,
al arrancar, completa el warm-up de embedding + LLM (`RAG_INFERENCE_WARMUP=true`)
para que el primer chat no pague cold start. Endpoint manual:
`POST /api/v1/health/warmup`.

Si hace falta repetir el pull a mano:

```powershell
docker compose exec ollama ollama pull llama3.2:latest
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama list
docker compose exec ollama ollama ps   # debe mostrar 100% GPU si CUDA está activo
```

Accesos: frontend `http://localhost` (o el puerto de `FRONTEND_HOST_PORT`),
API/OpenAPI `http://localhost:8000/docs`, PostgreSQL `localhost:5432` y Ollama
`localhost:11434`. El Compose por defecto no exige GPU; `demo_up.ps1` la activa
automáticamente si `nvidia-smi` y el runtime `nvidia` de Docker están disponibles.

```powershell
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
```

El `docker-compose.yaml` local publica esos cuatro puertos. `docker-compose.prod.yaml`
también los expone en este prototipo para poder inspeccionar la base y Ollama en el host.

## Producción

`docker-compose.prod.yaml` publica solo el puerto 80. Nginx del frontend sirve
la SPA y proxifica `/api/` al gateway; PostgreSQL y Ollama no se exponen al host.
Las imágenes propias son `samuelzo/agrops-api` y `samuelzo/agrops-frontend`
(variable `DOCKERHUB_USER`, por defecto `samuelzo`), o se construyen en el
servidor con `build`.

- API: https://hub.docker.com/repository/docker/samuelzo/agrops-api
- Frontend: https://hub.docker.com/repository/docker/samuelzo/agrops-frontend

Guía IONOS: [DEPLOY_IONOS.md](DEPLOY_IONOS.md).

```bash
docker compose -f docker-compose.prod.yaml build
docker compose -f docker-compose.prod.yaml up -d --remove-orphans
```

Los volúmenes persistentes son `postgres_data` y `ollama_data`. No existe volumen
de almacenamiento documental. `docker compose down -v` elimina datos persistentes
y solo debe usarse cuando esa pérdida sea intencionada.
