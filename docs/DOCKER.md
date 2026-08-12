# Ejecución con Docker en Windows

## Requisitos

- Windows 10/11 con Docker Desktop.
- Docker Compose v2 (`docker compose version`).
- Memoria y disco suficientes para Ollama, Cross-Encoder y PostgreSQL.
- GPU opcional; la ruta de vídeo revisada fuerza CUDA y no es portable a CPU.

## Variables de entorno

Cree `.env` en la raíz. No lo versiona ni reutilice credenciales de ejemplo:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=agrops
DATABASE_URL=postgresql+asyncpg://postgres:change-me@postgres:5432/agrops
SECRET_KEY=replace-with-a-long-random-secret

OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_URL=http://ollama:11434
OLLAMA_API_KEY=ollama
RAG_GENERATION_MODEL=llama3
RAG_EMBEDDING_MODEL=qwen3-embedding:latest
RETRIEVAL_CACHE_TTL=120

WHISPER_MODEL=small
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto

# Solo para parsers/rutas opcionales:
# LLAMA_CLOUD_API_KEY=
# AEMET_API_KEY=
# SENTINEL_CLIENT_ID=
# SENTINEL_CLIENT_SECRET=
# MARITIME_API_KEY=
# REEFER_IOT_API_KEY=
# WHATSAPP_API_URL=
# WHATSAPP_ACCESS_TOKEN=
```

`DATABASE_URL` debe usar hostname `postgres` desde el contenedor API; un backend ejecutado en Windows usa `localhost`.

## Ruta de modelos

El Compose auditado monta una ruta absoluta específica:

```yaml
C:\Users\Usuario\.ollama\models:/root/.ollama/models
```

Esto reduce portabilidad y puede no ser el directorio real de otro usuario. Cambie el lado izquierdo o sustituya el bind mount por un volumen nombrado. No asuma que el contenedor verá los modelos del Ollama instalado en el host.

## Arranque

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f api
```

Descargue los modelos dentro del contenedor si no están disponibles:

```powershell
docker compose exec ollama ollama pull llama3
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull qwen3-embedding:latest
docker compose exec ollama ollama list
```

Accesos:

- frontend: `http://localhost`;
- API/OpenAPI: `http://localhost:8000/docs`;
- Ollama: `http://localhost:11434`;
- PostgreSQL: `localhost:5432`.

## GPU (Docker Desktop + WSL2 + NVIDIA)

El cuello de botella del chat es Ollama. Sin GPU, verás `PROCESSOR 100% CPU` en `ollama ps`.

Checklist:

1. Drivers NVIDIA actualizados en Windows.
2. Docker Desktop → Settings → Resources → **WSL Integration** activada.
3. Docker Desktop → Settings → Resources → **Use GPU** / NVIDIA runtime disponible (`docker info` debe listar `Runtimes: ... nvidia`).
4. En `%UserProfile%\.wslconfig` (reiniciar WSL después):

```ini
[wsl2]
memory=24GB
processors=16
networkingMode=mirrored
```

5. Recrear Ollama con GPU:

```powershell
docker compose up -d ollama
docker compose exec ollama ollama ps
```

Si aparece `100% GPU` (o mezcla GPU), está bien. Si sigue en `100% CPU`, alternativa más fiable en Windows: instalar Ollama nativo, parar el contenedor `ollama` y apuntar la API a `http://host.docker.internal:11434/v1`.

## Base de datos

PostgreSQL usa el volumen `postgres_data` y monta, en este orden:

1. `postgres/init/00_create_dump_role.sql` — crea el rol `palmero` (owner del dump de Render)
2. `postgres/seed.sql` — esquema + datos
3. migraciones `001`–`003`

Los scripts de `/docker-entrypoint-initdb.d` **solo se ejecutan al crear un volumen vacío**.

Si ves `role "palmero" does not exist` o `Skipping initialization`, el volumen quedó a medias: hay que recrearlo.

```powershell
docker compose down
docker volume ls
docker compose down -v
docker compose up -d postgres
docker compose logs -f postgres
```

`down -v` elimina los datos del volumen; úselo solo cuando la pérdida sea intencionada. Para cambios de esquema en una base existente se requiere una migración, no editar únicamente `seed.sql`.

## Estado y diagnóstico

```powershell
docker compose ps
docker compose logs postgres
docker compose logs ollama
docker compose logs api
docker compose logs frontend
docker compose exec postgres pg_isready -U $env:POSTGRES_USER
docker compose exec ollama ollama list
```

El Compose revisado tiene healthcheck para PostgreSQL, pero no para Ollama, API ni frontend. `depends_on` solo expresa orden/dependencia y no garantiza que todos estén listos; la API puede iniciar antes de Ollama.

## Limitaciones verificadas

- `ollama/ollama:latest` y la imagen `uv:latest` no fijan versión/digest.
- `postgres:15` fija la mayor, no el parche.
- La API necesita acceso de red al descargar por primera vez el Cross-Encoder desde Hugging Face.
- La ruta LlamaParse puede salir a un servicio cloud.
- Ollama y PostgreSQL exponen puertos al host sin restricciones adicionales.
- No se observó política de backup, rotación de logs o secretos gestionados.
- No hay evidencia de uso efectivo de HNSW.

Por estas razones, describa el despliegue como **prototipo funcional contenedorizado**, no como entorno productivo real.

## Parada

```powershell
docker compose stop
docker compose down
```

`down` conserva el volumen por defecto. Evite `down -v` salvo reinicio destructivo deliberado.
