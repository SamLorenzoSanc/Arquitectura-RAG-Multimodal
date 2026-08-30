"""Diagrama del pipeline de ingesta RAG (AgroPS / TFM)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrama-ingesta-rag.png"

W, H = 2600, 1480
BG = (255, 255, 255)
NAVY = (26, 54, 93)
ACCENT = (7, 104, 169)
INK = (45, 55, 72)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
SOFT = (247, 250, 252)
FILL_SYNC = (237, 242, 247)
FILL_ASYNC = (235, 248, 255)
FILL_STORE = (240, 253, 244)
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


def multiline_center(draw, cx, y, lines, fnt, fill=INK, gap=28):
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw / 2, y + i * gap), line, font=fnt, fill=fill)


def arrow_h(draw, x0, y, x1, color=ACCENT):
    draw.line([(x0, y), (x1 - 14, y)], fill=color, width=4)
    draw.polygon([(x1, y), (x1 - 16, y - 9), (x1 - 16, y + 9)], fill=color)


def arrow_v(draw, x, y0, y1, color=ACCENT):
    draw.line([(x, y0), (x, y1 - 14)], fill=color, width=4)
    draw.polygon([(x, y1), (x - 9, y1 - 16), (x + 9, y1 - 16)], fill=color)


def phase_box(draw, xy, title, lines, fill, f_title, f_body, f_sub=None, subtitle=None):
    x0, y0, x1, y1 = xy
    rounded(draw, xy, 20, fill, LINE, 3)
    cx = (x0 + x1) // 2
    center_text(draw, cx, y0 + 36, title, f_title, NAVY)
    if subtitle and f_sub:
        center_text(draw, cx, y0 + 68, subtitle, f_sub, GRAY)
        start_y = y0 + 100
    else:
        start_y = y0 + 78
    multiline_center(draw, cx, start_y, lines, f_body, INK, gap=30)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f_title = font(40, True)
    f_h = font(24, True)
    f_body = font(20)
    f_small = font(17)
    f_cap = font(18, True)
    f_tiny = font(15)

    d.text((56, 36), "Pipeline de ingesta RAG — AgroPS", font=f_title, fill=NAVY)
    d.text(
        (56, 88),
        "De fichero subido a chunks + embeddings + índice BM25 (defaults: 1400/120, nomic-embed-text)",
        font=f_small,
        fill=GRAY,
    )

    # Bandas de fase
    band_y0, band_y1 = 140, 520
    rounded(d, (40, band_y0, W - 40, band_y1), 24, FILL_SYNC, LINE, 2)
    d.text((64, band_y0 + 16), "FASE SÍNCRONA (HTTP)", font=f_cap, fill=NAVY)

    # Cajas fila superior
    boxes_top = [
        (
            (70, 200, 470, 470),
            "1. Upload",
            "POST /api/v1/documents",
            [
                "Multipart + JWT",
                "Tope 100 MiB",
                "Tenant + Knowledge Base",
            ],
            FILL_SYNC,
        ),
        (
            (520, 200, 960, 470),
            "2. Persistencia",
            "disco + PostgreSQL",
            [
                "LocalFileStorage (UUID)",
                "documents + file_hash",
                "processing_jobs = running",
                "HTTP accepted",
            ],
            FILL_SYNC,
        ),
        (
            (1010, 200, 1450, 470),
            "3. Cola local",
            "asyncio.create_task",
            [
                "Mismo proceso gateway",
                "Sin Redis / Celery",
                "Progreso en memoria",
            ],
            FILL_ASYNC,
        ),
    ]
    for xy, title, sub, lines, fill in boxes_top:
        phase_box(d, xy, title, lines, fill, f_h, f_body, f_tiny, sub)

    arrow_h(d, 470, 335, 520)
    arrow_h(d, 960, 335, 1010)

    # Flecha hacia banda async
    arrow_v(d, 1230, 470, 560)

    # Banda asíncrona
    rounded(d, (40, 560, W - 40, 1180), 24, FILL_ASYNC, LINE, 2)
    d.text((64, 576), "FASE ASÍNCRONA (ingest_uploaded_document)", font=f_cap, fill=ACCENT)

    boxes_mid = [
        (
            (70, 640, 560, 980),
            "4. Extracción",
            "extract_index_text",
            [
                "MD / TXT / CSV: UTF-8",
                "DOCX / PPTX: XML Office",
                "PDF: nativo + OCR selectivo",
                "Vídeo: Whisper (opcional)",
                "Tope 400 000 caracteres",
            ],
            WHITE,
        ),
        (
            (610, 640, 1100, 980),
            "5. Chunking",
            "split_into_chunks",
            [
                "Ventana S = 1400",
                "Solape O = 120",
                "Corte: ¶ → línea → espacio",
                "Filtro is_readable_text",
                "INSERT chunks",
            ],
            WHITE,
        ),
        (
            (1150, 640, 1680, 980),
            "6. Embeddings",
            "Ollama /api/embed",
            [
                "Modelo: nomic-embed-text",
                "Payload = content",
                "Lotes de 64",
                "Pad a 4096 dims",
                "INSERT embeddings",
            ],
            WHITE,
        ),
        (
            (1730, 640, 2520, 980),
            "7. Cierre léxico",
            "IngestDocument",
            [
                "Rebuild BM25 del tenant",
                "Texto: headline+summary+content",
                "Invalidar caché retrieve",
                "Job → completed / failed",
            ],
            FILL_STORE,
        ),
    ]
    for xy, title, sub, lines, fill in boxes_mid:
        phase_box(d, xy, title, lines, fill, f_h, f_body, f_tiny, sub)

    arrow_h(d, 560, 810, 610)
    arrow_h(d, 1100, 810, 1150)
    arrow_h(d, 1680, 810, 1730)

    # Detalle PDF OCR (caja inferior dentro de async)
    rounded(d, (70, 1010, 1100, 1150), 16, SOFT, LINE, 2)
    d.text((90, 1028), "Detalle PDF (alg. extract-pdf)", font=f_cap, fill=NAVY)
    d.text(
        (90, 1068),
        "Por página: texto nativo (pypdfium2) → si ilegible y RAG_PDF_OCR=true → raster + RapidOCR → unir páginas.",
        font=f_small,
        fill=INK,
    )
    d.text(
        (90, 1104),
        "Heurística: ratio latino, basura Unicode, streams internos PDF, vocales. Máx. 120 páginas.",
        font=f_small,
        fill=INK,
    )

    rounded(d, (1150, 1010, 2520, 1150), 16, FILL_STORE, LINE, 2)
    d.text((1170, 1028), "Almacenamiento resultante", font=f_cap, fill=NAVY)
    d.text(
        (1170, 1068),
        "PostgreSQL: documents · chunks · embeddings (pgvector / HNSW) · processing_jobs",
        font=f_small,
        fill=INK,
    )
    d.text(
        (1170, 1104),
        "Disco: DOCUMENT_STORAGE_ROOT + services/bm25_indexes/tenant_<id>.pkl",
        font=f_small,
        fill=INK,
    )

    # Pie
    d.text(
        (56, 1220),
        "Nota: el hexágono RAG solo cubre el cierre BM25 (paso 7). Extract / chunk / embed viven en gateway/services/.",
        font=f_small,
        fill=GRAY,
    )
    d.text(
        (56, 1260),
        "Asimetría del prototipo: el embedding usa solo content; BM25 indexa headline + summary + content.",
        font=f_small,
        fill=GRAY,
    )

    # Leyenda
    rounded(d, (56, 1320, 220, 1380), 10, FILL_SYNC, LINE, 2)
    d.text((240, 1336), "HTTP síncrono", font=f_small, fill=INK)
    rounded(d, (480, 1320, 644, 1380), 10, FILL_ASYNC, LINE, 2)
    d.text((664, 1336), "Procesado async", font=f_small, fill=INK)
    rounded(d, (920, 1320, 1084, 1380), 10, FILL_STORE, LINE, 2)
    d.text((1104, 1336), "Índices listos", font=f_small, fill=INK)

    rgb = img.convert("RGB")
    rgb.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
