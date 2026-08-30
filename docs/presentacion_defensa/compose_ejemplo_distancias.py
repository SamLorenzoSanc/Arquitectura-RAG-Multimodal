"""Figura 2D: A(1,2) pregunta vs B(4,6) chunk — L2, L1 y ángulo coseno."""

from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "ejemplo-distancias-ab.png"

INK = "#1A2E1A"
ACCENT = "#2F6B3A"
ACCENT2 = "#C47A2A"
MUTED = "#4A5C4A"
GRID = "#D7E0D4"


def main() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 5.4), dpi=180)
    fig.patch.set_facecolor("#F7F5F0")
    ax.set_facecolor("#F7F5F0")

    ax.set_xlim(-0.4, 7.2)
    ax.set_ylim(-0.4, 7.2)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, 8))
    ax.set_yticks(range(0, 8))
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.axhline(0, color="#8AA08A", linewidth=0.8)
    ax.axvline(0, color="#8AA08A", linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#C5D1C3")

    ax.annotate(
        "",
        xy=(4, 6),
        xytext=(1, 2),
        arrowprops=dict(arrowstyle="-", color=ACCENT, lw=2.4, linestyle="solid"),
    )
    ax.plot([1, 4, 4], [2, 2, 6], color=ACCENT2, lw=2.0, linestyle="--", solid_capstyle="round")

    ax.annotate(
        "",
        xy=(1, 2),
        xytext=(0, 0),
        arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.6, mutation_scale=12),
    )
    ax.annotate(
        "",
        xy=(4, 6),
        xytext=(0, 0),
        arrowprops=dict(arrowstyle="-|>", color=ACCENT2, lw=1.6, mutation_scale=12),
    )

    ax.scatter([1], [2], s=90, c=ACCENT, zorder=5, edgecolors="white", linewidths=1.2)
    ax.scatter([4], [6], s=90, c=ACCENT2, zorder=5, edgecolors="white", linewidths=1.2)

    ax.text(1.15, 1.25, "A  pregunta\n(1, 2)", color=ACCENT, fontsize=10, fontweight="bold")
    ax.text(4.2, 6.15, "B  chunk\n(4, 6)", color=ACCENT2, fontsize=10, fontweight="bold")
    ax.text(2.05, 4.35, "L2 = 5", color=ACCENT, fontsize=10, fontweight="bold", rotation=53)
    ax.text(2.15, 1.55, "L1 = 7", color=ACCENT2, fontsize=10, fontweight="bold")
    ax.text(0.35, 0.55, "ángulo\n(coseno)", color=MUTED, fontsize=8)

    ax.set_xlabel("dimensión 1", color=MUTED, fontsize=9)
    ax.set_ylabel("dimensión 2", color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_title("En RAG: A = embedding de la pregunta, B = embedding del chunk", color=INK, fontsize=10, pad=8)

    fig.tight_layout()
    fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print("OK", OUT)


if __name__ == "__main__":
    main()
