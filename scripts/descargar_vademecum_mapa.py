"""Descarga el JSON oficial del Registro de Productos Fitosanitarios (MAPA).

Equivale al botón «Listado completo de Productos Autorizados para el
Cuaderno de Explotaciones Agrarias» en
https://servicio.mapa.gob.es/regfiweb/Resumenes/Index

No scrapea Portal Tecnoagrícola. Actualizar los viernes (el MAPA refresca
el registro a las 14:00).
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXPORT_URL = (
    "https://servicio.mapa.gob.es/regfiweb/"
    "Exportaciones/ExportJsonProductosAutorizados"
)
FUENTE = "https://servicio.mapa.gob.es/regfiweb/"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "knowledge-base" / "Vademecum"

CANARIAS_HINTS = (
    "platan",
    "banana",
    "papa",
    "patata",
    "tomate",
    "vid",
    "vina",
    "uva",
    "aguacat",
    "papaya",
    "mango",
    "olivo",
    "aloe",
    "citric",
    "naranj",
    "limon",
    "mandarin",
    "pomelo",
    "chirimoy",
    "pimiento",
    "berenjena",
    "calabacin",
    "lechuga",
    "cebolla",
    "ajo",
    "forraj",
    "alfalfa",
    "fresa",
    "pepino",
    "melon",
    "sandia",
    "batata",
    "boniato",
    "cochinilla",
)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _es_cultivo_canario(cultivo: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", _fold(cultivo))
    for hint in CANARIAS_HINTS:
        if len(hint) <= 4:
            if hint in tokens:
                return True
        elif any(token.startswith(hint) or hint in token for token in tokens):
            return True
    return False


def _slug(text: str) -> str:
    folded = _fold(text)
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return (slug or "sin-cultivo")[:80]


def descargar_catalogo() -> dict:
    body = urllib.parse.urlencode(
        {"tipoExportacion": "ProductosAutorizados", "dataDto": "{}"}
    ).encode()
    request = urllib.request.Request(
        EXPORT_URL,
        data=body,
        method="POST",
        headers={
            "User-Agent": "AgroPS-TFM/1.0 (descarga oficial MAPA CUE)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://servicio.mapa.gob.es/regfiweb/Resumenes/Index",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, str):
        payload = json.loads(payload)
    contenido = payload.get("Contenido") if isinstance(payload, dict) else payload
    catalogo = json.loads(contenido) if isinstance(contenido, str) else contenido
    if not isinstance(catalogo, dict) or "Productos" not in catalogo:
        raise RuntimeError("El MAPA no devolvió el listado de productos autorizados.")
    catalogo["_meta"] = {
        "fuente": "Registro Oficial de Productos Fitosanitarios (MAPA)",
        "url": FUENTE,
        "descargado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fecha_registro_mapa": payload.get("Fecha") if isinstance(payload, dict) else None,
        "productos": len(catalogo.get("Productos") or []),
    }
    return catalogo


def _filas(productos: list[dict], solo_canarias: bool) -> list[dict]:
    rows: list[dict] = []
    for item in productos:
        datos = item.get("DATOSPRODUCTO") or {}
        composicion = "; ".join(
            f"{parte.get('Nombre Sustancia') or ''} {parte.get('Concentracion') or ''}"
            f"{parte.get('DescripcionNota') or ''}".strip()
            for parte in item.get("COMPOSICION") or []
        )
        usos = item.get("USOS") or [{}]
        for uso in usos:
            cultivo = str(uso.get("Cultivo") or "")
            if solo_canarias and cultivo and not _es_cultivo_canario(cultivo):
                continue
            if solo_canarias and not cultivo:
                continue
            rows.append(
                {
                    "num_registro": datos.get("Num_Registro") or "",
                    "nombre": datos.get("Nombre") or "",
                    "estado": datos.get("Estado") or "",
                    "formulado": datos.get("Formulado") or "",
                    "titular": datos.get("Titular") or "",
                    "composicion": composicion,
                    "cultivo": cultivo,
                    "agente": uso.get("Agente") or "",
                    "dosis_min": uso.get("Dosis_Min") if uso else "",
                    "dosis_max": uso.get("Dosis_Max") if uso else "",
                    "unidad_dosis": uso.get("Unidad Medida dosis") or "",
                    "plazo_seguridad": uso.get("Plazo Seguridad") or "",
                    "volumen_caldo": uso.get("Volumen Caldo") or "",
                    "fecha_caducidad": datos.get("Fecha_Caducidad") or "",
                }
            )
    return rows


def _escribir_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _escribir_cultivos(out_dir: Path, rows: list[dict]) -> int:
    dest = out_dir / "cultivos"
    dest.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["cultivo"] or "Sin cultivo"].append(row)
    written = 0
    for cultivo, items in grouped.items():
        lines = [
            f"# Vademécum fitosanitario — {cultivo}",
            "",
            "Fuente: Registro Oficial de Productos Fitosanitarios (MAPA).",
            f"Consulta: {FUENTE}",
            "En Canarias, confirmar siempre la ficha vigente en regfiweb antes de aplicar.",
            "",
        ]
        for row in items:
            lines.extend(
                [
                    f"## {row['nombre']} ({row['num_registro']})",
                    f"- Estado: {row['estado']}",
                    f"- Formulado: {row['formulado']}",
                    f"- Composición: {row['composicion']}",
                    f"- Cultivo: {row['cultivo']}",
                    f"- Agente / plaga: {row['agente']}",
                    f"- Dosis: {row['dosis_min']}–{row['dosis_max']} {row['unidad_dosis']}".strip(),
                    f"- Plazo de seguridad: {row['plazo_seguridad']}",
                    f"- Volumen de caldo: {row['volumen_caldo']}",
                    f"- Caducidad registro: {row['fecha_caducidad']}",
                    "",
                ]
            )
        path = dest / f"{_slug(cultivo)}.md"
        path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        written += 1
    return written


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Descargando listado oficial MAPA…")
    catalogo = descargar_catalogo()
    productos = catalogo.get("Productos") or []
    bruto = OUT_DIR / "productos_autorizados.json"
    bruto.write_text(
        json.dumps(catalogo, ensure_ascii=False),
        encoding="utf-8",
    )
    meta = catalogo.get("_meta") or {}
    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    todos = _filas(productos, solo_canarias=False)
    canarias = _filas(productos, solo_canarias=True)
    _escribir_csv(OUT_DIR / "vademecum_usos.csv", todos)
    _escribir_csv(OUT_DIR / "vademecum_canarias.csv", canarias)
    n_md = _escribir_cultivos(OUT_DIR, canarias)
    print(
        f"Listo: {meta.get('productos')} productos, "
        f"{len(todos)} usos, {len(canarias)} usos canarios, "
        f"{n_md} fichas por cultivo en {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
