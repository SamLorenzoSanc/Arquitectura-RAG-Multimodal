"""Esquema del back-end: dominio, aplicación (puertos) y adaptadores (estilo PolicyOps / Fig. 3.3)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
LOGOS = ROOT / "logos"
OUT = ROOT / "esquema-backend-agrops.png"

W, H = 2400, 1320
BG = (255, 255, 255)
NAVY = (26, 54, 93)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
PORT = (56, 161, 105)
FILL_OUT = (247, 250, 252)
FILL_APP = (237, 242, 247)
FILL_DOM = (226, 232, 240)
WHITE = (255, 255, 255)
INK = (45, 55, 72)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded(draw, xy, r, fill, outline, width=3):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


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


def section_title(draw, xy, text, fnt):
    draw.text(xy, text, font=fnt, fill=NAVY)


def bullet_list(draw, xy, headers, items, f_h, f_b, gap=38):
    x, y = xy
    for head in headers:
        draw.text((x, y), head, font=f_h, fill=NAVY)
        y += gap
    for item in items:
        if not item:
            y += 12
            continue
        draw.text((x, y), item, font=f_b, fill=INK)
        y += gap - 4
    return y


def port_arrow(draw, start, end):
    draw.line([start, end], fill=PORT, width=3)
    x, y = end
    draw.polygon([(x, y), (x - 14, y - 7), (x - 14, y + 7)], fill=PORT)
    mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
    draw.text((mid[0] - 28, mid[1] - 22), "Puerto", font=font(15, True), fill=PORT)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f_title = font(44, True)
    f_h1 = font(28, True)
    f_h2 = font(22, True)
    f_body = font(20)
    f_small = font(17)
    f_cap = font(22)

    python = fit_logo(LOGOS / "python.png", 72, 72)
    if python:
        img.alpha_composite(python, (48, 34))
    d.text((132, 46), "BACK-END", font=f_title, fill=NAVY)
    d.text((132, 92), "Python · FastAPI · arquitectura hexagonal (puertos y adaptadores)", font=f_small, fill=GRAY)

    # --- Anillo exterior: adaptadores ---
    outer = (36, 128, W - 36, H - 72)
    rounded(d, outer, 26, FILL_OUT, LINE, 3)
    section_title(d, (68, 146), "ADAPTADORES", f_h1)

    # --- Capa aplicación ---
    app_box = (72, 208, W - 72, 820)
    rounded(d, app_box, 22, FILL_APP, LINE, 3)
    section_title(d, (104, 226), "APLICACIÓN", f_h1)

    # --- Dominio (centro) ---
    dom_box = (860, 290, 1540, 760)
    rounded(d, dom_box, 18, FILL_DOM, NAVY, 3)
    section_title(d, (920, 318), "DOMINIO", f_h1)
    y = 378
    for head, lines in [
        ("Entidades", ["RetrievedChunk · RetrievalBundle"]),
        ("Objetos valor", ["RetrievalQuery"]),
        ("Reglas puras", ["rrf_fusion · expand_agro_query", "decide_is_hallucination (eval)"]),
    ]:
        d.text((900, y), head, font=f_h2, fill=NAVY)
        y += 38
        for line in lines:
            d.text((900, y), line, font=f_body, fill=INK)
            y += 34
        y += 16

    # --- Casos de uso (izquierda) ---
    bullet_list(
        d,
        (110, 300),
        ["CASOS DE USO"],
        [
            "HybridRetrieve",
            "AnswerQuestion",
            "IngestDocument",
            "EvaluateRetrieval",
            "EvaluateAnswer",
            "",
            "LoginUser · RegisterUser",
            "decide_review (HITL)",
        ],
        f_h2,
        f_body,
    )

    # --- Puertos de entrada (izquierda, debajo) ---
    bullet_list(
        d,
        (110, 620),
        ["PUERTOS DE ENTRADA"],
        [
            "execute (RAGService)",
            "POST /api/v1/chat",
            "POST /api/v1/documents",
            "POST /evaluation/*",
            "POST /human-validation/*",
        ],
        f_h2,
        f_body,
        gap=36,
    )

    # --- Puertos de salida (derecha) ---
    bullet_list(
        d,
        (1620, 300),
        ["PUERTOS DE SALIDA"],
        [
            "ChunkRepository",
            "EmbeddingPort",
            "LlmPort",
            "LexicalIndexPort",
            "RerankerPort",
            "",
            "UserRepository",
            "TokenSigner · PasswordHasher",
        ],
        f_h2,
        f_body,
    )

    d.text(
        (104, 780),
        "Los casos de uso dependen solo de los puertos (interfaces), no de PostgreSQL ni Ollama.",
        font=f_small,
        fill=GRAY,
    )

    # --- Tarjetas adaptador (parte inferior del anillo exterior) ---
    cards = [
        (120, "Adaptador API REST", "FastAPI  /api/v1", LOGOS / "fastapi-logo.png"),
        (680, "Adaptador PostgreSQL", "pgvector · HNSW", LOGOS / "postgresql.png"),
        (1240, "Adaptador Ollama", "Llama 3.2 · embeddings", LOGOS / "ollama.png"),
        (1800, "Adaptador BM25", "índice léxico / tenant", None),
    ]
    card_y1, card_y2 = 860, 1180
    card_w = 480
    for x, title, sub, logo_path in cards:
        box = (x, card_y1, x + card_w, card_y2)
        rounded(d, box, 16, WHITE, LINE, 3)
        logo = fit_logo(logo_path, 88, 88) if logo_path else None
        if logo:
            paste_center(img, logo, x + card_w / 2, card_y1 + 72)
        else:
            d.text((x + card_w / 2 - 24, card_y1 + 58), "BM25", font=f_h1, fill=NAVY)
        tw = d.textlength(title, font=f_h2)
        d.text((x + (card_w - tw) / 2, card_y1 + 128), title, font=f_h2, fill=NAVY)
        sw = d.textlength(sub, font=f_small)
        d.text((x + (card_w - sw) / 2, card_y1 + 168), sub, font=f_small, fill=GRAY)

    # Flechas puerto → adaptador
    port_arrow(d, (380, 760), (320, 860))
    port_arrow(d, (1200, 760), (920, 860))
    port_arrow(d, (1200, 760), (1480, 860))
    port_arrow(d, (1200, 760), (2040, 860))

    # Composition root
    rounded(d, (120, 1200, W - 120, 1288), 12, (248, 250, 252), LINE, 2)
    d.text(
        (148, 1218),
        "Composition root: build_rag_container() cablea adaptadores concretos → puertos. "
        "Cambiar Ollama o pgvector = cambiar adaptador, no el dominio.",
        font=f_small,
        fill=INK,
    )

    cap = "Figura: Esquema del back-end (dominio · aplicación · puertos · adaptadores)"
    cw = d.textlength(cap, font=f_cap)
    d.text(((W - cw) / 2, H - 48), cap, font=f_cap, fill=GRAY)

    rgb = Image.new("RGB", img.size, BG)
    rgb.paste(img, mask=img.split()[-1])
    rgb.save(OUT, "PNG", dpi=(180, 180))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
