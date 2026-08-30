"""Diagrama del preprocesamiento documental (AgroPS / TFM)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrama-preprocesamiento-docs.png"

W, H = 2800, 1680
BG = (255, 255, 255)
NAVY = (26, 54, 93)
ACCENT = (7, 104, 169)
GREEN = (39, 103, 73)
INK = (45, 55, 72)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
SOFT = (247, 250, 252)
FILL_A = (237, 242, 247)
FILL_B = (235, 248, 255)
FILL_C = (255, 250, 240)
FILL_D = (240, 253, 244)
WHITE = (255, 255, 255)


def font(size: int, bold: bool = False):
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


def multiline(draw, x, y, lines, fnt, fill=INK, gap=26):
    for i, line in enumerate(lines):
        draw.text((x, y + i * gap), line, font=fnt, fill=fill)


def arrow_h(draw, x0, y, x1, color=ACCENT):
    draw.line([(x0, y), (x1 - 14, y)], fill=color, width=5)
    draw.polygon([(x1, y), (x1 - 16, y - 9), (x1 - 16, y + 9)], fill=color)


def arrow_v(draw, x, y0, y1, color=ACCENT):
    draw.line([(x, y0), (x, y1 - 14)], fill=color, width=5)
    draw.polygon([(x, y1), (x - 9, y1 - 16), (x + 9, y1 - 16)], fill=color)


def step_box(draw, xy, num, title, lines, fill, f_num, f_title, f_body):
    x0, y0, x1, y1 = xy
    rounded(draw, xy, 22, fill, LINE, 3)
    # badge
    bx0, by0, bx1, by1 = x0 + 18, y0 + 18, x0 + 62, y0 + 62
    rounded(draw, (bx0, by0, bx1, by1), 12, ACCENT, ACCENT, 1)
    center_text(draw, (bx0 + bx1) // 2, (by0 + by1) // 2, str(num), f_num, WHITE)
    draw.text((x0 + 78, y0 + 26), title, font=f_title, fill=NAVY)
    multiline(draw, x0 + 24, y0 + 78, lines, f_body, INK, gap=28)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f_title = font(42, True)
    f_sub = font(20)
    f_h = font(24, True)
    f_body = font(19)
    f_num = font(22, True)
    f_small = font(16)
    f_cap = font(18, True)

    d.text((56, 32), "Preprocesamiento documental — AgroPS", font=f_title, fill=NAVY)
    d.text(
        (56, 88),
        "Del fichero subido a chunks indexados (embedding + BM25) · defaults: 1400 / 120 · nomic-embed-text",
        font=f_sub,
        fill=GRAY,
    )

    # Fila 1: pasos 1-3
    y1 = 150
    h1 = 320
    boxes1 = [
        (
            (50, y1, 900, y1 + h1),
            1,
            "Almacenamiento",
            [
                "• Guarda el binario en disco (UUID)",
                "• Crea registro en documents",
                "• Crea processing_jobs = running",
                "• Responde HTTP accepted",
            ],
            FILL_A,
        ),
        (
            (960, y1, 1810, y1 + h1),
            2,
            "Extracción de texto",
            [
                "• PDF → texto nativo; OCR si ilegible (BOC/CID)",
                "• DOCX / PPTX → XML interno",
                "• MD / TXT / CSV → UTF-8",
                "• Vídeo → transcripción (si aplica)",
            ],
            FILL_B,
        ),
        (
            (1870, y1, 2750, y1 + h1),
            3,
            "Limpieza",
            [
                "• Normaliza saltos de línea",
                "• Compacta párrafos vacíos",
                "• Descarta texto no legible / basura",
                "• Tope de caracteres indexables",
            ],
            FILL_C,
        ),
    ]
    for xy, num, title, lines, fill in boxes1:
        step_box(d, xy, num, title, lines, fill, f_num, f_h, f_body)

    # flechas fila 1
    mid_y = y1 + h1 // 2
    arrow_h(d, 900, mid_y, 960)
    arrow_h(d, 1810, mid_y, 1870)

    # flecha hacia abajo al centro
    arrow_v(d, W // 2, y1 + h1, y1 + h1 + 70)

    # Fila 2: chunking (ancho)
    y2 = y1 + h1 + 80
    h2 = 280
    step_box(
        d,
        (50, y2, 2750, y2 + h2),
        4,
        "Chunking  —  split_into_chunks",
        [
            "• Ventanas de 1400 caracteres con solape de 120",
            "• Corte preferente: párrafo (\\n\\n)  →  línea (\\n)  →  espacio  (evita partir a mitad de frase)",
            "• Cada fragmento conserva trazabilidad al documento fuente (document_id / chunk_id)",
            "• Filtra chunks demasiado cortos o ilegibles antes de embeber",
        ],
        FILL_B,
        f_num,
        f_h,
        f_body,
    )

    arrow_v(d, W // 2, y2 + h2, y2 + h2 + 70)

    # Fila 3: indexación + caché
    y3 = y2 + h2 + 80
    h3 = 300
    step_box(
        d,
        (50, y3, 1380, y3 + h3),
        5,
        "Indexación",
        [
            "• Cada chunk → embedding (nomic-embed-text)",
            "• Persistencia en PostgreSQL + pgvector",
            "• Actualización del índice léxico BM25",
            "• Listo para búsqueda híbrida (denso + BM25 + RRF)",
        ],
        FILL_D,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (1440, y3, 2750, y3 + h3),
        6,
        "Invalidación de caché",
        [
            "• Limpia la caché de retrieval del tenant",
            "• Las nuevas búsquedas ven el documento",
            "• Evita rankings obsoletos post-ingesta",
            "• Ámbito: mismo tenant / KB",
        ],
        FILL_A,
        f_num,
        f_h,
        f_body,
    )
    arrow_h(d, 1380, y3 + h3 // 2, 1440, GREEN)

    # pie
    rounded(d, (50, H - 110, 2750, H - 40), 14, SOFT, LINE, 2)
    d.text(
        (70, H - 88),
        "Código: extract_index_text + split_into_chunks (embedding_reindex.py) · orquestación: document_ingest.py",
        font=f_small,
        fill=GRAY,
    )
    d.text(
        (1880, H - 88),
        "AgroPS · TFM Samuel Lorenzo Sánchez",
        font=f_cap,
        fill=NAVY,
    )

    img.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
