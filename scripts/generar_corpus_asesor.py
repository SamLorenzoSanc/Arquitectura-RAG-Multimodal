"""Genera el corpus de asesoría agraria canaria a partir del vademécum MAPA.

Escribe knowledge-base/asesor-canarias/ (textos de marco) y
knowledge-base/asesor-canarias/cultivos/ (dossiers con productos agrupados por plaga).
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_PATH = REPO / "knowledge-base" / "Vademecum" / "vademecum_canarias.csv"
OUT = REPO / "knowledge-base" / "asesor-canarias"
CULTIVOS_DIR = OUT / "cultivos"
MAPA = "https://servicio.mapa.gob.es/regfiweb/"

# (slug, título, tokens que identifican el cultivo MAPA)
CULTIVOS = (
    ("platanera", "Platanera (plátano IGP)", ("platanera", "platano", "platanos", "banana")),
    ("papa", "Papa / patata", ("patata", "patatas", "papa")),
    ("tomate", "Tomate", ("tomate", "tomates")),
    ("vid", "Vid (uva de mesa y vinificación)", ("vid", "vina")),
    ("aguacate", "Aguacate", ("aguacate", "aguacates")),
    ("papaya", "Papaya", ("papaya", "papayas")),
    ("mango", "Mango", ("mango", "mangos")),
    ("citricos", "Cítricos", ("citric", "naranj", "limonero", "limones", "mandarin", "pomelo", "toronja")),
    ("olivo", "Olivo", ("olivo",)),
    ("pimiento", "Pimiento", ("pimiento", "pimientos")),
    ("berenjena", "Berenjena", ("berenjena", "berenjenas")),
    ("batata", "Batata / boniato", ("batata", "boniato")),
    ("cebolla", "Cebolla y ajo", ("cebolla", "ajo", "ajete")),
    ("lechuga", "Lechuga", ("lechuga",)),
    ("forrajes", "Cultivos forrajeros", ("forraj", "alfalfa")),
)


def _fold(text: str) -> str:
    nfd = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in nfd if not unicodedata.combining(ch)).casefold()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _fold(text)))


def _match(cultivo: str, needles: tuple[str, ...]) -> bool:
    tokens = _tokens(cultivo)
    blob = _fold(cultivo)
    for needle in needles:
        if needle in {"ajo"}:
            if needle in tokens and "ajete" not in tokens:
                return True
            continue
        if needle == "papa":
            if "papa" in tokens and "papaya" not in blob:
                return True
            continue
        if any(token == needle or token.startswith(needle) for token in tokens):
            return True
        if len(needle) >= 5 and needle in blob:
            return True
    return False


def _leer_csv() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"No está {CSV_PATH}. Ejecuta antes: python scripts/descargar_vademecum_mapa.py"
        )
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _dosis(row: dict[str, str]) -> str:
    low = (row.get("dosis_min") or "").strip()
    high = (row.get("dosis_max") or "").strip()
    unit = (row.get("unidad_dosis") or "").strip()
    if low and high and low != high:
        return f"{low}–{high} {unit}".strip()
    return f"{low or high} {unit}".strip()


def _dossier(nombre: str, slug: str, rows: list[dict[str, str]], marco: str) -> str:
    vigentes = [r for r in rows if (r.get("estado") or "").lower() == "vigente"]
    base = vigentes or rows
    by_pest: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for row in base:
        key = (
            row.get("num_registro") or "",
            row.get("agente") or "",
            _dosis(row),
        )
        if key in seen:
            continue
        seen.add(key)
        by_pest[row.get("agente") or "Sin agente"].append(row)

    lines = [
        f"# Dossier de asesoría: {nombre}",
        "",
        marco.strip(),
        "",
        "## Productos autorizados (MAPA)",
        "",
        f"Fuente: Registro Oficial de Productos Fitosanitarios. Consulta vigente: {MAPA}",
        "Antes de aplicar, confirma número de registro, cultivo, plaga, dosis y plazo de seguridad en la ficha oficial. En Canarias rige además la Orden de 12 de marzo de 1987 (territorio asimilado a país tercero).",
        "",
        f"Usos vigentes agrupados en este dossier: {len(base)}.",
        "",
    ]
    for pest in sorted(by_pest, key=lambda item: item.casefold()):
        lines.append(f"### {pest}")
        lines.append("")
        for row in sorted(by_pest[pest], key=lambda item: item.get("nombre") or ""):
            caldo = (row.get("volumen_caldo") or "").replace("\r", " ").replace("\n", " ").strip()
            lines.append(
                f"- **{row.get('nombre')}** (n.º {row.get('num_registro')}): "
                f"{row.get('formulado')}. "
                f"Dosis {_dosis(row)}. "
                f"Plazo de seguridad: {row.get('plazo_seguridad') or 'no indicado'}."
                + (f" Caldo: {caldo}." if caldo else "")
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


MARCOS = {
    "platanera": """
## Qué necesita el agricultor
El plátano IGP es el cultivo de referencia de Canarias (Medida II del POSEI). El asesor debe cubrir: ayudas por producción, GIP (trips, cochinilla, mosca blanca, nematodos), mal de Panamá (raza subtropical 4 presente; raza tropical 4 de cuarentena), riego y taponamiento de goteros, viento/deshoje, y cadena de frío.

## Ayuda POSEI
Medida II. Ayuda a los productores de plátanos IGP. Convocatoria anual (OPP). Texto consolidado del programa: Consejería de Agricultura. Decreto 69/2025 (cantidades de referencia).

## Problemas de campo más frecuentes
- Trips, cochinilla algodonosa, mosca blanca y ácaros.
- Nematodos y mal de Panamá (Fusarium oxysporum f. sp. cubense, raza subtropical 4).
- Clorosis (N, K, Mg, Fe), salinidad y estrés hídrico.
- Daño por viento alisio, deshoje y deshijado.
- Goteros taponados y filtros sucios.

## Qué no improvisar
No recomiendes materias activas que no figuren en la ficha MAPA para platanera. Las autorizaciones excepcionales caducan; verifica en regfiweb.
""",
    "papa": """
## Qué necesita el agricultor
Papa de mesa y de semilla (medianías y costa). POSEI Acción I.4 (superficie y comercialización). Vigilancia de Epitrix, Candidatus Liberibacter solanacearum (zebra chip) y calidad de semilla.

## Ayuda POSEI
Acción I.4. Subacción I.4.1 ayuda por superficie. Subacción I.4.2 ayuda a la comercialización.

## Problemas de campo más frecuentes
- Mildiu, polilla, pulgón y pulguillas (Epitrix).
- Semilla no certificada y podredumbres de tubérculo.
- Riego irregular y suelo con salinidad.
""",
    "tomate": """
## Qué necesita el agricultor
Tomate de invierno tradicional canario. POSEI Acción I.5 (hectárea y reconversión). Tuta, mosca blanca, oídio y virus; invernadero y calendario de recolección para mercado.

## Ayuda POSEI
Acción I.5. Subacción I.5.1 ayuda por hectárea. Subacción I.5.2 ayuda a la reconversión.
""",
    "vid": """
## Qué necesita el agricultor
Viña DOP canaria. POSEI I.3 (mantenimiento por hectárea), I.6 (transformación y embotellado) e I.7 (comercialización exterior). Filoxera: planes de contingencia, movimiento de uva y bioseguridad en vendimia.

## Ayuda POSEI
Acción I.3 mantenimiento de vides DOP. Acciones I.6 e I.7 para vino.

## Alerta sanitaria
Filoxera (Daktulosphaira vitifoliae). Consultar visor y órdenes vigentes de Sanidad Vegetal de Canarias antes de mover material vegetal o uva.
""",
    "aguacate": """
## Qué necesita el agricultor
Aguacate de medianías y costa. Comercialización en Acción I.1 (frutas). Riego, salinidad, Phytophthora, trips y viento. No hay medida POSEI específica como el plátano: entra en frutas recolectadas en Canarias.
""",
    "papaya": """
## Qué necesita el agricultor
Papaya bajo invernadero o abrigo. Acción I.1 (frutas). Ácaros, mosca blanca, virus y manejo de riego/CE. Confirmar productos MAPA: el cultivo tiene menos fichas que tomate o platanera.
""",
    "mango": """
## Qué necesita el agricultor
Mango (sur de islas). Acción I.1. Mosca de la fruta, antracnosis, riego deficitario y cosecha. GIP MAPA de mango.
""",
    "citricos": """
## Qué necesita el agricultor
Naranjo, limonero, mandarino y pomelo. Vigilancia de Trioza erytreae (ya en Canarias) y prevención de Huanglongbing (Liberibacter), ausente en Europa. No mover material sin pasaporte / inspección.
""",
    "olivo": """
## Qué necesita el agricultor
Olivo (Acción I.8.2 POSEI, ayuda por superficie). Repilo, mosca del olivo y sequía. GIP olivar MAPA.
""",
    "pimiento": """
## Qué necesita el agricultor
Pimiento de invernadero. Mosca blanca, trips, oídio y virus. GIP y registro MAPA; residuos y plazo de seguridad críticos para comercialización.
""",
    "berenjena": """
## Qué necesita el agricultor
Berenjena, a menudo en rotación de invernadero. Araña roja, trips y mosca blanca.
""",
    "batata": """
## Qué necesita el agricultor
Batata / boniato. POSEI I.1 (raíces y tubérculos) y mejoras 2026 de cuantías. Gorgojo (Cylas) y conservado postcosecha.
""",
    "cebolla": """
## Qué necesita el agricultor
Cebolla y ajo. Mildiu, trips y conservación. Acción I.1 hortalizas.
""",
    "lechuga": """
## Qué necesita el agricultor
Lechuga y similares de invierno. Mildiu, pulgón y autorizaciones excepcionales puntuales (p. ej. sulfoxaflor en apio/similares: comprobar vigencia).
""",
    "forrajes": """
## Qué necesita el agricultor
Forrajes para ganadería local. POSEI Acción III.12. No confundir con ayudas al plátano o a la papa.
""",
}


def main() -> None:
    CULTIVOS_DIR.mkdir(parents=True, exist_ok=True)
    rows = _leer_csv()
    index_lines = [
        "# Corpus de asesoría agraria canaria (AgroPS)",
        "",
        "Este corpus está pensado para que el asistente actúe como **asesor de campo**: ayudas POSEI, sanidad vegetal, GIP y productos MAPA. No sustituye al técnico de la OPP ni a Sanidad Vegetal.",
        "",
        "## Cómo usarlo",
        "Sube a Documentos, en un proyecto «Asesor Canarias», primero los capítulos 01–13 y después los dossiers de `cultivos/`. Reprocesa OCR solo si algún PDF oficial sale ilegible.",
        "",
        "## Capítulos de marco",
    ]
    for path in sorted((OUT).glob("*.md")):
        if path.name.startswith("00_") or path.name.lower() == "readme.md":
            continue
        first = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        index_lines.append(f"- `{path.name}` — {first}")

    index_lines.extend(["", "## Dossiers de cultivo", ""])
    for slug, titulo, needles in CULTIVOS:
        matched = [row for row in rows if _match(row.get("cultivo") or "", needles)]
        if slug == "papa":
            matched = [
                row
                for row in matched
                if "papaya" not in _fold(row.get("cultivo") or "")
            ]
        if slug == "citricos":
            matched = [
                row
                for row in matched
                if "hierba" not in _fold(row.get("cultivo") or "")
            ]
        text = _dossier(titulo, slug, matched, MARCOS[slug])
        dest = CULTIVOS_DIR / f"{slug}.md"
        dest.write_text(text, encoding="utf-8")
        n_prod = len({row.get("num_registro") for row in matched})
        index_lines.append(
            f"- `cultivos/{slug}.md` — {titulo} ({n_prod} productos MAPA, {len(matched)} usos)"
        )
        print(f"{slug}: {len(matched)} usos, {n_prod} productos")

    (OUT / "00_indice.md").write_text("\n".join(index_lines).strip() + "\n", encoding="utf-8")
    print(f"Corpus en {OUT}")


if __name__ == "__main__":
    main()
