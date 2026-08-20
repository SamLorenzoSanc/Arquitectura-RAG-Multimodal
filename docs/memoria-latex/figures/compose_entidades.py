"""Diagrama de entidades estilo Figura 3.4 (PolicyOps) para AgroPS — persistencia."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "entidades-backend-agrops.png"

W, H = 2100, 1180
BG = (255, 255, 255)
INK = (32, 32, 32)
GRAY = (100, 100, 100)
PURPLE = (176, 150, 214)
TEAL = (92, 184, 176)
YELLOW = (232, 205, 92)
LILAC = (206, 186, 230)
WHITE = (255, 255, 255)
EDGE = (40, 40, 40)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def card(draw, xy, header, color, attrs, f_title, f_body):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=12, fill=WHITE, outline=EDGE, width=3)
    draw.rounded_rectangle((x1, y1, x2, y1 + 64), radius=12, fill=color, outline=EDGE, width=3)
    draw.rectangle((x1 + 3, y1 + 44, x2 - 3, y1 + 64), fill=color)
    tw = draw.textlength(header, font=f_title)
    draw.text((x1 + (x2 - x1 - tw) / 2, y1 + 16), header, font=f_title, fill=INK)
    y = y1 + 92
    for attr in attrs:
        draw.ellipse((x1 + 30, y + 11, x1 + 40, y + 21), fill=INK)
        draw.text((x1 + 56, y + 2), attr, font=f_body, fill=INK)
        y += 40


def arrow(draw, a, b):
    draw.line([a, b], fill=EDGE, width=4)
    x, y = b
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    left = (x - 16 * ux + 10 * uy, y - 16 * uy - 10 * ux)
    right = (x - 16 * ux - 10 * uy, y - 16 * uy + 10 * ux)
    draw.polygon([b, left, right], fill=EDGE)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = font(30, True)
    f_body = font(23)
    f_cap = font(26)

    # Posiciones al estilo Fig. 3.4: arriba centro, medio izq/der, abajo derecha
    tenant = (680, 36, 1420, 310)
    kb = (80, 420, 680, 760)
    doc = (1420, 400, 2020, 760)
    chunk = (1420, 860, 2020, 1100)

    card(
        d,
        tenant,
        "TENANT",
        PURPLE,
        [
            "Identificador",
            "Nombre",
            "Organización",
            "Bases de conocimiento",
            "Documentos asociados",
        ],
        f_title,
        f_body,
    )
    card(
        d,
        kb,
        "KNOWLEDGE BASE",
        TEAL,
        [
            "Identificador",
            "Nombre",
            "Tenant al que pertenece",
            "Documentos asociados",
        ],
        f_title,
        f_body,
    )
    card(
        d,
        doc,
        "DOCUMENT",
        YELLOW,
        [
            "Identificador",
            "Nombre de fichero",
            "Tipo MIME",
            "Base de conocimiento",
            "Chunks asociados",
        ],
        f_title,
        f_body,
    )
    card(
        d,
        chunk,
        "CHUNK",
        LILAC,
        [
            "Identificador",
            "Posición, titular, texto",
            "Documento al que pertenece",
            "Embedding (modelo + vector)",
        ],
        f_title,
        f_body,
    )

    cx = 1050  # centro TENANT
    fork_y = 310
    rail_y = 370

    # TENANT → bifurcación hacia KB y DOCUMENT
    d.line([(cx, fork_y), (cx, rail_y)], fill=EDGE, width=4)
    d.line([(380, rail_y), (1720, rail_y)], fill=EDGE, width=4)
    arrow(d, (380, rail_y), (380, 420))
    arrow(d, (1720, rail_y), (1720, 400))

    # DOCUMENT → KNOWLEDGE BASE (pertenece a)
    arrow(d, (1420, 580), (680, 580))

    # CHUNK → DOCUMENT (pertenece a)
    arrow(d, (1720, 860), (1720, 760))

    cap = "Figura: Entidades"
    cw = d.textlength(cap, font=f_cap)
    d.text(((W - cw) / 2, H - 48), cap, font=f_cap, fill=GRAY)

    img.save(OUT, "PNG", dpi=(180, 180))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
