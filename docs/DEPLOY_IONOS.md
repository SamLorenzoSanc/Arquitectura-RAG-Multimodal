# Despliegue IONOS

El workflow `.github/workflows/deploy-ionos.yml` construye y publica solo dos
imágenes propias:

- `agrops-api`, desde `gateway/`;
- `agrops-frontend`, desde `frontend/agrops/`.

Después copia `docker-compose.prod.yaml` y `postgres/` al VPS, descarga las
imágenes y ejecuta Compose. PostgreSQL/pgvector y Ollama proceden de sus imágenes
oficiales.

## Secretos de GitHub

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `VITE_API_URL`
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_APP_DIR`

El VPS debe disponer de un `.env` no versionado con credenciales de PostgreSQL,
`DATABASE_URL`, `SECRET_KEY` y la configuración funcional de RAG. No necesita
variables de microservicios, Redis, MQTT ni almacenamiento documental.

## Flujo

```text
push main
  -> build/push API y frontend
  -> copia Compose y SQL
  -> docker compose pull
  -> docker compose up -d --remove-orphans
```

`--remove-orphans` retira contenedores del despliegue distribuido anterior sin
eliminar los volúmenes declarados de PostgreSQL u Ollama.
