# Calidad de software: tests, cobertura, Coveralls y Doxygen

Este documento describe cómo **testear** el gateway y publicar **cobertura** (Coveralls) y **documentación de API** (Doxygen) para el TFM.

## Qué mide cada herramienta

| Herramienta | Rol |
|---|---|
| **pytest** | Ejecuta tests (unitarios / integración) |
| **pytest-cov / coverage.py** | % de líneas/ramas ejecutadas por los tests |
| **Coveralls** | Dashboard cloud del historial de cobertura (CI) |
| **Doxygen** | Documentación HTML/XML del código (docstrings + estructura) |

> Doxygen **no** es cobertura de tests: documenta la API. Coveralls **sí** muestra cobertura de ejecución.

## Ejecutar tests con cobertura (local)

Desde `gateway/` (PowerShell):

```powershell
cd gateway
uv sync --group dev
$env:PYTHONPATH = (Get-Location).Path
uv run pytest -q tests/unit -m unit --confcutdir=tests/unit `
  --cov=services.evaluation_metrics `
  --cov=services.rag_dataset_service `
  --cov-report=term-missing `
  --cov-report=xml:coverage.xml `
  --cov-report=html:htmlcov `
  --cov-fail-under=40
```

O desde la raíz:

```powershell
.\scripts\run_quality.ps1
```

Informes:

- HTML: `gateway/htmlcov/index.html`
- XML (Coveralls/CI): `gateway/coverage.xml`

El umbral del **núcleo medido** es **40%** (`--cov-fail-under=40`). El `fail_under` global del paquete completo en `pyproject.toml` es 15% (aún hay módulos grandes sin unit tests: ingest, Whisper, agentic…).

## Coveralls

1. Entra en [coveralls.io](https://coveralls.io) y vincula el repositorio GitHub.
2. En GitHub → **Settings → Secrets and variables → Actions → New repository secret**:
   - Name: `COVERALLS_REPO_TOKEN`
   - Value: el token que te da Coveralls (nunca lo subas al código ni al chat).
3. El workflow `.github/workflows/quality.yml` lee `secrets.COVERALLS_REPO_TOKEN` y sube `coverage.xml` en cada push/PR a `main`/`master`.
4. Badge:

```markdown
[![Coverage Status](https://coveralls.io/repos/github/SamLorenzoSanc/Arquitectura-RAG-Multimodal/badge.svg?branch=main)](https://coveralls.io/github/SamLorenzoSanc/Arquitectura-RAG-Multimodal?branch=main)
```

> Si el token se filtró (chat, commit, captura), **rótalo** en Coveralls y actualiza el secret de GitHub.
## Doxygen

Requisitos: [Doxygen](https://www.doxygen.nl/) instalado (`doxygen` en PATH).

```powershell
# Desde la raíz del repo
doxygen Doxyfile
# Abrir
start docs\doxygen\html\index.html
```

En CI, el job `doxygen` publica el artefacto `doxygen-html`.

## Marcadores de tests

- `unit` — sin Postgres/Ollama (CI por defecto)
- `integration` — requiere DB (`workflow_dispatch` en `python-tests.yml`)
- `slow` — modelos / rendimiento

## Ampliación recomendada (TFM)

1. Subir `fail_under` a 40 → 60 cuando el núcleo `services/` esté cubierto.
2. Añadir tests de `routes` con `TestClient` y mocks.
3. Tests de rutas del monolito con dependencias de PostgreSQL/Ollama simuladas.
4. (Opcional) Vitest + Coveralls para el frontend React.
