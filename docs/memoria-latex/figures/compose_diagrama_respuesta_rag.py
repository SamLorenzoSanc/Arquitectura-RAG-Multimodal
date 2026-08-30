"""Diagrama del pipeline de respuesta RAG (AnswerQuestion / hybrid)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrama-respuesta-rag.png"

W, H = 2680, 1520
BG = (255, 255, 255)
NAVY = (26, 54, 93)
ACCENT = (7, 104, 169)
INK = (45, 55, 72)
GRAY = (113, 128, 150)
LINE = (160, 174, 192)
SOFT = (247, 250, 252)
FILL_Q = (237, 242, 247)
FILL_RET = (235, 248, 255)
FILL_GEN = (240, 253, 244)
FILL_AGENT = (255, 247, 237)
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
    center_text(draw, cx, y0 + 34, title, f_title, NAVY)
    if subtitle and f_sub:
        center_text(draw, cx, y0 + 64, subtitle, f_sub, GRAY)
        start_y = y0 + 96
    else:
        start_y = y0 + 76
    multiline_center(draw, cx, start_y, lines, f_body, INK, gap=28)


def main():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f_title = font(40, True)
    f_h = font(22, True)
    f_body = font(18)
    f_small = font(16)
    f_cap = font(18, True)
    f_tiny = font(14)

    d.text((56, 32), "Pipeline de respuesta RAG — AgroPS", font=f_title, fill=NAVY)
    d.text(
        (56, 84),
        "Caso de uso AnswerQuestion (modo hybrid): retrieve híbrido → prompt con evidencia → Llama 3.2 vía Ollama",
        font=f_small,
        fill=GRAY,
    )

    # Fila principal answer
    rounded(d, (40, 130, W - 40, 520), 24, FILL_Q, LINE, 2)
    d.text((64, 146), "MODO HYBRID — AnswerQuestion.execute", font=f_cap, fill=NAVY)

    top = [
        (
            (70, 190, 480, 480),
            "1. Pregunta",
            "POST /api/v1/chat",
            [
                "q + historial H",
                "tenant / colecciones",
                "rag_mode = hybrid",
                "k_final ≈ 8",
            ],
            WHITE,
        ),
        (
            (530, 190, 1040, 480),
            "2. HybridRetrieve",
            "Alg. dens+BM25+RRF",
            [
                "Rewrite opcional (LLM)",
                "Expansión léxico agrario",
                "Dense + BM25 (q y q_exp)",
                "RRF k=60 → Top-k",
                "Rerank off por defecto",
            ],
            FILL_RET,
        ),
        (
            (1090, 190, 1600, 480),
            "3. Evidencia",
            "chunks C",
            [
                "Si C=∅ y abstención:",
                "plantilla out-of-knowledge",
                "(sin llamar al LLM)",
                "Si hay C: recorte chars",
                "y fuentes para citar",
            ],
            WHITE,
        ),
        (
            (1650, 190, 2600, 480),
            "4. Generación",
            "BuildPrompt + Ollama",
            [
                "Sistema + contexto + q",
                "Modelo: llama3.2",
                "Solo con evidencia",
                "Respuesta a + citas C",
                "Related questions (opc.)",
            ],
            FILL_GEN,
        ),
    ]
    for xy, title, sub, lines, fill in top:
        phase_box(d, xy, title, lines, fill, f_h, f_body, f_tiny, sub)

    arrow_h(d, 480, 335, 530)
    arrow_h(d, 1040, 335, 1090)
    arrow_h(d, 1600, 335, 1650)

    # Detalle retrieve
    rounded(d, (40, 550, W - 40, 980), 24, FILL_RET, LINE, 2)
    d.text((64, 566), "DETALLE HybridRetrieve (cuatro listas → RRF)", font=f_cap, fill=ACCENT)

    ret_boxes = [
        (
            (70, 620, 520, 920),
            "A. Consulta",
            [
                "q' = rewrite(q) si aplica",
                "q_exp = ExpandAgro(q')",
                "embed(q') en Ollama",
                "nomic-embed-text",
            ],
        ),
        (
            (560, 620, 1060, 920),
            "B. Vía densa",
            [
                "pgvector / coseno",
                "HNSW sobre embeddings",
                "DenseSearch(q')",
                "DenseSearch(q_exp)",
                "Filtro tenant / KB",
            ],
        ),
        (
            (1100, 620, 1600, 920),
            "C. Vía léxica",
            [
                "BM25 por tenant",
                "Índice pickle",
                "Bm25Search(q')",
                "Bm25Search(q_exp)",
                "Códigos / términos exactos",
            ],
        ),
        (
            (1640, 620, 2600, 920),
            "D. Fusión",
            [
                "U = RRF(D, B, D_exp, B_exp)",
                "Opcional Cross-Encoder",
                "C = TopK(U, k_final)",
                "Demo: RAG_USE_RERANKER=false",
                "Eval. congelada: híbrido fijo",
            ],
        ),
    ]
    for xy, title, lines in ret_boxes:
        x0, y0, x1, y1 = xy
        rounded(d, xy, 18, WHITE, LINE, 2)
        cx = (x0 + x1) // 2
        center_text(d, cx, y0 + 36, title, f_h, NAVY)
        multiline_center(d, cx, y0 + 80, lines, f_body, INK, gap=32)

    arrow_h(d, 520, 770, 560)
    arrow_h(d, 1060, 770, 1100)
    arrow_h(d, 1600, 770, 1640)

    # Rama agéntica
    rounded(d, (40, 1010, W - 40, 1320), 24, FILL_AGENT, LINE, 2)
    d.text(
        (64, 1026),
        "RAMA ALTERNATIVA — Agentic RAG (LangGraph) cuando rag_mode = agentic",
        font=f_cap,
        fill=(192, 86, 33),
    )

    agent = [
        ("Plan", ["ClassifyIntent(q)", "PlanTools (JSON/heurística)", "Vacío → respuesta directa"]),
        ("Retrieve", ["Tools: KB híbrida,", "SQL acotado, memoria…", "Misma HybridRetrieve"]),
        ("Grade", ["grade_documents", "sí → generar", "no → rewrite ≤1"]),
        ("Answer", ["SynthPrompt + LLM", "Abstención si falla", "Traza de tools en UI"]),
    ]
    aw = 580
    gap = 40
    x = 70
    for i, (title, lines) in enumerate(agent):
        xy = (x, 1080, x + aw, 1280)
        rounded(d, xy, 16, WHITE, LINE, 2)
        cx = x + aw // 2
        center_text(d, cx, 1110, f"{i+1}. {title}", f_h, NAVY)
        multiline_center(d, cx, 1150, lines, f_body, INK, gap=30)
        if i < len(agent) - 1:
            arrow_h(d, x + aw, 1180, x + aw + gap)
        x += aw + gap

    d.text(
        (56, 1350),
        "Nota: la evaluación cuantitativa del TFM (run_20260819T165515Z) mide el camino hybrid fijo, no el grafo agéntico.",
        font=f_small,
        fill=GRAY,
    )
    d.text(
        (56, 1388),
        "Sin RAG (baseline): se omite HybridRetrieve y el LLM responde solo con la pregunta + prompt de sistema vacío de contexto.",
        font=f_small,
        fill=GRAY,
    )

    rounded(d, (56, 1435, 200, 1485), 10, FILL_Q, LINE, 2)
    d.text((220, 1450), "Entrada", font=f_small, fill=INK)
    rounded(d, (360, 1435, 504, 1485), 10, FILL_RET, LINE, 2)
    d.text((524, 1450), "Recuperación", font=f_small, fill=INK)
    rounded(d, (720, 1435, 864, 1485), 10, FILL_GEN, LINE, 2)
    d.text((884, 1450), "Generación", font=f_small, fill=INK)
    rounded(d, (1060, 1435, 1204, 1485), 10, FILL_AGENT, LINE, 2)
    d.text((1224, 1450), "Modo agéntico", font=f_small, fill=INK)

    rgb = img.convert("RGB")
    rgb.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
