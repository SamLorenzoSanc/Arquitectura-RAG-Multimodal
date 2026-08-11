# Despliegue automatizado en VPS IONOS (Figura 4.2)

Pipeline:

```text
Desarrollador ──push──► GitHub
                          │
                          ▼
                   GitHub Actions
                   (build imágenes)
                          │
                          ▼
                     Docker Hub
                          │
                          ▼
              SSH → VPS 217.154.102.81
              docker compose -f docker-compose.prod.yaml up -d
                          │
                          ▼
         Contenedores: postgres, redis, mosquitto,
         ollama, inference, retrieval, ingest-worker,
         telemetry, api, frontend
```

## Requisitos previos (una vez)

### 1. VPS IONOS

- IP: `217.154.102.81` (o la que te den)
- Ubuntu 22.04/24.04 recomendado
- ≥ 8 GB RAM si vas a correr Ollama en CPU (16 GB mejor)
- Sin GPU → modelos pequeños y latencia alta (aceptable en demo)

```bash
# Desde tu PC
scp scripts/vps_bootstrap.sh root@217.154.102.81:/tmp/
ssh root@217.154.102.81 'bash /tmp/vps_bootstrap.sh'
ssh root@217.154.102.81 'nano /opt/agrops/.env'
```

### 2. Docker Hub

1. Crea cuenta / Access Token en https://hub.docker.com
2. Repos se crean al primer push (`agrops-api`, `agrops-frontend`, …)

### 3. Secrets en GitHub

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Ejemplo / valor |
|---|---|
| `DOCKERHUB_USERNAME` | tu usuario Docker Hub |
| `DOCKERHUB_TOKEN` | access token Docker Hub |
| `VPS_HOST` | `217.154.102.81` |
| `VPS_USER` | `root` (o usuario con docker) |
| `VPS_SSH_KEY` | clave privada SSH completa (`-----BEGIN …`) |
| `VPS_APP_DIR` | `/opt/agrops` |
| `VPS_PORT` | `22` (opcional) |
| `VITE_API_URL` | `http://217.154.102.81:8000/api/v1` |

Generar clave solo para deploy (en tu PC):

```powershell
ssh-keygen -t ed25519 -f agrops_deploy -N ""
# Copia la pública al VPS
type agrops_deploy.pub | ssh root@217.154.102.81 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
# Pega el contenido de agrops_deploy (privada) en VPS_SSH_KEY
```

### 4. Firewall IONOS

En el panel IONOS / `ufw`: abre **22**, **80**, **8000**. No abras 5432 ni 6379 a Internet.

## Cómo se dispara

- Push a `main` / `master`, o
- Actions → **Deploy IONOS** → Run workflow

Workflow: `.github/workflows/deploy-ionos.yml`

## Tras el primer deploy

```bash
ssh root@217.154.102.81
cd /opt/agrops
docker compose -f docker-compose.prod.yaml ps
docker exec -it agrops-ollama ollama pull llama3.2
docker exec -it agrops-ollama ollama pull qwen3-embedding:latest
```

URLs:

- Frontend: http://217.154.102.81/
- API /docs: http://217.154.102.81:8000/docs

## Limitaciones realistas (TFM)

- Ollama en CPU en VPS barato será lento; para la defensa puedes dejar LLM en tu PC y apuntar `OLLAMA` remoto, o usar un VPS con más RAM.
- El workflow antiguo `deploy.yml` (Azure) no se usa; este es el de IONOS.
- `DATABASE_URL` en el `.env` del VPS debe apuntar al servicio `postgres` del compose (no a Render) si quieres datos locales en el servidor.

## Rollback rápido

```bash
cd /opt/agrops
export DOCKERHUB_USER=...
export IMAGE_TAG=<sha_anterior>
docker compose -f docker-compose.prod.yaml pull
docker compose -f docker-compose.prod.yaml up -d
```
