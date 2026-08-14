# Bootstrap del VPS IONOS (ejecutar UNA vez por SSH)
# Uso:
#   scp scripts/vps_bootstrap.sh root@217.154.102.81:/tmp/
#   ssh root@217.154.102.81 'bash /tmp/vps_bootstrap.sh'

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/agrops}"
DOCKERHUB_USER="${DOCKERHUB_USER:-}"

echo "==> Actualizar sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git ufw

echo "==> Instalar Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

echo "==> Docker Compose plugin"
docker compose version >/dev/null

echo "==> Directorio app ${APP_DIR}"
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/postgres"

echo "==> Firewall (80 HTTP, 22 SSH)"
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw --force enable || true

echo "==> Placeholder .env (EDITAR antes del primer deploy)"
if [ ! -f "${APP_DIR}/.env" ]; then
  cat > "${APP_DIR}/.env" <<'EOF'
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
EOF
  chmod 600 "${APP_DIR}/.env"
  echo "Creado ${APP_DIR}/.env — edítalo ahora."
fi

echo "==> Listo. Siguiente:"
echo "  1) nano ${APP_DIR}/.env"
echo "  2) Configura secrets en GitHub y lanza el workflow Deploy IONOS"
echo "  3) Tras el primer up: docker exec agrops-ollama ollama pull llama3.2"
echo "                       docker exec agrops-ollama ollama pull qwen3-embedding:latest"
