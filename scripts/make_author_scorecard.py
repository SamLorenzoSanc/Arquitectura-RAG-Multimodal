# -*- coding: utf-8 -*-
"""Genera la plantilla ciega de puntuación humana a partir de un results.csv.

No incluye columnas del juez. Samuel puntúa 1-5 de exactitud y luego se calcula
el acuerdo (±1 punto) con scripts/score_human_agreement.py.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "docs" / "evaluation_runs" / "human_sample_item_ids.json"


def main(results_csv: str) -> None:
    src = Path(results_csv)
    ids = set(json.loads(SAMPLE.read_text(encoding="utf-8"))["item_ids"])
    out = src.parent / "author_scorecard.csv"
    with src.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    fields = [
        "item_id",
        "category",
        "question",
        "reference_answer",
        "rag_answer",
        "vanilla_answer",
        "author_rag_accuracy",
        "author_vanilla_accuracy",
        "author_notes",
    ]
    selected = [r for r in rows if int(r["item_id"]) in ids]
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in selected:
            w.writerow({k: (r.get(k, "") if k not in {"author_rag_accuracy", "author_vanilla_accuracy", "author_notes"} else "") for k in fields})
    print(f"wrote {out} n={len(selected)} (sin columnas de juez)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: python scripts/make_author_scorecard.py docs/evaluation_runs/<run_id>/results.csv")
    main(sys.argv[1])
