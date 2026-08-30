"""Diagrama: documentos y prompt → mismo embedding → pgvector → k-NN."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUTS = [
    HERE / "diagrama-embeddings-knn.png",
    HERE.parent / "memoria-latex" / "figures" / "diagrama-embeddings-knn.png",
]

W, H = 2480, 1080
BG = (247, 245, 240)
INK = (26, 46, 26)
MUTED = (74, 92, 74)
ACCENT = (47, 107, 58)
ACCENT2 = (196, 122, 42)
WHITE = (255, 255, 255)
CARD = (255, 255, 255)
SOFT = (232, 239, 230)
LINE = (176, 191, 176)
AMBER = (255, 247, 232)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded(draw, xy, r=20, fill=CARD, outline=LINE, width=3):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def center(draw, cx, cy, text, fnt, fill=INK):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2), text, font=fnt, fill=fill)


def arrow_h(draw, x0, y, x1, color=ACCENT, width=6):
    draw.line([(x0, y), (x1 - 18, y)], fill=color, width=width)
    draw.polygon([(x1, y), (x1 - 20, y - 10), (x1 - 20, y + 10)], fill=color)


def document_icon(draw, x, y, w=72, h=88):
    fold = 18
    draw.polygon(
        [(x, y), (x + w - fold, y), (x + w, y + fold), (x + w, y + h), (x, y + h)],
        fill=SOFT,
        outline=ACCENT,
    )
    draw.polygon(
        [(x + w - fold, y), (x + w, y + fold), (x + w - fold, y + fold)],
        fill=WHITE,
        outline=ACCENT,
    )
    for i in range(3):
        yy = y + 32 + i * 14
        draw.line([(x + 12, yy), (x + w - 14, yy)], fill=ACCENT, width=3)


def cylinder(draw, x, y, w, h):
    ry = 32
    draw.ellipse([x, y + h - ry * 2, x + w, y + h], fill=SOFT, outline=ACCENT, width=4)
    draw.rectangle([x, y + ry, x + w, y + h - ry], fill=SOFT, outline=None)
    draw.line([(x, y + ry), (x, y + h - ry)], fill=ACCENT, width=4)
    draw.line([(x + w, y + ry), (x + w, y + h - ry)], fill=ACCENT, width=4)
    draw.ellipse([x, y, x + w, y + ry * 2], fill=WHITE, outline=ACCENT, width=4)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_h = font(24, True)
    f_body = font(20)
    f_small = font(17)
    f_tiny = font(15)
    f_badge = font(16, True)

    # Legend
    rounded(d, (40, 24, 430, 92), 14, WHITE, ACCENT, 2)
    d.ellipse([62, 46, 90, 74], fill=ACCENT)
    d.text((104, 48), "1  Ingesta (documentos)", font=f_badge, fill=ACCENT)
    rounded(d, (450, 24, 860, 92), 14, WHITE, ACCENT2, 2)
    d.ellipse([472, 46, 500, 74], fill=ACCENT2)
    d.text((514, 48), "2  Consulta (prompt)", font=f_badge, fill=ACCENT2)
    d.text(
        (890, 44),
        "Mismo modelo nomic-embed-text  ·  distancia coseno  ·  k = 10",
        font=f_small,
        fill=MUTED,
    )

    # Geometry
    doc = (50, 140, 420, 360)
    prompt = (50, 700, 420, 940)
    model = (600, 220, 1240, 720)
    pg = (1460, 130, 1880, 460)
    knn = (1980, 180, 2430, 410)
    query = (600, 820, 1240, 940)

    # Documentos
    rounded(d, doc, 20, WHITE, ACCENT, 4)
    document_icon(d, 80, 188)
    d.text((175, 198), "Documentos", font=f_h, fill=INK)
    d.text((175, 238), "chunks de la KB", font=f_body, fill=MUTED)
    d.text((80, 300), "PDF / texto fragmentado", font=f_tiny, fill=MUTED)
    d.text((80, 326), "se embebe el content", font=f_tiny, fill=MUTED)

    # Prompt
    rounded(d, prompt, 20, WHITE, ACCENT2, 4)
    d.rounded_rectangle((80, 760, 152, 832), 12, fill=AMBER, outline=ACCENT2, width=3)
    center(d, 116, 796, "?", font(28, True), ACCENT2)
    d.text((175, 768), "Prompt", font=f_h, fill=INK)
    d.text((175, 810), "pregunta del usuario", font=f_body, fill=MUTED)
    d.text((80, 870), "Mismo modelo que la ingesta", font=f_tiny, fill=MUTED)
    d.text((80, 896), "si cambia, hay que reindexar", font=f_tiny, fill=MUTED)

    # Embedding model
    rounded(d, model, 26, WHITE, INK, 4)
    d.rectangle((600, 220, 1240, 286), fill=ACCENT)
    center(d, 920, 253, "Embedding model", font(26, True), WHITE)
    center(d, 920, 370, "nomic-embed-text", f_h, ACCENT)
    center(d, 920, 420, "texto  →  vector 768-d", f_body, MUTED)
    center(d, 920, 500, "Un solo espacio semántico", f_body, INK)
    center(d, 920, 546, "pregunta y chunks comparables", f_small, MUTED)
    center(d, 920, 620, "padding a 4096 para pgvector", f_tiny, MUTED)
    center(d, 920, 680, "① entra arriba   ② entra abajo", f_tiny, MUTED)

    # pgvector
    cylinder(d, pg[0], pg[1], pg[2] - pg[0], pg[3] - pg[1])
    cx_pg = (pg[0] + pg[2]) / 2
    center(d, cx_pg, 210, "pgvector", f_h, INK)
    center(d, cx_pg, 255, "PostgreSQL", f_small, MUTED)
    center(d, cx_pg, 330, "HNSW · coseno", f_body, ACCENT)
    center(d, cx_pg, 372, "vector_cosine_ops", f_tiny, MUTED)

    # k nearest
    rounded(d, knn, 20, SOFT, ACCENT, 4)
    center(d, 2205, 230, "k más cercanos", f_h, INK)
    center(d, 2205, 280, "k = 10", font(28, True), ACCENT)
    center(d, 2205, 328, "retrieval_k", f_small, MUTED)
    center(d, 2205, 368, "chunks → prompt del LLM", f_tiny, MUTED)

    # Query chip
    rounded(d, query, 16, AMBER, ACCENT2, 3)
    center(d, 920, 880, "Query  =  vector de la pregunta", f_h, ACCENT2)

    # Arrows ① documentos → model (y=250, into model left at mid-upper)
    y_in = 250
    arrow_h(d, 420, y_in, 600, ACCENT, 7)
    center(d, 510, 218, "① indexar", f_tiny, ACCENT)

    # model → pgvector (same height, from model right)
    # model top is 220; y_in=250 is inside the green header — better use y=250 still
    # Actually 250 is in the header bar. Use y=250 from docs center... docs center is (140+360)/2=250. Good.
    # Model left is 600. Header occupies 220-286, so y=250 hits the header. Raise docs arrow to 250 is ok visually as "into the model".
    arrow_h(d, 1240, y_in, 1460, ACCENT, 7)
    center(d, 1350, 218, "vectores", f_tiny, ACCENT)

    # pgvector → k
    arrow_h(d, 1880, 295, 1980, ACCENT, 7)

    # ② prompt → model (right then up into lower-left of model)
    y_pr = 820
    x_elbow = 510
    d.line([(420, y_pr), (x_elbow, y_pr)], fill=ACCENT2, width=7)
    d.line([(x_elbow, y_pr), (x_elbow, 560)], fill=ACCENT2, width=7)
    arrow_h(d, x_elbow, 560, 600, ACCENT2, 7)
    center(d, 490, 780, "② embed", f_tiny, ACCENT2)

    # model bottom → query chip
    d.line([(920, 720), (920, 820)], fill=ACCENT2, width=7)
    d.polygon([(920, 820), (910, 800), (930, 800)], fill=ACCENT2)

    # query → right → up into pgvector bottom
    qx = 1670
    d.line([(1240, 880), (qx, 880)], fill=ACCENT2, width=7)
    d.line([(qx, 880), (qx, 460)], fill=ACCENT2, width=7)
    d.polygon([(qx, 460), (qx - 10, 480), (qx + 10, 480)], fill=ACCENT2)
    center(d, 1455, 910, "buscar por distancia coseno", f_tiny, ACCENT2)

    # Caption
    rounded(d, (50, 980, 2430, 1052), 14, WHITE, LINE, 2)
    d.text(
        (70, 1002),
        "k-NN no vota una clase: ordena chunks por d_cos(query, chunk) y devuelve los 10 más cercanos. BM25/RRF van después, fuera de este diagrama.",
        font=f_small,
        fill=INK,
    )

    for out in OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, "PNG")
        print("OK", out)


if __name__ == "__main__":
    main()
