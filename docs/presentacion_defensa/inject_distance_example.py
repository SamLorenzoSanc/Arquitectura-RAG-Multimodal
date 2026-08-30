#!/usr/bin/env python3
"""Inserta una diapositiva: embeddings + ejemplo L2 / L1 / coseno A(1,2) B(4,6)."""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / "Defensa_TFM_AgroPS_15min_knn.pptx",
    ROOT / "Defensa_TFM_AgroPS_15min.pptx",
]
OUT_FALLBACK = ROOT / "Defensa_TFM_AgroPS_15min_distancias.pptx"
FIG = ROOT / "ejemplo-distancias-ab.png"

BG = RGBColor(0xF7, 0xF5, 0xF0)
INK = RGBColor(0x1A, 0x2E, 0x1A)
MUTED = RGBColor(0x4A, 0x5C, 0x4A)
ACCENT = RGBColor(0x2F, 0x6B, 0x3A)
ACCENT2 = RGBColor(0xC4, 0x7A, 0x2A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xE8, 0xEF, 0xE6)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARKER = "Embeddings = puntos. Ejemplo A(1,2) y B(4,6)"


def _fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _rect(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    _fill(shape, color)
    return shape


def _round(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    _fill(shape, color)
    return shape


def _set_run(run, text, size=18, bold=False, color=INK, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


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
        p.space_after = Pt(spec.get("space_after", 3))
        run = p.add_run()
        _set_run(
            run,
            spec["text"],
            size=spec.get("size", 14),
            bold=spec.get("bold", False),
            color=spec.get("color", INK),
            font=spec.get("font", "Calibri"),
        )
    return box


def _badge(slide, left, top, width, height, text, bg=ACCENT, fg=WHITE, size=11):
    shape = _round(slide, left, top, width, height, bg)
    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    _set_run(run, text, size=size, bold=True, color=fg)
    try:
        tf._txBody.bodyPr.set("anchor", "ctr")
    except Exception:
        pass
    return shape


def _move_slide(prs: Presentation, old_index: int, new_index: int) -> None:
    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
    slides = list(sld_id_lst)
    el = slides[old_index]
    sld_id_lst.remove(el)
    sld_id_lst.insert(new_index, el)


def _has_marker(prs: Presentation) -> bool:
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_text_frame and MARKER in sh.text_frame.text:
                return True
    return False


def _find_insert_at(prs: Presentation) -> int:
    for i, slide in enumerate(prs.slides):
        for sh in slide.shapes:
            if sh.has_text_frame and "Métrica de búsqueda: distancia coseno" in sh.text_frame.text:
                return i + 1
    for i, slide in enumerate(prs.slides):
        for sh in slide.shapes:
            if sh.has_text_frame and "Técnicas de IA aplicadas" in sh.text_frame.text:
                return i + 1
    return min(8, len(prs.slides))


def add_distance_example_slide(prs: Presentation, insert_at: int) -> None:
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
    s = prs.slides.add_slide(blank)
    _rect(s, 0, 0, SLIDE_W, SLIDE_H, BG)
    _rect(s, 0, 0, SLIDE_W, Inches(0.08), ACCENT)

    _textbox(
        s,
        Inches(0.4),
        Inches(0.18),
        Inches(12.5),
        Inches(0.42),
        [{"text": MARKER, "size": 22, "bold": True, "color": INK}],
    )
    _textbox(
        s,
        Inches(0.4),
        Inches(0.58),
        Inches(12.5),
        Inches(0.32),
        [
            {
                "text": "A = embedding de la pregunta · B = embedding de un chunk. En AgroPS hay 768 dimensiones; en 2D se ve la misma geometría.",
                "size": 13,
                "color": MUTED,
            }
        ],
    )

    _round(s, Inches(0.35), Inches(1.0), Inches(5.05), Inches(5.85), CARD)
    if FIG.exists():
        s.shapes.add_picture(str(FIG), Inches(0.5), Inches(1.15), width=Inches(4.75))
    else:
        _textbox(
            s,
            Inches(0.55),
            Inches(3.4),
            Inches(4.6),
            Inches(0.8),
            [{"text": "Falta ejemplo-distancias-ab.png", "size": 14, "color": MUTED}],
        )

    cards = [
        (
            "Euclidiana (L2)",
            "5",
            "√((4−1)² + (6−2)²) = √(9+16) = 5",
            "Línea recta (Pitágoras). En el lab, no en el chat.",
            ACCENT2,
            False,
        ),
        (
            "Manhattan (L1)",
            "7",
            "|4−1| + |6−2| = 3+4 = 7",
            "Camino en cuadrícula. Tampoco usa HNSW.",
            MUTED,
            False,
        ),
        (
            "Coseno  ← producción",
            "0,0076",
            "1 − 16 / √260 ≈ 1 − 0,9924 = 0,0076",
            "Ángulo, no magnitud. Casi 0 = muy similares.",
            ACCENT,
            True,
        ),
    ]
    for i, (title, value, formula, note, color, highlight) in enumerate(cards):
        y = Inches(1.0 + i * 1.55)
        _round(s, Inches(5.55), y, Inches(7.4), Inches(1.45), SOFT if highlight else CARD)
        _rect(s, Inches(5.55), y, Inches(0.12), Inches(1.45), color)
        _badge(s, Inches(5.85), y + Inches(0.12), Inches(3.55), Inches(0.32), title, color)
        _textbox(
            s,
            Inches(9.55),
            y + Inches(0.08),
            Inches(3.15),
            Inches(0.4),
            [{"text": value, "size": 22, "bold": True, "color": color, "align": PP_ALIGN.RIGHT}],
        )
        _textbox(
            s,
            Inches(5.85),
            y + Inches(0.5),
            Inches(6.85),
            Inches(0.38),
            [{"text": formula, "size": 13, "bold": True, "color": INK}],
        )
        _textbox(
            s,
            Inches(5.85),
            y + Inches(0.9),
            Inches(6.85),
            Inches(0.4),
            [{"text": note, "size": 12, "color": MUTED}],
        )

    _round(s, Inches(5.55), Inches(5.7), Inches(7.4), Inches(1.15), SOFT)
    _textbox(
        s,
        Inches(5.75),
        Inches(5.85),
        Inches(7.05),
        Inches(0.9),
        [
            {
                "text": "k-NN ordena todos los B por d(A,B) y se queda con k=10 más cercanos. Coseno ≈ 0 ⇒ mismo ángulo semántico. L2=5 y L1=7 miden «cuánto se recorre»; en texto importa la orientación, por eso AgroPS usa coseno + HNSW.",
                "size": 13,
                "bold": True,
                "color": INK,
            }
        ],
    )

    _textbox(
        s,
        Inches(0.4),
        Inches(7.05),
        Inches(10),
        Inches(0.3),
        [{"text": "AgroPS · Defensa TFM · ejemplo distancias", "size": 10, "color": MUTED}],
    )

    n = len(prs.slides)
    _move_slide(prs, n - 1, insert_at)


def _open_source() -> tuple[Path, Presentation]:
    for path in CANDIDATES:
        if path.exists():
            return path, Presentation(str(path))
    raise FileNotFoundError("No hay PPTX de defensa en presentacion_defensa/")


def _save(prs: Presentation, src: Path) -> Path:
    try:
        prs.save(str(src))
        return src
    except OSError as exc:
        prs.save(str(OUT_FALLBACK))
        print(f"Archivo bloqueado ({exc}). Guardado en: {OUT_FALLBACK}")
        return OUT_FALLBACK


def main() -> int:
    src, prs = _open_source()
    if _has_marker(prs):
        print(f"La diapositiva ya está en {src.name}. No duplico.")
        return 0
    insert_at = _find_insert_at(prs)
    add_distance_example_slide(prs, insert_at)
    out = _save(prs, src)
    print(f"Guardado: {out} ({len(prs.slides)} diapositivas). Insertada en posición {insert_at + 1}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
