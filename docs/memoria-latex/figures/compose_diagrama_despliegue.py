"""Diagrama de despliegue AgroPS con logos (estilo PolicyOps Fig. 4.2)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
LOGOS = ROOT / "logos"
OUT = ROOT / "diagrama-despliegue-agrops.png"

W, H = 2800, 1600
BG = (255, 255, 255)
NAVY = (26, 54, 93)
INK = (45, 55, 72)
GRAY = (113, 128, 150)
LINE = (180, 188, 200)
SOFT = (247, 250, 252)
ACCENT = (7, 104, 169)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fit_logo(path: Path, max_w: int, max_h: int):
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img


def paste(base: Image.Image, logo: Image.Image | None, cx: int, cy: int):
    if logo is None:
        return
    base.alpha_composite(logo, (int(cx - logo.width / 2), int(cy - logo.height / 2)))


def rounded(draw, xy, r=16, fill=SOFT, outline=LINE, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def arrow(draw, start, end, label: str | None = None, color=ACCENT):
    draw.line([start, end], fill=color, width=4)
    x, y = end
    dx, dy = end[0] - start[0], end[1] - start[1]
    if abs(dx) >= abs(dy):
        draw.polygon([(x, y), (x - 16, y - 9), (x - 16, y + 9)], fill=color)
        if label:
            draw.text(((start[0] + end[0]) // 2 - 40, y - 36), label, font=font(18, True), fill=color)
    else:
        draw.polygon([(x, y), (x - 9, y - 16), (x + 9, y - 16)], fill=color)
        if label:
            draw.text((x + 12, (start[1] + end[1]) // 2 - 10), label, font=font(18, True), fill=color)


def draw_person(draw, cx, cy):
    """Silueta simple de desarrollador."""
    draw.ellipse((cx - 28, cy - 70, cx + 28, cy - 14), fill=NAVY)
    draw.rounded_rectangle((cx - 42, cy - 8, cx + 42, cy + 70), radius=20, fill=NAVY)


def node_card(base, draw, xy, title: str, logo_path: Path | None, logo_size=90):
    x0, y0, x1, y1 = xy
    rounded(draw, xy, 18, SOFT, LINE, 2)
    cx = (x0 + x1) // 2
    if logo_path:
        logo = fit_logo(logo_path, logo_size, logo_size)
        paste(base, logo, cx, y0 + 70)
    draw.text((cx - len(title) * 7, y1 - 48), title, font=font(20, True), fill=NAVY)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(img)

    draw.text((70, 40), "Figura: Diagrama de despliegue — AgroPS", font=font(34, True), fill=NAVY)

    # ========== FILA SUPERIOR: CI ==========
    y_top = 160

    # Desarrollador
    draw_person(draw, 160, y_top + 90)
    draw.text((70, y_top + 190), "DESARROLLADOR", font=font(18, True), fill=NAVY)

    arrow(draw, (220, y_top + 80), (360, y_top + 80), "PUSH")

    # GitHub repo
    node_card(img, draw, (360, y_top, 620, y_top + 200), "REPOSITORIO GITHUB", LOGOS / "github.png", 100)
    # small git branch hint
    draw.text((390, y_top + 165), "main / master", font=font(15), fill=GRAY)

    arrow(draw, (620, y_top + 80), (760, y_top + 80), "ACTION TRIGGER")

    # GitHub Actions
    node_card(img, draw, (760, y_top, 1060, y_top + 200), "GITHUB ACTIONS", LOGOS / "githubactions.png", 100)
    draw.text((790, y_top + 165), "deploy-ionos.yml", font=font(15), fill=GRAY)

    arrow(draw, (1060, y_top + 80), (1200, y_top + 80), "WORKFLOW CREA IMÁGENES")

    # Imágenes creadas
    rounded(draw, (1200, y_top - 10, 1880, y_top + 210), 18, SOFT, ACCENT, 3)
    whale = fit_logo(LOGOS / "docker.png", 56, 56)
    paste(img, whale, 1240, y_top + 30)
    draw.text((1280, y_top + 12), "IMÁGENES CREADAS", font=font(20, True), fill=NAVY)

    for i, name in enumerate(
        [
            "samuelzo/agrops-api:latest",
            "samuelzo/agrops-frontend:latest",
        ]
    ):
        yy = y_top + 60 + i * 70
        rounded(draw, (1240, yy, 1840, yy + 58), 12, (255, 255, 255), LINE, 2)
        paste(img, fit_logo(LOGOS / "docker.png", 36, 36), 1270, yy + 29)
        draw.text((1300, yy + 16), name, font=font(18), fill=INK)

    # Flecha a Docker Hub
    arrow(draw, (1540, y_top + 210), (1540, 520), "SUBIDA A DOCKER HUB")

    # Docker Hub (nube)
    hub_box = (1280, 530, 1800, 760)
    rounded(draw, hub_box, 24, (239, 246, 255), ACCENT, 3)
    # nube simple
    hx, hy = 1540, 620
    draw.ellipse((hx - 120, hy - 40, hx - 20, hy + 40), fill=(200, 220, 240), outline=ACCENT, width=2)
    draw.ellipse((hx - 40, hy - 55, hx + 80, hy + 35), fill=(200, 220, 240), outline=ACCENT, width=2)
    draw.ellipse((hx + 40, hy - 35, hx + 130, hy + 40), fill=(200, 220, 240), outline=ACCENT, width=2)
    paste(img, fit_logo(LOGOS / "docker.png", 70, 70), hx, hy)
    draw.text((1400, 700), "DOCKER HUB", font=font(24, True), fill=NAVY)

    # ========== FILA INFERIOR: CD ==========
    y_bot = 900

    draw_person(draw, 160, y_bot + 40)
    draw.text((55, y_bot + 140), "DESARROLLADOR", font=font(18, True), fill=NAVY)
    draw.text((40, y_bot + 168), "/ OPERADOR VPS", font=font(16), fill=GRAY)

    arrow(draw, (220, y_bot + 40), (400, y_bot + 40), "docker compose up -d")

    # Docker Compose
    rounded(draw, (400, y_bot - 40, 780, y_bot + 180), 18, SOFT, LINE, 2)
    paste(img, fit_logo(LOGOS / "docker.png", 100, 100), 590, y_bot + 40)
    draw.text((470, y_bot + 120), "DOCKER COMPOSE", font=font(20, True), fill=NAVY)
    draw.text((455, y_bot + 148), "docker-compose.prod.yaml", font=font(15), fill=GRAY)

    # pull from hub
    arrow(draw, (1540, 760), (1540, 860), None)
    draw.line([(1540, 860), (780, y_bot + 40)], fill=ACCENT, width=4)
    draw.polygon([(780, y_bot + 40), (798, y_bot + 28), (798, y_bot + 52)], fill=ACCENT)
    draw.text((900, 820), "DESCARGA DE IMAGEN", font=font(18, True), fill=ACCENT)

    arrow(draw, (780, y_bot + 40), (960, y_bot + 40), "LEVANTA CONTENEDOR")

    # Contenedores
    rounded(draw, (960, y_bot - 60, 2140, y_bot + 220), 18, SOFT, NAVY, 3)
    draw.text((1000, y_bot - 40), "CONTENEDORES", font=font(22, True), fill=NAVY)

    containers = [
        (1080, "DATABASE", LOGOS / "postgresql.png", "pgvector"),
        (1380, "API", LOGOS / "fastapi-logo.png", "FastAPI"),
        (1680, "FRONTEND", LOGOS / "react.png", "React + Nginx"),
        (1980, "OLLAMA", LOGOS / "ollama.png", "LLM local"),
    ]
    for cx, title, logo_p, sub in containers:
        rounded(draw, (cx - 110, y_bot + 10, cx + 110, y_bot + 190), 14, (255, 255, 255), LINE, 2)
        paste(img, fit_logo(LOGOS / "docker.png", 28, 28), cx - 70, y_bot + 32)
        paste(img, fit_logo(logo_p, 72, 72), cx, y_bot + 90)
        draw.text((cx - 55, y_bot + 140), title, font=font(16, True), fill=NAVY)
        draw.text((cx - 50, y_bot + 162), sub, font=font(13), fill=GRAY)

    # Aplicación
    arrow(draw, (2140, y_bot + 80), (2320, y_bot + 80), None)
    rounded(draw, (2320, y_bot - 20, 2720, y_bot + 200), 18, (239, 246, 255), ACCENT, 3)
    # monitor
    mx, my = 2520, y_bot + 70
    draw.rounded_rectangle((mx - 90, my - 55, mx + 90, my + 45), radius=8, fill=NAVY)
    draw.rectangle((mx - 78, my - 42, mx + 78, my + 28), fill=(220, 235, 250))
    draw.rectangle((mx - 30, my + 45, mx + 30, my + 55), fill=NAVY)
    draw.rectangle((mx - 50, my + 55, mx + 50, my + 62), fill=GRAY)
    draw.text((2420, y_bot + 155), "APLICACIÓN", font=font(20, True), fill=NAVY)

    draw.text(
        (70, 1480),
        "Push → GitHub Actions → Docker Hub → Compose → contenedores (postgres, api, frontend, ollama).",
        font=font(18),
        fill=GRAY,
    )
    draw.text(
        (70, 1515),
        "Prototipo funcional contenedorizado — no certificación de producción industrial.",
        font=font(17),
        fill=GRAY,
    )

    img.convert("RGB").save(OUT, "PNG")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
