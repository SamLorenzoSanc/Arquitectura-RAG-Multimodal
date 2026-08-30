"""Diagrama del algoritmo de búsqueda del asistente AgroPS (defensa TFM)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrama-busqueda-asistente-agrops.png"
PRESENT = ROOT.parent.parent / "presentacion_defensa" / OUT.name

W, H = 2800, 1750
BG = (255, 255, 255)
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
FILL_E = (254, 243, 242)
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
    rounded(draw, xy, 20, fill, LINE, 3)
    bx0, by0, bx1, by1 = x0 + 16, y0 + 16, x0 + 58, y0 + 58
    rounded(draw, (bx0, by0, bx1, by1), 12, ACCENT, ACCENT, 1)
    center_text(draw, (bx0 + bx1) // 2, (by0 + by1) // 2, str(num), f_num, WHITE)
    draw.text((x0 + 72, y0 + 24), title, font=f_title, fill=NAVY)
    multiline(draw, x0 + 22, y0 + 72, lines, f_body, INK, gap=27)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = font(40, True)
    f_sub = font(19)
    f_h = font(22, True)
    f_body = font(18)
    f_num = font(20, True)
    f_small = font(15)
    f_cap = font(17, True)

    d.text((50, 28), "Algoritmo de búsqueda del asistente AgroPS", font=f_title, fill=NAVY)
    d.text(
        (50, 82),
        "Orquestación agéntica + recuperación híbrida (denso + BM25 + RRF) · demo: hybrid_rrf · sin reranker",
        font=f_sub,
        fill=GRAY,
    )

    # Ejemplo banda
    rounded(d, (50, 125, 2750, 195), 14, FILL_C, LINE, 2)
    d.text(
        (70, 148),
        "Ejemplo: «Las hojas se están poniendo amarillas: ¿qué puede ser?»  →  intent=diagnostic  →  tool diagnose_crop  →  hybrid_rrf",
        font=f_body,
        fill=INK,
    )

    # Fila 1
    y1 = 230
    h1 = 250
    step_box(
        d,
        (50, y1, 680, y1 + h1),
        1,
        "Pregunta del usuario",
        [
            "• Chat autenticado (tenant)",
            "• Historial corto (2–6 msgs)",
            "• Modo Agent (agéntico)",
        ],
        FILL_A,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (740, y1, 1430, y1 + h1),
        2,
        "Orquestación (Alg. 3)",
        [
            "• Clasifica intención",
            "• Elige herramienta(s)",
            "• p.ej. diagnose_crop",
            "• Camino rápido: 1 retrieve",
        ],
        FILL_B,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (1490, y1, 2180, y1 + h1),
        3,
        "Búsqueda densa",
        [
            "• Embedding pregunta",
            "• nomic-embed-text",
            "• pgvector (coseno)",
            "• Top-k vecinos semánticos",
        ],
        FILL_D,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (2240, y1, 2750, y1 + h1),
        4,
        "Búsqueda BM25",
        [
            "• Índice léxico tenant",
            "• Tokens / palabras exactas",
            "• Top-k coincidencias",
            "• En paralelo con denso",
        ],
        FILL_C,
        f_num,
        f_h,
        f_body,
    )
    mid1 = y1 + h1 // 2
    arrow_h(d, 680, mid1, 740)
    arrow_h(d, 1430, mid1, 1490)
    # fork visual: from 2 down to note that 3 and 4 are parallel
    d.text((1520, y1 - 28), "en paralelo ↓", font=f_small, fill=ACCENT)

    # Arrow from step 2 down to fusion area
    arrow_v(d, 1085, y1 + h1, y1 + h1 + 55)

    # Fila 2 - RRF
    y2 = y1 + h1 + 65
    h2 = 230
    step_box(
        d,
        (50, y2, 1380, y2 + h2),
        5,
        "Fusión RRF (Alg. 2)",
        [
            "• Junta rankings denso + BM25",
            "• score = 1 / (60 + posición)",
            "• Gana quien aparece alto en ambas listas",
            "• Ejemplo: 01_rol_del_asesor.md (dense+bm25)",
        ],
        FILL_B,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (1440, y2, 2750, y2 + h2),
        6,
        "Top-k de evidencia",
        [
            "• Se quedan los mejores fragmentos (final_k)",
            "• Reranker BGE: desactivado en la demo",
            "• Si no hay evidencia útil → abstención",
            "• (no se llama al LLM / plantilla out-of-knowledge)",
        ],
        FILL_E,
        f_num,
        f_h,
        f_body,
    )
    arrow_h(d, 1380, y2 + h2 // 2, 1440, GREEN)
    # connect 3 and 4 into 5
    arrow_v(d, 1835, y1 + h1, y2)
    arrow_v(d, 2495, y1 + h1, y2)
    arrow_h(d, 1835, y2 - 20, 700, ACCENT)

    arrow_v(d, W // 2, y2 + h2, y2 + h2 + 55)

    # Fila 3 - generate
    y3 = y2 + h2 + 65
    h3 = 260
    step_box(
        d,
        (50, y3, 1380, y3 + h3),
        7,
        "Generación anclada",
        [
            "• Prompt = sistema + fragmentos + pregunta",
            "• Llama 3.2 local (Ollama)",
            "• Instrucción: no inventar dosis / cifras",
            "• Respuesta en español con fuentes",
        ],
        FILL_D,
        f_num,
        f_h,
        f_body,
    )
    step_box(
        d,
        (1440, y3, 2750, y3 + h3),
        8,
        "Respuesta API / UI",
        [
            "• answer + context + retrieval",
            "• architecture: agentic_langgraph_rag",
            "• strategy: hybrid_rrf",
            "• Conversación persistida (memoria largo plazo)",
        ],
        FILL_A,
        f_num,
        f_h,
        f_body,
    )
    arrow_h(d, 1380, y3 + h3 // 2, 1440, GREEN)

    # Pie
    rounded(d, (50, H - 120, 2750, H - 40), 14, SOFT, LINE, 2)
    d.text(
        (70, H - 95),
        "Código: HybridRetrieve + rrf_fusion (rag/) · orquestación: AgenticRAGService · Chat demo: RAG_AGENT_FAST + hybrid_rrf",
        font=f_small,
        fill=GRAY,
    )
    d.text(
        (70, H - 68),
        "Idea clave: el LLM razona; el corpus aporta los hechos. Denso entiende paráfrasis; BM25 clava términos; RRF los combina.",
        font=f_cap,
        fill=NAVY,
    )

    img.save(OUT, "PNG", optimize=True)
    PRESENT.parent.mkdir(parents=True, exist_ok=True)
    PRESENT.write_bytes(OUT.read_bytes())
    print(f"Wrote {OUT}")
    print(f"Copied {PRESENT}")


if __name__ == "__main__":
    main()
