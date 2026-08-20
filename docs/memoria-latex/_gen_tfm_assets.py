"""Genera gráfica de métricas y capturas de interfaz para la memoria."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
FIG = ROOT / "figures"
SRC = FIG / "from-pdf"
FIG.mkdir(exist_ok=True)

RENAMES = {
    "p13_img2_904x356.png": "rag-pipeline-simple.png",
    "p18_img2_597x353.png": "lost-in-the-middle.png",
    "p22_img2_568x439.png": "hiperplano-decision.png",
    "p23_img2_580x447.png": "desvanecimiento-gradiente.png",
    "p24_img2_584x776.png": "evolucion-llm.png",
    "p25_img2_259x360.png": "transformer-vaswani.png",
    "p26_img2_575x453.png": "matriz-atencion.png",
}


def copy_pdf_figures() -> None:
    for src_name, dest_name in RENAMES.items():
        src = SRC / src_name
        if src.exists():
            Image.open(src).convert("RGB").save(FIG / dest_name, "PNG")


def metrics_chart() -> None:
    cats = [
        "direct_fact",
        "temporal",
        "relationship",
        "numerical",
        "comparative",
        "holistic",
        "spanning",
    ]
    mrr = [0.887, 0.842, 0.941, 0.801, 0.724, 0.518, 0.470]
    acc = [4.52, 4.41, 4.62, 4.18, 4.05, 2.80, 2.95]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4), dpi=160)
    colors = ["#1D4ED8"] * 5 + ["#B45309", "#B91C1C"]
    axes[0].bar(cats, mrr, color=colors)
    axes[0].axhline(0.7911, color="#0F172A", linestyle="--", linewidth=1, label="MRR global 0,7911")
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("MRR")
    axes[0].set_title("Recuperación por categoría")
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].legend(fontsize=8)
    axes[1].bar(cats, acc, color=colors)
    axes[1].axhline(4.21, color="#0F172A", linestyle="--", linewidth=1, label="Exactitud media 4,21")
    axes[1].set_ylim(0, 5)
    axes[1].set_ylabel("Exactitud (juez 1–5)")
    axes[1].set_title("Calidad de generación por categoría")
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "metricas-rag.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _font(size: int, bold: bool = False):
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _chrome(title: str, nav: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (1280, 720), "#F8FAFC")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1280, 64), fill="#FFFFFF")
    d.line((0, 64, 1280, 64), fill="#E2E8F0")
    d.rounded_rectangle((18, 16, 58, 52), 8, fill="#15539C")
    d.text((70, 18), "AGROPS", font=_font(22, True), fill="#0F172A")
    d.text((1180, 22), "S. Lorenzo", font=_font(14), fill="#475569")
    d.rectangle((0, 64, 232, 720), fill="#0F172A")
    for i, item in enumerate(
        ["Inicio", "Chat", "Documentos", "Datasets", "Evaluación", "Organización", "Grafo"]
    ):
        y = 92 + i * 44
        active = item == nav
        if active:
            d.rounded_rectangle((12, y - 8, 220, y + 28), 8, fill="#1E3A8A")
        d.text((28, y), item, font=_font(15, active), fill="#F8FAFC")
    d.text((252, 80), title, font=_font(22, True), fill="#0F172A")
    return img, d


def ui_docs() -> None:
    img, d = _chrome("Gestión documental", "Documentos")
    d.rounded_rectangle((252, 128, 1248, 680), 12, fill="#FFFFFF", outline="#E2E8F0")
    headers = ["Documento", "Base de conocimiento", "Estado", "Chunks"]
    for i, h in enumerate(headers):
        d.text((272 + i * 240, 148), h, font=_font(13, True), fill="#64748B")
    rows = [
        ("BOE PAC 2023-2027.pdf", "Normativa PAC", "Indexado", "142"),
        ("POSEI Canarias 2025.pdf", "Ayudas POSEI", "Indexado", "88"),
        ("BCAM 8 superficies.pdf", "Condicionalidad", "Indexado", "36"),
        ("Jóvenes agricultores.pdf", "Normativa PAC", "Pendiente", "0"),
    ]
    for r, row in enumerate(rows):
        y = 196 + r * 52
        d.line((272, y - 10, 1228, y - 10), fill="#F1F5F9")
        for c, val in enumerate(row):
            d.text((272 + c * 240, y), val, font=_font(14), fill="#0F172A")
    img.save(FIG / "ui-documentos.png")


def ui_org() -> None:
    img, d = _chrome("Organización y departamentos", "Organización")
    for i, (name, members) in enumerate(
        [("Cooperativa Valle Guerra", "12 miembros"), ("Departamento Técnico PAC", "5 miembros"), ("Inspección POSEI", "4 miembros")]
    ):
        x = 252 + i * 330
        d.rounded_rectangle((x, 140, x + 310, 320), 14, fill="#FFFFFF", outline="#E2E8F0")
        d.rounded_rectangle((x + 18, 160, x + 58, 200), 8, fill="#DBEAFE")
        d.text((x + 72, 168), name, font=_font(15, True), fill="#0F172A")
        d.text((x + 72, 198), members, font=_font(13), fill="#64748B")
        d.text((x + 24, 240), "Bases: PAC, POSEI, BCAM", font=_font(13), fill="#1D4ED8")
    d.rounded_rectangle((252, 360, 1248, 680), 12, fill="#FFFFFF", outline="#E2E8F0")
    d.text((272, 380), "Roles: administrador, técnico, inspector", font=_font(16, True), fill="#0F172A")
    d.text((272, 420), "Aislamiento multi-tenant por organización y knowledge base.", font=_font(14), fill="#334155")
    img.save(FIG / "ui-organizacion.png")


def ui_chat() -> None:
    img, d = _chrome("Asistente RAG", "Chat")
    d.rounded_rectangle((252, 128, 900, 680), 12, fill="#FFFFFF", outline="#E2E8F0")
    d.rounded_rectangle((272, 160, 620, 230), 10, fill="#EFF6FF")
    d.text((288, 172), "¿Cuál es la ayuda POSEI por hectárea de aguacate?", font=_font(14), fill="#1E3A8A")
    d.rounded_rectangle((400, 250, 880, 430), 10, fill="#F8FAFC", outline="#E2E8F0")
    d.text((416, 266), "Según el documento POSEI Canarias 2025, la ayuda", font=_font(14), fill="#0F172A")
    d.text((416, 292), "compensatoria para aguacate es de 1.200 €/ha en", font=_font(14), fill="#0F172A")
    d.text((416, 318), "explotaciones admisibles de Canarias, sujeta a", font=_font(14), fill="#0F172A")
    d.text((416, 344), "condicionalidad y recinto declarado.", font=_font(14), fill="#0F172A")
    d.text((416, 384), "Fuente: POSEI Canarias 2025, p. 14", font=_font(12, True), fill="#1D4ED8")
    d.rounded_rectangle((920, 128, 1248, 680), 12, fill="#FFFFFF", outline="#E2E8F0")
    d.text((940, 150), "Evidencia recuperada", font=_font(15, True), fill="#0F172A")
    d.text((940, 190), "1. POSEI · pág. 14 · 0,82", font=_font(13), fill="#334155")
    d.text((940, 220), "2. PAC 2023-27 · pág. 41 · 0,61", font=_font(13), fill="#334155")
    d.text((940, 250), "Modo: híbrido (RRF)", font=_font(13, True), fill="#15539C")
    img.save(FIG / "ui-chat.png")


def ui_ingest() -> None:
    img, d = _chrome("Ingesta y datasets RAG", "Datasets")
    d.rounded_rectangle((252, 128, 1248, 680), 12, fill="#FFFFFF", outline="#E2E8F0")
    steps = ["1. Archivo", "2. Schema mapping", "3. Preview", "4. Importar"]
    for i, step in enumerate(steps):
        x = 292 + i * 230
        d.rounded_rectangle((x, 170, x + 200, 220), 20, fill="#DBEAFE")
        d.text((x + 18, 184), step, font=_font(14, True), fill="#1E3A8A")
    d.text((292, 260), "prompt ← pregunta   context ← fragmento   expected_response ← ground_truth", font=_font(14), fill="#0F172A")
    d.rounded_rectangle((292, 320, 1208, 620), 10, fill="#F8FAFC", outline="#E2E8F0")
    d.text((312, 340), "Preview CSV (21 filas, 7 categorías PAC/POSEI)", font=_font(15, True), fill="#0F172A")
    d.text((312, 390), "direct_fact · temporal · relationship · spanning", font=_font(14), fill="#334155")
    d.text((312, 430), "regulatory_compliance · regulatory_fact · traceability", font=_font(14), fill="#334155")
    img.save(FIG / "ui-ingesta.png")


def ui_graph() -> None:
    img, d = _chrome("Grafo de conocimiento", "Grafo")
    d.rounded_rectangle((252, 128, 1248, 680), 12, fill="#0B1220")
    nodes = [
        (520, 260, "PAC 2021/2115"),
        (860, 240, "POSEI"),
        (700, 420, "BCAM 8"),
        (980, 430, "Jóvenes agr."),
        (430, 470, "Aguacate"),
    ]
    for (x1, y1, _), (x2, y2, _) in zip(nodes, nodes[1:]):
        d.line((x1 + 70, y1 + 24, x2 + 70, y2 + 24), fill="#38BDF8", width=2)
    for x, y, label in nodes:
        d.ellipse((x, y, x + 140, y + 56), fill="#1E3A8A", outline="#93C5FD")
        d.text((x + 16, y + 16), label, font=_font(13, True), fill="#F8FAFC")
    d.text((280, 160), "Entidades normativas y relaciones extraídas del corpus", font=_font(15, True), fill="#E2E8F0")
    img.save(FIG / "ui-grafo.png")


if __name__ == "__main__":
    copy_pdf_figures()
    metrics_chart()
    ui_docs()
    ui_org()
    ui_chat()
    ui_ingest()
    ui_graph()
    print("assets ok")
