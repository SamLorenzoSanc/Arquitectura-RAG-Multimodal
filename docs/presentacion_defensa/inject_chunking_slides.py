#!/usr/bin/env python3
"""Inserta diapositivas de estrategia de chunking (con código) en la PPTX de defensa."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Presentacion_TFM_user.pptx"
OUT = ROOT / "Presentacion_TFM_PPTX.pptx"
ONEDRIVE_DIR = Path.home() / "OneDrive" / "Documentos"

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x4A, 0x4A, 0x4A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0x0B, 0x5F, 0x8A)
CODE_BG = RGBColor(0x1E, 0x1E, 0x1E)
CODE_FG = RGBColor(0xD4, 0xD4, 0xD4)
CODE_KW = RGBColor(0x56, 0x9C, 0xD6)
CODE_CMT = RGBColor(0x6A, 0x99, 0x55)
SOFT = RGBColor(0xF0, 0xF4, 0xF8)


def _fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _round(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    _fill(shape, color)
    return shape


def _textbox(slide, left, top, width, height, specs, valign=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    try:
        tf._txBody.bodyPr.set(
            "anchor",
            {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[valign],
        )
    except Exception:
        pass
    first = True
    for spec in specs:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(spec.get("space_after", 4))
        run = p.add_run()
        run.text = spec["text"]
        run.font.size = Pt(spec.get("size", 14))
        run.font.bold = spec.get("bold", False)
        run.font.color.rgb = spec.get("color", INK)
        run.font.name = spec.get("font", "Calibri")
    return box


def _code_block(slide, left, top, width, height, lines: list[tuple[str, str]]):
    _round(slide, left, top, width, height, CODE_BG)
    box = slide.shapes.add_textbox(
        left + Inches(0.18),
        top + Inches(0.12),
        width - Inches(0.3),
        height - Inches(0.2),
    )
    tf = box.text_frame
    tf.word_wrap = False
    colors = {"plain": CODE_FG, "kw": CODE_KW, "cmt": CODE_CMT, "blank": CODE_FG}
    first = True
    for kind, text in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(1)
        run = p.add_run()
        run.text = text if kind != "blank" else " "
        run.font.name = "Consolas"
        run.font.size = Pt(11)
        run.font.bold = kind == "kw"
        run.font.color.rgb = colors.get(kind, CODE_FG)
    return box


def _move_slide(prs: Presentation, old_index: int, new_index: int) -> None:
    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
    slides = list(sld_id_lst)
    el = slides[old_index]
    sld_id_lst.remove(el)
    sld_id_lst.insert(new_index, el)


def _has_chunking(prs: Presentation) -> bool:
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_text_frame and "Estrategia de chunking" in sh.text_frame.text:
                return True
    return False


def add_chunking_slides(prs: Presentation, insert_after: int = 8) -> None:
    blank = prs.slide_layouts[4]

    # ── Slide A: estrategia ─────────────────────────────────────
    s = prs.slides.add_slide(blank)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.85))
    _fill(bar, ACCENT)
    _textbox(
        s,
        Inches(0.45),
        Inches(0.2),
        Inches(12),
        Inches(0.5),
        [{"text": "Estrategia de chunking (ingesta)", "size": 26, "bold": True, "color": WHITE}],
    )

    cards = [
        ("Ventana", "1.400 caracteres", "RAG_CHUNK_SIZE"),
        ("Solape", "120 caracteres", "RAG_CHUNK_OVERLAP"),
        ("Cortes suaves", "parrafo → linea → palabra", "evita partir frases"),
    ]
    for i, (title, value, note) in enumerate(cards):
        x = Inches(0.4 + i * 4.2)
        _round(s, x, Inches(1.15), Inches(4.0), Inches(1.55), SOFT)
        _textbox(
            s,
            x + Inches(0.2),
            Inches(1.3),
            Inches(3.6),
            Inches(0.35),
            [{"text": title, "size": 13, "bold": True, "color": ACCENT}],
        )
        _textbox(
            s,
            x + Inches(0.2),
            Inches(1.65),
            Inches(3.6),
            Inches(0.45),
            [{"text": value, "size": 20, "bold": True, "color": INK}],
        )
        _textbox(
            s,
            x + Inches(0.2),
            Inches(2.2),
            Inches(3.6),
            Inches(0.35),
            [{"text": note, "size": 12, "color": MUTED}],
        )

    _round(s, Inches(0.4), Inches(2.95), Inches(6.1), Inches(3.7), SOFT)
    _textbox(
        s,
        Inches(0.6),
        Inches(3.15),
        Inches(5.7),
        Inches(0.4),
        [{"text": "Por que esta estrategia", "size": 16, "bold": True, "color": ACCENT}],
    )
    bullets = [
        "Fragmentos grandes: requisitos, plazos y cifras juntos.",
        "Solape 120: continuidad entre ventanas (menos corte).",
        "Prioridad de corte: parrafo → linea → espacio (>=40%).",
        "Cada chunk guarda headline + summary + content.",
        "El embedding usa el cuerpo (content); headline cita.",
        "Archivo: gateway/services/embedding_reindex.py",
    ]
    y = 3.6
    for b in bullets:
        _textbox(
            s,
            Inches(0.65),
            Inches(y),
            Inches(5.6),
            Inches(0.45),
            [{"text": f"•  {b}", "size": 12, "color": INK}],
        )
        y += 0.45

    _round(s, Inches(6.75), Inches(2.95), Inches(6.1), Inches(3.7), CODE_BG)
    _textbox(
        s,
        Inches(6.95),
        Inches(3.15),
        Inches(5.7),
        Inches(0.35),
        [{"text": "Ventanas con solape (esquema)", "size": 14, "bold": True, "color": WHITE}],
    )
    _code_block(
        s,
        Inches(6.95),
        Inches(3.55),
        Inches(5.7),
        Inches(2.9),
        [
            ("cmt", "# Documento largo -> ventanas solapadas"),
            ("blank", ""),
            ("plain", "|--------- chunk 0 (1400) ---------|"),
            ("plain", "              |-- overlap 120 --|"),
            ("plain", "              |--------- chunk 1 ----|"),
            ("blank", ""),
            ("cmt", "# Si hay \\n\\n cerca del final,"),
            ("cmt", "# se corta ahi (no a mitad de frase)."),
            ("blank", ""),
            ("kw", "start = max(end - overlap, start + 1)"),
        ],
    )
    _textbox(
        s,
        Inches(0.4),
        Inches(6.85),
        Inches(3),
        Inches(0.3),
        [{"text": "BUSINESS & TECH", "size": 10, "color": MUTED}],
    )

    # ── Slide B: código ─────────────────────────────────────────
    s2 = prs.slides.add_slide(blank)
    bar2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.85))
    _fill(bar2, ACCENT)
    _textbox(
        s2,
        Inches(0.45),
        Inches(0.2),
        Inches(12),
        Inches(0.5),
        [
            {
                "text": "Código real: split_into_chunks + persistencia",
                "size": 24,
                "bold": True,
                "color": WHITE,
            }
        ],
    )
    _textbox(
        s2,
        Inches(0.45),
        Inches(0.95),
        Inches(12),
        Inches(0.3),
        [
            {
                "text": "gateway/services/embedding_reindex.py  ·  corrida oficial: 1400 / 120",
                "size": 12,
                "color": MUTED,
            }
        ],
    )

    code_lines = [
        ("cmt", "# gateway/services/embedding_reindex.py"),
        ("plain", 'CHUNK_SIZE    = int(os.getenv("RAG_CHUNK_SIZE", "1400"))'),
        ("plain", 'CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))'),
        ("blank", ""),
        ("kw", "def split_into_chunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):"),
        ("plain", '    cleaned = re.sub(r"\\r\\n", "\\n", text or "").strip()'),
        ("plain", "    parts, start = [], 0"),
        ("kw", "    while start < len(cleaned):"),
        ("plain", "        end = min(len(cleaned), start + size)"),
        ("kw", "        if end < len(cleaned):  # corte suave"),
        ("plain", '            cut = cleaned[start:end].rfind("\\n\\n")'),
        ("kw", "            if cut < size * 0.4:"),
        ("plain", '                cut = cleaned[start:end].rfind("\\n")'),
        ("kw", "            if cut < size * 0.4:"),
        ("plain", '                cut = cleaned[start:end].rfind(" ")'),
        ("kw", "            if cut >= size * 0.4:"),
        ("plain", "                end = start + cut"),
        ("plain", "        parts.append(cleaned[start:end].strip())"),
        ("plain", "        start = max(end - overlap, start + 1)"),
        ("kw", "    return parts"),
    ]
    _code_block(s2, Inches(0.35), Inches(1.35), Inches(8.0), Inches(5.2), code_lines)

    _round(s2, Inches(8.55), Inches(1.35), Inches(4.4), Inches(5.2), SOFT)
    _textbox(
        s2,
        Inches(8.75),
        Inches(1.55),
        Inches(4.0),
        Inches(0.4),
        [{"text": "Persistencia del fragmento", "size": 14, "bold": True, "color": ACCENT}],
    )
    persist_lines = [
        ("cmt", "# Tras split_into_chunks(body)"),
        ("blank", ""),
        ("plain", "Chunk("),
        ("plain", "  position=position,"),
        ("plain", "  headline=line[:200],"),
        ("plain", "  summary=part[:280],"),
        ("plain", "  content=part,"),
        ("plain", ")"),
        ("blank", ""),
        ("cmt", "# Vector = cuerpo del chunk"),
        ("plain", "embedding_payload()"),
        ("plain", "  -> content (preferido)"),
        ("blank", ""),
        ("cmt", "# Anti-ruido"),
        ("plain", "is_readable_text("),
        ("plain", "  part, min_chars=24)"),
    ]
    _code_block(s2, Inches(8.75), Inches(2.05), Inches(4.0), Inches(3.5), persist_lines)
    _textbox(
        s2,
        Inches(8.75),
        Inches(5.7),
        Inches(4.0),
        Inches(0.7),
        [
            {
                "text": "Mensaje: no es un splitter genérico; prioriza límites semánticos y deja el fragmento auditable (headline/summary/content).",
                "size": 11,
                "color": INK,
            }
        ],
    )
    _textbox(
        s2,
        Inches(0.4),
        Inches(6.85),
        Inches(3),
        Inches(0.3),
        [{"text": "BUSINESS & TECH", "size": 10, "color": MUTED}],
    )

    # Colocar justo después de Técnicas de AI (slide 8)
    n = len(prs.slides)
    _move_slide(prs, n - 2, insert_after)
    _move_slide(prs, len(prs.slides) - 1, insert_after + 1)


def _sync_onedrive(path: Path) -> None:
    if not ONEDRIVE_DIR.exists():
        print("OneDrive/Documentos no encontrado; omito sync.")
        return
    dest = ONEDRIVE_DIR / "Presentacion_TFM_PPTX_chunking.pptx"
    try:
        shutil.copy2(path, dest)
        print(f"Copiado a: {dest}")
    except OSError as exc:
        print(f"No se pudo copiar a OneDrive ({exc}). Abre: {path}")


def main() -> int:
    if not SRC.exists():
        print(f"No existe {SRC}", file=sys.stderr)
        return 1
    prs = Presentation(str(SRC))
    if _has_chunking(prs):
        print("Ya existen diapositivas de chunking; regenero OUT desde SRC+inyeccion.")
        # regenerar desde copia limpia si el usuario vuelve a copiar el original
    else:
        add_chunking_slides(prs, insert_after=8)
        prs.save(str(OUT))
        print(f"Guardado: {OUT} ({len(prs.slides)} slides)")
        shutil.copy2(OUT, SRC)
        _sync_onedrive(OUT)
        return 0

    # Si ya tenia chunking en SRC (re-ejecucion), solo sincronizar OUT
    if not OUT.exists():
        prs.save(str(OUT))
    _sync_onedrive(OUT if OUT.exists() else SRC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
