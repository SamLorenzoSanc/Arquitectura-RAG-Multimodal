"""Figura única para el tribunal: cómo se aplica Ports & Adapters en AgroPS."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
LOGOS = ROOT / "logos"
OUT_PNG = ROOT / "hexagono-rag-agrops.png"

W, H = 2800, 1580
BG = (255, 255, 255)
NAVY = (26, 54, 93)
APP = (43, 108, 176)
FW = (186, 220, 244)
PORT = (56, 161, 105)
SIDE = (197, 48, 48)
ACTOR = (226, 232, 240)
INK = (15, 23, 42)
MUTED = (71, 85, 105)
LINE = (160, 174, 192)
WHITE = (255, 255, 255)
GRAY = (113, 128, 150)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hex_pts(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    start = -math.pi / 2
    return [
        (cx + r * math.cos(start + i * math.pi / 3), cy + r * math.sin(start + i * math.pi / 3))
        for i in range(6)
    ]


def draw_hex(draw, cx, cy, r, fill, outline, width=3):
    if outline and width > 0:
        draw.polygon(hex_pts(cx, cy, r + width * 0.4), fill=outline)
    draw.polygon(hex_pts(cx, cy, r - width * 0.15), fill=fill)


def text_size(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def text_center(draw, xy, text, fnt, fill):
    w, h = text_size(draw, text, fnt)
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - w / 2, xy[1] - h / 2 - bbox[1]), text, font=fnt, fill=fill)


def rounded(draw, xy, r, fill, outline, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def pill(draw, xy, text, fnt, fill=PORT, fg=WHITE):
    rounded(draw, xy, 6, fill, fill, 1)
    x1, y1, x2, y2 = xy
    text_center(draw, ((x1 + x2) / 2, (y1 + y2) / 2), text, fnt, fg)


def fit_logo(path: Path, max_w: int, max_h: int):
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img


def paste_center(base, logo, cx, cy):
    if logo is None:
        return
    base.alpha_composite(logo, (int(cx - logo.width / 2), int(cy - logo.height / 2)))


def arrow(draw, a, b, fill=APP, width=5):
    draw.line([a, b], fill=fill, width=width)
    x, y = b
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    left = (x - 18 * ux + 10 * uy, y - 18 * uy - 10 * ux)
    right = (x - 18 * ux - 10 * uy, y - 18 * uy + 10 * ux)
    draw.polygon([b, left, right], fill=fill)


def actor_card(draw, xy, title, lines, f_title, f_body):
    rounded(draw, xy, 16, WHITE, LINE, 3)
    x1, y1, x2, y2 = xy
    text_center(draw, ((x1 + x2) / 2, y1 + 36), title, f_title, NAVY)
    y = y1 + 70
    for line in lines:
        text_center(draw, ((x1 + x2) / 2, y), line, f_body, MUTED)
        y += 28


def main() -> None:
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)

    f_title = font(38, True)
    f_h2 = font(20, True)
    f_h3 = font(17, True)
    f_body = font(16)
    f_small = font(15)
    f_tiny = font(14)
    f_hex = font(22, True)
    f_hex_sub = font(15)
    f_cap = font(17)

    d.text((48, 24), "Aplicación de la arquitectura hexagonal en AgroPS", font=f_title, fill=NAVY)
    d.text(
        (48, 74),
        "Ports & Adapters (Cockburn, 2005)  ·  el dominio RAG no depende de FastAPI, PostgreSQL ni Ollama",
        font=f_body,
        fill=MUTED,
    )

    pill(d, (48, 118, 290, 154), "Lado conductor", f_h3, SIDE)
    pill(d, (2488, 118, 2752, 154), "Lado dirigido", f_h3, SIDE)

    legend = [(NAVY, "Dominio"), (APP, "Aplicación"), (FW, "Adaptadores"), (PORT, "Puertos")]
    lx = 1680
    for fill, lab in legend:
        d.rounded_rectangle((lx, 78, lx + 18, 96), 3, fill=fill)
        d.text((lx + 24, 74), lab, font=f_tiny, fill=NAVY)
        lx += 150

    # --- Hexágono ---
    cx, cy = 1400, 820
    r_fw, r_app, r_dom = 390, 275, 155
    draw_hex(d, cx, cy, r_fw, FW, (90, 140, 180), 5)
    draw_hex(d, cx, cy, r_app, APP, (30, 80, 140), 4)
    draw_hex(d, cx, cy, r_dom, NAVY, NAVY, 3)

    text_center(d, (cx, cy - 28), "DOMINIO", f_hex, WHITE)
    text_center(d, (cx, cy + 2), "rag/domain", f_tiny, (190, 210, 230))
    text_center(d, (cx, cy + 28), "RetrievedChunk", f_small, WHITE)
    text_center(d, (cx, cy + 50), "RRF · citación", f_small, WHITE)

    text_center(d, (cx, cy - r_app + 28), "APLICACIÓN", f_h2, WHITE)
    text_center(d, (cx, cy - r_app + 52), "rag/application", f_tiny, (220, 235, 250))
    text_center(d, (cx, cy + r_app - 58), "IngestDocument", f_small, WHITE)
    text_center(d, (cx, cy + r_app - 36), "HybridRetrieve · AnswerQuestion", f_small, WHITE)

    text_center(d, (cx, cy - r_fw + 26), "ADAPTADORES", f_h2, NAVY)
    text_center(d, (cx, cy - r_fw + 50), "rag/adapters", f_tiny, NAVY)

    f_pill = font(14, True)
    pill(d, (cx - 330, cy - 18, cx - 178, cy + 16), "Adapter In", f_pill)
    pill(d, (cx - 248, cy + 40, cx - 148, cy + 70), "Port In", f_pill)
    pill(d, (cx + 148, cy + 40, cx + 248, cy + 70), "Port Out", f_pill)
    pill(d, (cx + 178, cy - 18, cx + 338, cy + 16), "Adapter Out", f_pill)

    # --- Conductor ---
    actor_card(
        d,
        (48, 210, 360, 400),
        "Técnico / UI",
        ["React · Vite · Tailwind", "login · documentos · chat"],
        f_h2,
        f_small,
    )
    actor_card(
        d,
        (48, 440, 360, 640),
        "API REST",
        ["FastAPI  /api/v1", "auth · documents · chat"],
        f_h2,
        f_small,
    )
    actor_card(
        d,
        (48, 680, 360, 860),
        "Pruebas",
        ["test_rag_hexagon", "puertos falsos (mocks)"],
        f_h2,
        f_small,
    )

    paste_center(img, fit_logo(LOGOS / "react.png", 40, 40), 88, 248)
    paste_center(img, fit_logo(LOGOS / "fastapi-logo.png", 44, 44), 88, 478)

    d.line([(390, 305), (390, 770)], fill=APP, width=4)
    d.polygon([(390, 305), (382, 321), (398, 321)], fill=APP)
    d.polygon([(390, 770), (382, 754), (398, 754)], fill=APP)
    d.text((400, 520), "API", font=f_h3, fill=APP)
    arrow(d, (360, 305), (390, 305), APP, 4)
    arrow(d, (360, 540), (390, 540), APP, 4)
    arrow(d, (360, 770), (390, 770), APP, 4)
    d.line([(430, 305), (430, cy)], fill=APP, width=4)
    arrow(d, (430, cy), (cx - 330, cy), APP, 5)

    # --- Dirigido ---
    actor_card(
        d,
        (2440, 210, 2752, 430),
        "Base de datos",
        ["PostgreSQL", "pgvector  ·  HNSW"],
        f_h2,
        f_small,
    )
    actor_card(
        d,
        (2440, 470, 2752, 710),
        "Inferencia",
        ["Ollama", "Llama 3.2", "qwen3-embedding"],
        f_h2,
        f_small,
    )
    actor_card(
        d,
        (2440, 750, 2752, 930),
        "Índice léxico",
        ["BM25", "Cross-Encoder"],
        f_h2,
        f_small,
    )

    paste_center(img, fit_logo(LOGOS / "postgresql.png", 46, 46), 2488, 252)
    paste_center(img, fit_logo(LOGOS / "ollama.png", 52, 36), 2492, 512)

    d.line([(2370, 320), (2370, 840)], fill=APP, width=4)
    d.polygon([(2370, 320), (2362, 336), (2378, 336)], fill=APP)
    d.polygon([(2370, 840), (2362, 824), (2378, 824)], fill=APP)
    spi_w = text_size(d, "SPI", f_h3)[0]
    d.text((2370 - spi_w - 10, 560), "SPI", font=f_h3, fill=APP)
    arrow(d, (cx + 338, cy), (2330, cy), APP, 5)
    d.line([(2330, 320), (2330, 840)], fill=APP, width=4)
    arrow(d, (2330, 320), (2440, 320), APP, 4)
    arrow(d, (2330, 590), (2440, 590), APP, 4)
    arrow(d, (2330, 840), (2440, 840), APP, 4)

    # --- Composition root ---
    rounded(d, (520, 1288, 2280, 1478), 16, (248, 250, 252), LINE, 2)
    d.text((548, 1308), "Composition root   ·   rag/composition.py   ·   build_rag_container()", font=f_h2, fill=NAVY)
    d.text(
        (548, 1348),
        "Cablea los adaptadores concretos a los puertos del dominio. El caso de uso recibe interfaces, no SQLAlchemy ni Ollama.",
        font=f_small,
        fill=INK,
    )
    d.text(
        (548, 1382),
        "Puertos de salida:  ChunkRepository   ·   EmbeddingPort   ·   LlmPort   ·   LexicalIndexPort   ·   RerankerPort",
        font=f_small,
        fill=NAVY,
    )
    d.text(
        (548, 1418),
        "Adaptadores reales:  PgvectorChunkRepository   ·   OllamaEmbeddingAdapter / OllamaLlmAdapter   ·   Bm25LexicalIndex",
        font=f_small,
        fill=MUTED,
    )
    d.text(
        (548, 1450),
        "Idea a defender: cambiar de LLM o de almacén vectorial = cambiar el adaptador. Las reglas de citación y RRF no se tocan.",
        font=f_small,
        fill=SIDE,
    )

    cap = "AgroPS MVP  ·  FastAPI hexagonal  ·  PostgreSQL/pgvector  ·  Ollama (Llama 3.2 + qwen3-embedding)  ·  React / Vite / Tailwind"
    cw = d.textlength(cap, font=f_cap)
    d.text(((W - cw) / 2, H - 42), cap, font=f_cap, fill=GRAY)

    rgb = Image.new("RGB", img.size, BG)
    rgb.paste(img, mask=img.split()[-1])
    rgb.save(OUT_PNG, "PNG", dpi=(180, 180))
    print("wrote", OUT_PNG, rgb.size)


if __name__ == "__main__":
    main()
