"""Parsers puros para datasets abiertos de Canarias (SAT e ISTAC)."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Iterable, Optional


SAT_FIELDS = (
    "denominacion",
    "nif",
    "objeto_social_principal_id",
    "objeto_social_principal_nombre",
    "ambito_id",
    "ambito_nombre",
    "clase_responsabilidad",
    "duracion",
    "numero_socios",
    "situacion",
    "direccion",
    "direccion_codigo_postal",
    "direccion_municipio_id",
    "direccion_municipio_nombre",
    "direccion_provincia_id",
    "direccion_provincia_nombre",
)

_UNKNOWN_NIF = "_U"
_NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_socios(value: Any) -> Optional[int]:
    text = _clean(value)
    if text is None or not text.isdigit():
        return None
    return int(text)


def normalize_sat_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Normaliza una fila SAT. Descarta filas sin denominación o con NIF desconocido vacío."""
    denominacion = _clean(row.get("denominacion"))
    nif = _clean(row.get("nif"))
    if not denominacion:
        return None
    if nif == _UNKNOWN_NIF:
        nif = None
    return {
        "denominacion": denominacion,
        "nif": nif,
        "objeto_social_principal_id": _clean(row.get("objeto_social_principal_id")),
        "objeto_social_principal_nombre": _clean(
            row.get("objeto_social_principal_nombre")
        ),
        "ambito_id": _clean(row.get("ambito_id")),
        "ambito_nombre": _clean(row.get("ambito_nombre")),
        "clase_responsabilidad": _clean(row.get("clase_responsabilidad")),
        "duracion": _clean(row.get("duracion")),
        "numero_socios": _parse_socios(row.get("numero_socios")),
        "situacion": _clean(row.get("situacion")),
        "direccion": _clean(row.get("direccion")),
        "direccion_codigo_postal": _clean(row.get("direccion_codigo_postal")),
        "direccion_municipio_id": _clean(row.get("direccion_municipio_id")),
        "direccion_municipio_nombre": _clean(row.get("direccion_municipio_nombre")),
        "direccion_provincia_id": _clean(row.get("direccion_provincia_id")),
        "direccion_provincia_nombre": _clean(row.get("direccion_provincia_nombre")),
    }


def parse_sat_csv(path: str | Path) -> list[dict[str, Any]]:
    """Lee el registro SAT Canarias y devuelve filas normalizadas."""
    file_path = Path(path)
    rows: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            normalized = normalize_sat_row(raw or {})
            if normalized is not None:
                rows.append(normalized)
    return rows


def filter_sat_rows(
    rows: Iterable[dict[str, Any]],
    *,
    municipio: Optional[str] = None,
    situacion: Optional[str] = None,
    cnae_contains: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Filtra SATs por municipio, situación o texto de CNAE."""
    municipio_norm = (municipio or "").strip().lower()
    situacion_norm = (situacion or "").strip().lower()
    cnae_norm = (cnae_contains or "").strip().lower()

    result: list[dict[str, Any]] = []
    for row in rows:
        if municipio_norm and municipio_norm not in (
            (row.get("direccion_municipio_nombre") or "").lower()
        ):
            continue
        if situacion_norm and situacion_norm != (row.get("situacion") or "").lower():
            continue
        if cnae_norm and cnae_norm not in (
            (row.get("objeto_social_principal_nombre") or "").lower()
        ):
            continue
        result.append(row)
    return result


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(",", ".")
    if not text or not _NUMBER_RE.match(text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def series_id_from_filename(filename: str) -> str:
    """Deriva un id estable a partir del nombre de fichero ISTAC."""
    stem = Path(filename).stem
    stem = re.sub(r"~latest-selection$", "", stem)
    stem = re.sub(r"-1_1-selection$", "", stem)
    stem = re.sub(r"-selection$", "", stem)
    return stem.rstrip("-_")


def parse_istac_sheet_rows(
    rows: list[list[Any]],
    *,
    series_id: str,
    source_file: str,
) -> dict[str, Any]:
    """
    Extrae metadatos y observaciones numéricas de una hoja ISTAC ya materializada.

    La estructura típica tiene título en la primera fila, fecha de actualización
    y una matriz con etiquetas de fila/columna.
    """
    title = None
    updated_at = None
    for row in rows[:12]:
        cells = [_clean(c) for c in row]
        non_empty = [c for c in cells if c]
        if title is None and non_empty:
            title = non_empty[0]
        for idx, cell in enumerate(cells):
            if cell and "ltima actualizaci" in cell.lower().replace("ú", "u"):
                if idx + 1 < len(cells) and cells[idx + 1]:
                    updated_at = cells[idx + 1]
                break

    observations: list[dict[str, Any]] = []
    header_row_idx = None
    for idx, row in enumerate(rows):
        # Cabecera candidata: contiene varios periodos/años o indicadores.
        labels = [_clean(c) for c in row[1:]]
        useful = [c for c in labels if c and not c.lower().startswith("unidad")]
        if len(useful) >= 2:
            header_row_idx = idx
            break

    if header_row_idx is None:
        return {
            "series_id": series_id,
            "title": title or series_id,
            "updated_at": updated_at,
            "source_file": source_file,
            "observations": [],
        }

    headers = [_clean(c) for c in rows[header_row_idx]]
    for row in rows[header_row_idx + 1 :]:
        if not row:
            continue
        row_label = _clean(row[0]) if len(row) else None
        # Algunas tablas ISTAC empiezan la etiqueta en columna 1/2.
        if row_label is None:
            for cell in row[:3]:
                row_label = _clean(cell)
                if row_label:
                    break
        if not row_label:
            continue
        for col_idx, cell in enumerate(row):
            if col_idx == 0:
                continue
            value = _to_float(cell)
            if value is None:
                continue
            col_label = headers[col_idx] if col_idx < len(headers) else None
            observations.append(
                {
                    "row_label": row_label,
                    "column_label": col_label,
                    "value": value,
                    "unit": None,
                }
            )

    return {
        "series_id": series_id,
        "title": title or series_id,
        "updated_at": updated_at,
        "source_file": source_file,
        "observations": observations,
    }


def parse_istac_xlsx(path: str | Path) -> dict[str, Any]:
    """Lee un XLSX ISTAC con openpyxl y extrae observaciones."""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependencia de runtime
        raise RuntimeError("openpyxl es necesario para importar ISTAC") from exc

    file_path = Path(path)
    workbook = load_workbook(file_path, read_only=True, data_only=True)
    try:
        sheet = workbook[workbook.sheetnames[0]]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()

    return parse_istac_sheet_rows(
        rows,
        series_id=series_id_from_filename(file_path.name),
        source_file=file_path.name,
    )
