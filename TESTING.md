# Guía de pruebas

La suite del backend está en `gateway/tests`. Los comandos siguientes usan la ruta explícita porque `gateway/pyproject.toml` contiene actualmente `testpaths = ["test"]` (singular), que no coincide con el directorio real.

## Preparación en Windows

```powershell
cd gateway
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

El proyecto exige Python 3.12 o posterior. La instalación editable incluye `pytest` y `pytest-asyncio`. Para reproducir exactamente el entorno bloqueado, instale `uv` y ejecute `uv sync --frozen`.

## Suite rápida

```powershell
cd gateway
python -m pytest tests -q
```

Los tests existentes usan SQLite en memoria y sustituciones de dependencias cuando es posible. Algunos módulos importan dependencias pesadas aun cuando el test las simula.

Ejemplos focalizados:

```powershell
python -m pytest tests\parsers -q
python -m pytest tests\services -q
python -m pytest tests\api -q
python -m pytest tests\api\test_evaluation_endpoints.py -q
python -m pytest tests\parsers\test_pdf_parser.py -q
```

## Categorías

La clasificación objetivo del plan es:

- `unit`: funciones puras, esquemas, normalización, métricas y parsers aislados.
- `integration`: FastAPI + base de datos/pgvector, filesystem o servicios reales.
- `slow`: modelos, Ollama, Cross-Encoder, OCR/Whisper, corpus completo o rendimiento.

En la revisión del 10-08-2026 solo se observaron marcas `pytest.mark.asyncio`; no estaban registrados `unit`, `integration` ni `slow`. Hasta que el worker de tests añada y registre esas marcas, use selección por directorio o nombre. Después, los comandos esperados son:

```powershell
python -m pytest tests -m unit -q
python -m pytest tests -m integration -q
python -m pytest tests -m slow -q
python -m pytest tests -m "not integration and not slow" -q
```

No se presentan estos filtros como operativos hasta comprobar la configuración final de `pyproject.toml`.

## Integración con Docker

Levante dependencias desde la raíz:

```powershell
docker compose up -d postgres ollama
docker compose ps
```

Configure el proceso local:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:change-me@localhost:5432/agrops"
$env:OLLAMA_BASE_URL = "http://localhost:11434/v1"
$env:OLLAMA_URL = "http://localhost:11434"
$env:OLLAMA_API_KEY = "ollama"
cd gateway
python -m pytest tests -m integration -q
```

Use credenciales iguales a las de `.env`. Las pruebas que requieran generación/embeddings también necesitan los modelos declarados por el test (`llama3`, `llama3.2` y/o `qwen3-embedding:latest`).

## Diagnóstico y cobertura

```powershell
python -m pytest tests -vv --maxfail=1
python -m pytest tests -k evaluation -q
python -m pytest tests --collect-only -q
```

No hay dependencia/configuración de cobertura verificada. No use `--cov` hasta instalar y registrar `pytest-cov`.

## Qué no valida la suite rápida

- Disponibilidad y versión real de Ollama/modelos.
- Uso efectivo de un índice vectorial HNSW mediante `EXPLAIN`.
- Aislamiento multitenant frente a una instancia PostgreSQL real.
- Calidad de OCR/visión/vídeo end-to-end.
- Resultados de RAGAS (no existe integración visible).
- Reproducción de la evaluación de siete categorías o de una supuesta muestra de 150.

## CI

Existe `.github/workflows/python-tests.yml`, gestionado por otro worker. Antes de confiar en CI, confirme que:

1. usa Python compatible con `requires-python >=3.12`;
2. ejecuta `gateway/tests`, no `gateway/test`;
3. separa suite rápida de integración/lenta;
4. no declara exitosas pruebas de Ollama/pgvector si esos servicios no están disponibles;
5. conserva artefactos y parámetros de cualquier evaluación de calidad.

## Criterio de reproducibilidad

Para cada ejecución de evaluación registre commit, fecha, fingerprint del dataset, tenant/knowledge base, modelos y tags/digests, versiones de Ollama y dependencias, parámetros de retrieval, temperatura efectiva, hardware, semilla cuando aplique y latencias. Sin esos datos, una tabla de resultados no es plenamente reproducible.
