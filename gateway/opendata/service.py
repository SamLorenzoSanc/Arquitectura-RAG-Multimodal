"""Servicio de importación y consulta de datos abiertos Canarias."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from opendata.parsers import (
    filter_sat_rows,
    parse_istac_xlsx,
    parse_sat_csv,
)

DEFAULT_OPENDATA_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "opendata"
)


async def ensure_opendata_tables(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS sat_societies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                denominacion TEXT NOT NULL,
                nif VARCHAR(32),
                objeto_social_principal_id VARCHAR(32),
                objeto_social_principal_nombre TEXT,
                ambito_id VARCHAR(64),
                ambito_nombre TEXT,
                clase_responsabilidad VARCHAR(64),
                duracion VARCHAR(64),
                numero_socios INTEGER,
                situacion VARCHAR(64),
                direccion TEXT,
                direccion_codigo_postal VARCHAR(16),
                direccion_municipio_id VARCHAR(32),
                direccion_municipio_nombre TEXT,
                direccion_provincia_id VARCHAR(32),
                direccion_provincia_nombre TEXT,
                source_file TEXT,
                imported_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                UNIQUE (nif, denominacion)
            )
            """
        )
    )
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS istac_series (
                series_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                updated_at TEXT,
                source_file TEXT NOT NULL,
                imported_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS istac_observations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                series_id TEXT NOT NULL REFERENCES istac_series(series_id) ON DELETE CASCADE,
                row_label TEXT,
                column_label TEXT,
                value DOUBLE PRECISION NOT NULL,
                unit TEXT
            )
            """
        )
    )
    await db.commit()


async def import_sat_file(
    db: AsyncSession,
    path: str | Path,
    *,
    source_file: Optional[str] = None,
) -> dict[str, Any]:
    file_path = Path(path)
    rows = parse_sat_csv(file_path)
    source = source_file or file_path.name
    await ensure_opendata_tables(db)

    upsert = text(
        """
        INSERT INTO sat_societies (
            denominacion, nif, objeto_social_principal_id,
            objeto_social_principal_nombre, ambito_id, ambito_nombre,
            clase_responsabilidad, duracion, numero_socios, situacion,
            direccion, direccion_codigo_postal, direccion_municipio_id,
            direccion_municipio_nombre, direccion_provincia_id,
            direccion_provincia_nombre, source_file
        ) VALUES (
            :denominacion, :nif, :objeto_social_principal_id,
            :objeto_social_principal_nombre, :ambito_id, :ambito_nombre,
            :clase_responsabilidad, :duracion, :numero_socios, :situacion,
            :direccion, :direccion_codigo_postal, :direccion_municipio_id,
            :direccion_municipio_nombre, :direccion_provincia_id,
            :direccion_provincia_nombre, :source_file
        )
        ON CONFLICT (nif, denominacion) DO UPDATE SET
            objeto_social_principal_id = EXCLUDED.objeto_social_principal_id,
            objeto_social_principal_nombre = EXCLUDED.objeto_social_principal_nombre,
            situacion = EXCLUDED.situacion,
            direccion = EXCLUDED.direccion,
            direccion_municipio_nombre = EXCLUDED.direccion_municipio_nombre,
            source_file = EXCLUDED.source_file,
            imported_at = NOW()
        """
    )
    for row in rows:
        await db.execute(upsert, {**row, "source_file": source})
    await db.commit()
    return {"imported": len(rows), "source_file": source}


async def import_istac_file(db: AsyncSession, path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    parsed = parse_istac_xlsx(file_path)
    await ensure_opendata_tables(db)

    await db.execute(
        text(
            """
            INSERT INTO istac_series (series_id, title, updated_at, source_file)
            VALUES (:series_id, :title, :updated_at, :source_file)
            ON CONFLICT (series_id) DO UPDATE SET
                title = EXCLUDED.title,
                updated_at = EXCLUDED.updated_at,
                source_file = EXCLUDED.source_file,
                imported_at = NOW()
            """
        ),
        {
            "series_id": parsed["series_id"],
            "title": parsed["title"],
            "updated_at": parsed["updated_at"],
            "source_file": parsed["source_file"],
        },
    )
    await db.execute(
        text("DELETE FROM istac_observations WHERE series_id = :series_id"),
        {"series_id": parsed["series_id"]},
    )
    insert_obs = text(
        """
        INSERT INTO istac_observations (series_id, row_label, column_label, value, unit)
        VALUES (:series_id, :row_label, :column_label, :value, :unit)
        """
    )
    for obs in parsed["observations"]:
        await db.execute(
            insert_obs,
            {
                "series_id": parsed["series_id"],
                "row_label": obs["row_label"],
                "column_label": obs["column_label"],
                "value": obs["value"],
                "unit": obs.get("unit"),
            },
        )
    await db.commit()
    return {
        "series_id": parsed["series_id"],
        "title": parsed["title"],
        "observations": len(parsed["observations"]),
        "source_file": parsed["source_file"],
    }


async def import_opendata_directory(
    db: AsyncSession,
    directory: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(directory) if directory else DEFAULT_OPENDATA_DIR
    if not root.exists():
        raise FileNotFoundError(f"No existe el directorio de opendata: {root}")

    sat_files = sorted(root.glob("registro_sat_canarias*.csv"))
    istac_files = sorted(root.glob("dataset-ISTAC-*.xlsx"))

    sat_results = []
    for path in sat_files:
        sat_results.append(await import_sat_file(db, path))

    istac_results = []
    for path in istac_files:
        istac_results.append(await import_istac_file(db, path))

    return {
        "directory": str(root),
        "sat": sat_results,
        "istac": istac_results,
        "sat_files": len(sat_files),
        "istac_files": len(istac_files),
    }


async def list_sat_societies(
    db: AsyncSession,
    *,
    municipio: Optional[str] = None,
    situacion: Optional[str] = None,
    cnae_contains: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    await ensure_opendata_tables(db)
    result = await db.execute(text("SELECT * FROM sat_societies ORDER BY denominacion"))
    rows = [dict(r) for r in result.mappings().all()]
    filtered = filter_sat_rows(
        rows,
        municipio=municipio,
        situacion=situacion,
        cnae_contains=cnae_contains,
    )
    return filtered[: max(1, min(limit, 500))]


async def list_istac_series(db: AsyncSession) -> list[dict[str, Any]]:
    await ensure_opendata_tables(db)
    result = await db.execute(
        text(
            """
            SELECT s.series_id, s.title, s.updated_at, s.source_file, s.imported_at,
                   COUNT(o.id) AS observation_count
            FROM istac_series s
            LEFT JOIN istac_observations o ON o.series_id = s.series_id
            GROUP BY s.series_id, s.title, s.updated_at, s.source_file, s.imported_at
            ORDER BY s.title
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


async def list_istac_observations(
    db: AsyncSession,
    series_id: str,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    await ensure_opendata_tables(db)
    result = await db.execute(
        text(
            """
            SELECT row_label, column_label, value, unit
            FROM istac_observations
            WHERE series_id = :series_id
            ORDER BY row_label NULLS LAST, column_label NULLS LAST
            LIMIT :limit
            """
        ),
        {"series_id": series_id, "limit": max(1, min(limit, 2000))},
    )
    return [dict(r) for r in result.mappings().all()]
