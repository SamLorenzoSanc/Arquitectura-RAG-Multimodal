"""Genera diagrama OCR + capturas de código para defensa / memoria TFM."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT

W_DIAG, H_DIAG = 2600, 1500
NAVY = (26, 54, 93)
ACCENT = (7, 104, 169)
GREEN = (39, 103, 73)
AMBER = (180, 120, 40)
INK = (45, 55, 72)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
SOFT = (247, 250, 252)
FILL_A = (237, 242, 247)
FILL_B = (235, 248, 255)
FILL_C = (255, 250, 240)
FILL_D = (240, 253, 244)
WHITE = (255, 255, 255)

# Code capture theme (VS Code dark)
CODE_BG = (30, 30, 30)
CODE_FG = (212, 212, 212)
CODE_KW = (86, 156, 214)
CODE_STR = (206, 145, 120)
CODE_CMT = (106, 153, 85)
CODE_NUM = (181, 206, 168)
CODE_FN = (220, 220, 170)
GUTTER = (80, 80, 80)
HEADER = (45, 45, 45)


def font(size: int, bold: bool = False, mono: bool = False):
    if mono:
        candidates = [
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/cascadiamono.ttf",
            "C:/Windows/Fonts/cour.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded(draw, xy, r=18, fill=SOFT, outline=LINE, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def center_text(draw, cx, cy, text, fnt, fill=INK):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2), text, font=fnt, fill=fill)


def arrow_h(draw, x0, y, x1, color=ACCENT):
    draw.line([(x0, y), (x1 - 14, y)], fill=color, width=4)
    draw.polygon([(x1, y), (x1 - 16, y - 9), (x1 - 16, y + 9)], fill=color)


def arrow_v(draw, x, y0, y1, color=ACCENT):
    draw.line([(x, y0), (x, y1 - 14)], fill=color, width=4)
    draw.polygon([(x, y1), (x - 9, y1 - 16), (x + 9, y1 - 16)], fill=color)


def box(draw, xy, title, lines, fill, f_h, f_b):
    x0, y0, x1, y1 = xy
    rounded(draw, xy, 20, fill, LINE, 3)
    cx = (x0 + x1) // 2
    center_text(draw, cx, y0 + 34, title, f_h, NAVY)
    y = y0 + 70
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=f_b)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw / 2, y), line, font=f_b, fill=INK)
        y += 28


def compose_ocr_diagram():
    img = Image.new("RGB", (W_DIAG, H_DIAG), WHITE)
    d = ImageDraw.Draw(img)
    f_title = font(40, True)
    f_h = font(22, True)
    f_b = font(18)
    f_s = font(16)
    f_cap = font(17, True)

    d.text((50, 28), "OCR selectivo en PDF — AgroPS", font=f_title, fill=NAVY)
    d.text(
        (50, 82),
        "Motor: RapidOCR · Render: pypdfium2 · Estrategia: nativo primero, OCR solo si la página es ilegible",
        font=f_s,
        fill=GRAY,
    )

    # Patrones
    rounded(d, (50, 130, 2550, 250), 16, FILL_A, LINE, 2)
    d.text((70, 148), "Patrones de diseño aplicados", font=f_cap, fill=NAVY)
    d.text(
        (70, 185),
        "1) Hexagonal (Ports & Adapters): la extracción vive fuera del dominio RAG; el hexágono solo consume texto ya recuperable.  "
        "2) Estrategia adaptativa por página: nativo vs OCR según is_readable_text.  "
        "3) Singleton perezoso del motor RapidOCR (un engine por proceso).",
        font=f_s,
        fill=INK,
    )

    y = 290
    boxes = [
        ((50, y, 520, y + 220), "PDF bytes", ["pypdfium2", "abre documento", "página a página"], FILL_A),
        ((580, y, 1100, y + 220), "Texto nativo", ["get_text_bounded()", "rápido, sin GPU", "falla en CID/BOC"], FILL_B),
        ((1160, y, 1750, y + 220), "¿Legible?", ["latin_ratio", "junk_ratio", "¿streams PDF?"], FILL_C),
        ((1810, y, 2550, y + 220), "Si NO → OCR", ["rasteriza (scale≈2)", "RapidOCR", "une líneas txts"], FILL_D),
    ]
    for xy, title, lines, fill in boxes:
        box(d, xy, title, lines, fill, f_h, f_b)
    mid = y + 110
    arrow_h(d, 520, mid, 580)
    arrow_h(d, 1100, mid, 1160)
    arrow_h(d, 1750, mid, 1810)

    # Decision diamond area
    y2 = y + 280
    rounded(d, (50, y2, 2550, y2 + 280), 18, SOFT, LINE, 2)
    d.text((70, y2 + 20), "Decisión is_readable_text (heurística anti-basura)", font=f_cap, fill=NAVY)
    criteria = [
        ("Mínimo de caracteres", "≥ 24 (nativo) / 12 (OCR)"),
        ("Streams internos PDF", "descarta /Type /Length endobj…"),
        ("Basura Unicode", "junk_ratio < 8%"),
        ("Letras latinas + ES", "latin_ratio ≥ 28%"),
        ("Vocales", "evita cadenas sin vocales"),
        ("Resultado", "elige nativo u OCR por página"),
    ]
    x = 80
    for title, body in criteria:
        rounded(d, (x, y2 + 70, x + 380, y2 + 240), 14, WHITE, LINE, 2)
        d.text((x + 16, y2 + 90), title, font=f_h, fill=ACCENT)
        # wrap body
        d.text((x + 16, y2 + 140), body, font=f_b, fill=INK)
        x += 410

    y3 = y2 + 320
    rounded(d, (50, y3, 2550, y3 + 160), 16, FILL_D, LINE, 2)
    d.text((70, y3 + 25), "Por qué RapidOCR (y no Tesseract/cloud)", font=f_cap, fill=GREEN)
    d.text(
        (70, y3 + 65),
        "• Local / offline (privacidad del corpus normativo)   • Ligero y embebible en el contenedor API   "
        "• OCR solo en páginas fallidas → menos latencia   • El píxel se descarta: el RAG sigue siendo textual",
        font=f_b,
        fill=INK,
    )
    d.text(
        (70, y3 + 110),
        "Código: gateway/services/pdf_extract.py  ·  Flag: RAG_PDF_OCR=1  ·  Escala: RAG_PDF_OCR_SCALE≈2",
        font=f_s,
        fill=GRAY,
    )

    out = OUT_DIR / "diagrama-ocr-selectivo.png"
    img.save(out, "PNG", optimize=True)
    print(f"Wrote {out}")


def _tokenize_line(line: str) -> list[tuple[str, tuple[int, int, int]]]:
    """Rough Python highlighting for capture slides."""
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    parts: list[tuple[str, tuple[int, int, int]]] = []
    if indent:
        parts.append((indent, CODE_FG))
    if not stripped:
        return parts or [("", CODE_FG)]
    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
        parts.append((stripped, CODE_CMT))
        return parts

    keywords = {
        "def",
        "return",
        "if",
        "elif",
        "else",
        "for",
        "in",
        "try",
        "except",
        "finally",
        "with",
        "as",
        "from",
        "import",
        "global",
        "None",
        "True",
        "False",
        "not",
        "and",
        "or",
        "await",
        "async",
        "class",
    }
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if ch in "\"'":
            quote = ch
            j = i + 1
            while j < len(stripped):
                if stripped[j] == "\\" and j + 1 < len(stripped):
                    j += 2
                    continue
                if stripped[j] == quote:
                    j += 1
                    break
                j += 1
            parts.append((stripped[i:j], CODE_STR))
            i = j
            continue
        if ch.isdigit():
            j = i
            while j < len(stripped) and (stripped[j].isdigit() or stripped[j] == "."):
                j += 1
            parts.append((stripped[i:j], CODE_NUM))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < len(stripped) and (stripped[j].isalnum() or stripped[j] == "_"):
                j += 1
            word = stripped[i:j]
            nxt = stripped[j : j + 1]
            if word in keywords:
                color = CODE_KW
            elif nxt == "(":
                color = CODE_FN
            else:
                color = CODE_FG
            parts.append((word, color))
            i = j
            continue
        parts.append((ch, CODE_FG))
        i += 1
    return parts


def compose_code_capture(
    *,
    filename: str,
    title: str,
    subtitle: str,
    lines: list[str],
    start_line: int,
):
    f_mono = font(22, mono=True)
    f_title = font(28, True)
    f_sub = font(16)
    f_gutter = font(18, mono=True)

    # measure
    line_h = 32
    pad_x, pad_y = 28, 24
    header_h = 78
    width = 1600
    height = header_h + pad_y * 2 + line_h * len(lines) + 20

    img = Image.new("RGB", (width, height), CODE_BG)
    d = ImageDraw.Draw(img)

    # header bar
    d.rectangle((0, 0, width, header_h), fill=HEADER)
    d.ellipse((22, 30, 38, 46), fill=(255, 95, 86))
    d.ellipse((48, 30, 64, 46), fill=(255, 189, 46))
    d.ellipse((74, 30, 90, 46), fill=(39, 201, 63))
    d.text((110, 18), title, font=f_title, fill=WHITE)
    d.text((110, 50), subtitle, font=f_sub, fill=(170, 170, 170))

    y = header_h + pad_y
    gutter_w = 70
    for idx, line in enumerate(lines):
        ln = start_line + idx
        d.text((pad_x, y), f"{ln:3d}", font=f_gutter, fill=GUTTER)
        x = pad_x + gutter_w
        for token, color in _tokenize_line(line):
            d.text((x, y), token, font=f_mono, fill=color)
            bbox = d.textbbox((0, 0), token, font=f_mono)
            x += bbox[2] - bbox[0]
        y += line_h

    out = OUT_DIR / filename
    img.save(out, "PNG", optimize=True)
    print(f"Wrote {out}")


def main():
    compose_ocr_diagram()

    compose_code_capture(
        filename="captura-codigo-ocr-decision.png",
        title="pdf_extract.py — decisión nativo vs OCR",
        subtitle="gateway/services/pdf_extract.py · extract_pdf_text (bucle por página)",
        start_line=194,
        lines=[
            "for index in range(limit):",
            "    page = pdf[index]",
            "    try:",
            "        native = _native_page_text(page)",
            "        chosen = native",
            "        if ocr and not is_readable_text(native, min_chars=24):",
            "            scanned = _ocr_page(page, scale)",
            "            if is_readable_text(scanned, min_chars=12) or (",
            "                scanned.strip() and latin_ratio(scanned) > latin_ratio(native)",
            "            ):",
            "                chosen = scanned",
            "                ocr_pages += 1",
            "            elif is_readable_text(native, min_chars=12):",
            "                native_pages += 1",
            "            else:",
            "                continue",
        ],
    )

    compose_code_capture(
        filename="captura-codigo-rapidocr.png",
        title="pdf_extract.py — motor RapidOCR",
        subtitle="Singleton perezoso + OCR sobre página rasterizada",
        start_line=90,
        lines=[
            "def _get_engine() -> Any:",
            "    global _ENGINE, _ENGINE_FAILED",
            "    ...",
            "    try:",
            "        from rapidocr import RapidOCR",
            "        _ENGINE = RapidOCR()",
            "    except Exception:",
            "        logger.exception(\"RapidOCR no está disponible…\")",
            "        _ENGINE_FAILED = True",
            "        return None",
            "    return _ENGINE",
            "",
            "def ocr_image(image: Any) -> str:",
            "    engine = _get_engine()",
            "    array = np.asarray(image.convert(\"RGB\"))",
            "    result = engine(array, use_cls=False)",
            "    return \"\\n\".join(str(item).strip() for item in result.txts …)",
        ],
    )

    compose_code_capture(
        filename="captura-codigo-is-readable.png",
        title="pdf_extract.py — heurística is_readable_text",
        subtitle="Evita indexar tofu, CID rotos o streams internos del PDF",
        start_line=63,
        lines=[
            "def is_readable_text(text: str, *, min_chars: int = 24) -> bool:",
            "    stripped = (text or \"\").strip()",
            "    if len(stripped) < min_chars:",
            "        return False",
            "    if looks_like_pdf_internals(stripped):",
            "        return False",
            "    if junk_ratio(stripped) >= 0.08:",
            "        return False",
            "    if latin_ratio(stripped) < 0.28:",
            "        return False",
            "    vowels = len(re.findall(r\"[aeiouáéíóú…]\", stripped))",
            "    if vowels / max(len(stripped), 1) < 0.035 and latin_ratio(stripped) < 0.55:",
            "        return False",
            "    return True",
        ],
    )

    # Copy to presentation folder
    present = ROOT.parent.parent / "presentacion_defensa"
    present.mkdir(parents=True, exist_ok=True)
    for name in (
        "diagrama-ocr-selectivo.png",
        "captura-codigo-ocr-decision.png",
        "captura-codigo-rapidocr.png",
        "captura-codigo-is-readable.png",
    ):
        src = OUT_DIR / name
        if src.exists():
            (present / name).write_bytes(src.read_bytes())
            print(f"Copied -> {present / name}")


if __name__ == "__main__":
    main()
