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
# Con GPU NVIDIA (opcional):
.\scripts\demo_up.ps1 -Gpu
```

O a mano:

```powershell
docker compose config
docker compose build
docker compose up -d
```

El servicio `ollama-init` descarga `nomic-embed-text` (embeddings) y
`llama3.2:latest` (generación) la primera vez. Hasta que termine, el chat
responderá que el modelo no está disponible. Si hace falta repetirlo a mano:

```powershell
docker compose exec ollama ollama pull llama3.2:latest
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama list
```

Accesos: frontend `http://localhost` (o el puerto de `FRONTEND_HOST_PORT`),
API/OpenAPI `http://localhost:8000/docs`, PostgreSQL `localhost:5432` y Ollama
`localhost:11434`. El Compose por defecto no exige GPU; para usarla:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
```

El `docker-compose.yaml` local publica esos cuatro puertos. `docker-compose.prod.yaml`
también los expone en este prototipo para poder inspeccionar la base y Ollama en el host.

## Producción

`docker-compose.prod.yaml` publica solo el puerto 80. Nginx del frontend sirve
la SPA y proxifica `/api/` al gateway; PostgreSQL y Ollama no se exponen al host.
Las imágenes propias son `${DOCKERHUB_USER}/agrops-api` y
`${DOCKERHUB_USER}/agrops-frontend` (o se construyen en el servidor con `build`).

Guía IONOS: [DEPLOY_IONOS.md](DEPLOY_IONOS.md).

```bash
docker compose -f docker-compose.prod.yaml build
docker compose -f docker-compose.prod.yaml up -d --remove-orphans
```

Los volúmenes persistentes son `postgres_data` y `ollama_data`. No existe volumen
de almacenamiento documental. `docker compose down -v` elimina datos persistentes
y solo debe usarse cuando esa pérdida sea intencionada.
