# Despliegue IONOS

El workflow `.github/workflows/deploy-ionos.yml` construye y publica solo dos
imágenes propias:

- `agrops-api`, desde `gateway/`;
- `agrops-frontend`, desde `frontend/agrops/` (Nginx sirve la SPA y proxifica
  `/api/` hacia el contenedor `api`).

Después copia `docker-compose.prod.yaml` y `postgres/` al VPS, descarga las
imágenes y ejecuta Compose. PostgreSQL/pgvector y Ollama proceden de sus imágenes
oficiales. El único puerto público es **80**.

## Secretos de GitHub

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_APP_DIR` (por ejemplo `/opt/agrops`)

`VITE_API_URL` ya no hace falta: el frontend se construye con `/api/v1` y Nginx
reenvía al gateway en la red interna de Docker.

## `.env` en el VPS (no versionado)

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CAMBIAR_PASSWORD_FUERTE
POSTGRES_DB=agrops
DATABASE_URL=postgresql+asyncpg://postgres:CAMBIAR_PASSWORD_FUERTE@postgres:5432/agrops
SECRET_KEY=CAMBIAR_SECRET_LARGO_ALEATORIO
OLLAMA_API_KEY=ollama
DOCKERHUB_USER=TU_USUARIO_DOCKERHUB
IMAGE_TAG=latest
RAG_GENERATION_MODEL=llama3.2:latest
RAG_EMBEDDING_MODEL=qwen3-embedding:latest
CORS_ORIGINS=http://TU_IP_O_DOMINIO
```

## Arranque único del VPS

```bash
scp scripts/vps_bootstrap.sh root@VPS_HOST:/tmp/
ssh root@VPS_HOST 'bash /tmp/vps_bootstrap.sh'
ssh root@VPS_HOST 'nano /opt/agrops/.env'
```

## Flujo CI/CD

```text
push main  (o workflow_dispatch)
  -> build/push API y frontend a Docker Hub
  -> copia Compose y SQL
  -> docker compose pull
  -> docker compose up -d --remove-orphans
```

La primera vez Ollama descarga los modelos (`ollama-init`). Hasta que termine,
el chat puede responder que el modelo no está disponible.

## Despliegue manual en el servidor (sin GitHub Actions)

Con el repositorio clonado y el `.env` listo:

```bash
docker compose -f docker-compose.prod.yaml build
docker compose -f docker-compose.prod.yaml up -d
docker compose -f docker-compose.prod.yaml ps
```

## Límites

Es un prototipo funcional contenedorizado: HTTP sin TLS, un solo nodo, tags
flotantes de modelos y sin alta disponibilidad. No equivale a un endurecimiento
productivo (GDPR, AI Act, backups, HTTPS).
