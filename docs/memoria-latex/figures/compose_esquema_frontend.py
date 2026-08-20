"""Esquema del front-end: dominio, aplicación, puertos y adaptadores (estilo Fig. 3.5)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
LOGOS = ROOT / "logos"
OUT = ROOT / "esquema-frontend-agrops.png"

W, H = 2480, 1280
BG = (255, 255, 255)
NAVY = (26, 54, 93)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
FILL_OUT = (247, 250, 252)
FILL_APP = (237, 242, 247)
FILL_DOM = (226, 232, 240)
WHITE = (255, 255, 255)
INK = (45, 55, 72)
TS_BLUE = (49, 120, 198)


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


def draw_fetch_icon(draw, cx, cy, size=72):
    half = size // 2
    box = (cx - half, cy - half - 8, cx + half, cy + half - 8)
    rounded(draw, box, 10, (248, 250, 252), LINE, 2)
    f = font(22, True)
    draw.text((cx - 36, cy - 28), "{ }", font=f, fill=NAVY)
    draw.text((cx - 30, cy + 2), "FETCH", font=font(16, True), fill=GRAY)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f_title = font(42, True)
    f_h1 = font(28, True)
    f_h2 = font(22, True)
    f_body = font(20)
    f_small = font(17)
    f_cap = font(22)

    ts = fit_logo(LOGOS / "typescript.png", 64, 64)
    if ts:
        img.alpha_composite(ts, (118, 38))
    d.text((48, 48), "FRONT-END", font=f_title, fill=NAVY)

    # --- Anillo adaptadores ---
    outer = (36, 118, W - 36, H - 72)
    rounded(d, outer, 26, FILL_OUT, LINE, 3)
    d.text((68, 136), "ADAPTADORES", font=f_h1, fill=NAVY)

    # --- Capa aplicación (izquierda/centro) ---
    app_box = (72, 198, 1620, 860)
    rounded(d, app_box, 22, FILL_APP, LINE, 3)
    d.text((104, 216), "APLICACIÓN", font=f_h1, fill=NAVY)

    # --- Dominio ---
    dom_box = (760, 280, 1280, 760)
    rounded(d, dom_box, 18, FILL_DOM, NAVY, 3)
    d.text((820, 308), "DOMINIO", font=f_h1, fill=NAVY)
    y = 368
    for head, lines in [
        ("Entidades", ["DocumentItem · Message", "Conversation"]),
        ("Objetos valor", ["ChatRequest · ChatResponse", "ContextChunk · RetrievalInfo"]),
        ("Enumerados", ["rag_mode · MessageRole", "processing_status"]),
    ]:
        d.text((800, y), head, font=f_h2, fill=NAVY)
        y += 38
        for line in lines:
            d.text((800, y), line, font=f_body, fill=INK)
            y += 34
        y += 14

    # --- Casos de uso (izquierda) ---
    d.text((110, 290), "CASOS DE USO", font=f_h2, fill=NAVY)
    for i, name in enumerate(
        ["LoginUser · RegisterUser", "ListDocuments · UploadDocument", "AskQuestion (Chat)", "RunEvaluation · HITL"]
    ):
        d.text((110, 340 + i * 42), name, font=f_body, fill=INK)

    d.text((110, 540), "PUERTOS DE ENTRADA", font=f_h2, fill=NAVY)
    for i, name in enumerate(
        ["pages · hooks (React)", "DocumentsPage · ChatPage", "ShellContext · useOrganization"]
    ):
        d.text((110, 590 + i * 42), name, font=f_body, fill=INK)

    d.text((1320, 290), "PUERTOS DE SALIDA", font=f_h2, fill=NAVY)
    for i, name in enumerate(
        ["AuthService · DocumentService", "ChatService · EvaluationService", "api.ts (HttpClient + JWT)"]
    ):
        d.text((1320, 340 + i * 42), name, font=f_body, fill=INK)

    d.text(
        (104, 800),
        "La UI invoca casos de uso vía servicios; los servicios dependen del puerto HTTP, no de fetch ni axios directamente en las páginas.",
        font=f_small,
        fill=GRAY,
    )

    # --- Adaptadores (columna derecha, estilo Fig. 3.5) ---
    http_box = (1680, 230, 2400, 520)
    rounded(d, http_box, 18, WHITE, LINE, 3)
    draw_fetch_icon(d, 2040, 310)
    tw = d.textlength("Adaptador HTTP", font=f_h2)
    d.text((1680 + (720 - tw) / 2, 370), "Adaptador HTTP", font=f_h2, fill=NAVY)
    sw = d.textlength("axios · /api/v1 · Bearer JWT", font=f_small)
    d.text((1680 + (720 - sw) / 2, 410), "axios · /api/v1 · Bearer JWT", font=f_small, fill=GRAY)

    react_box = (1680, 560, 2400, 1140)
    rounded(d, react_box, 18, WHITE, LINE, 3)
    tw = d.textlength("Adaptador React", font=f_h2)
    d.text((1680 + (720 - tw) / 2, 590), "Adaptador React", font=f_h2, fill=NAVY)

    logos = [
        (fit_logo(LOGOS / "react.png", 72, 72), 1760),
        (fit_logo(LOGOS / "vite.png", 72, 72), 1920),
        (fit_logo(LOGOS / "typescript.png", 64, 64), 2080),
        (fit_logo(LOGOS / "tailwind.png", 72, 72), 2240),
    ]
    for logo, x in logos:
        paste_center(img, logo, x, 700)

    d.text((1710, 780), "React Router · TanStack Query · componentes UI", font=f_small, fill=GRAY)

    # Flechas puerto → adaptadores
    d.line([(1620, 400), (1680, 400)], fill=LINE, width=4)
    d.polygon([(1680, 400), (1664, 392), (1664, 408)], fill=LINE)
    d.text((1638, 368), "Puerto", font=font(15, True), fill=GRAY)

    d.line([(1620, 780), (1680, 780)], fill=LINE, width=4)
    d.polygon([(1680, 780), (1664, 772), (1664, 788)], fill=LINE)

    cap = "Figura: Diagrama Front-end"
    cw = d.textlength(cap, font=f_cap)
    d.text(((W - cw) / 2, H - 48), cap, font=f_cap, fill=GRAY)

    rgb = Image.new("RGB", img.size, BG)
    rgb.paste(img, mask=img.split()[-1])
    rgb.save(OUT, "PNG", dpi=(180, 180))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
