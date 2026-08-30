# Servidores MCP de AgroPS

Dos servidores **stdio** propios para Cursor. No forman parte de la imagen Docker del gateway: Cursor los lanza en el host y ellos hablan con el stack ya levantado (`localhost:8000` y `localhost:5432`).

La carpeta se llama `mcp_servers` a propósito: si se llamara `mcp/` taparía el paquete PyPI `mcp` al importar.

| Servidor | Proceso | Para qué |
|---|---|---|
| `agrops` | `mcp_servers/agrops_gateway.py` | Salud, retrieve híbrido, documentos, índice, config RAG |
| `agrops-postgres` | `mcp_servers/agrops_postgres.py` | SQL de solo lectura sobre el corpus (sin `embeddings.vector`) |

## Requisitos

- Python 3.10+ (`python` en el PATH)
- Stack AgroPS en marcha (`docker compose up` o gateway + Postgres locales)
- Credenciales de un usuario de la API en `.env` (no en `mcp.json`)

```powershell
python -m pip install -r mcp_servers/requirements.txt
python mcp_servers/tests/test_postgres.py
```

## Variables (`.env`)

```dotenv
AGROPS_BASE_URL=http://localhost:8000
AGROPS_MCP_EMAIL=tu-usuario@ejemplo.com
AGROPS_MCP_PASSWORD=tu-password
# Alternativa al login: AGROPS_MCP_TOKEN=eyJ...

# DSN desde el host (no uses el hostname Docker `postgres` ni `+asyncpg`)
MCP_DATABASE_URL=postgresql://postgres:change-me@localhost:5432/agrops
```

Si no defines `MCP_DATABASE_URL`, el servidor Postgres monta el DSN con `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` y host `localhost`. Si solo existe `DATABASE_URL` de Compose, se reescribe `+asyncpg` → `postgresql` y `postgres` → `localhost`.

## Activar en Cursor

La configuración del workspace está en [`.cursor/mcp.json`](../.cursor/mcp.json). Tras instalar dependencias:

1. Recarga la ventana o abre **Customize → MCP**.
2. Comprueba el punto verde en `agrops` y `agrops-postgres`.
3. Si falla, **Output → MCP Logs**.

Ejemplos de uso en el chat:

- «Usa `ready` y `corpus_stats`»
- «Con `retrieve`, pregunta qué es el POSEI en Canarias»
- «Lista las tablas y describe `embedding_index_state`»

`retrieve` consume embeddings/Ollama; no llama al LLM de generación.

`corpus_stats` no hace `COUNT(*)` sobre `embeddings` (vectores 4096-d). Usa `pg_class.reltuples` (estimación de ANALYZE) en una sola consulta y reutiliza la conexión TCP del proceso MCP.
