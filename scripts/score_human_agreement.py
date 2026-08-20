# -*- coding: utf-8 -*-
"""Acuerdo autor–juez (±1 punto). No calcula kappa (hace falta segundo anotador)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def agree(a: float, b: float) -> bool:
    return abs(a - b) <= 1.0


def main(scorecard: str, results: str) -> None:
    sc_rows = {int(r["item_id"]): r for r in csv.DictReader(Path(scorecard).open(encoding="utf-8-sig"))}
    res_rows = {int(r["item_id"]): r for r in csv.DictReader(Path(results).open(encoding="utf-8"))}
    pairs_rag = []
    pairs_van = []
    missing = []
    for iid, sc in sc_rows.items():
        res = res_rows.get(iid)
        if not res:
            missing.append(iid)
            continue
        ar = (sc.get("author_rag_accuracy") or "").strip()
        av = (sc.get("author_vanilla_accuracy") or "").strip()
        if ar:
            pairs_rag.append((float(ar), float(res["rag_accuracy"])))
        if av:
            pairs_van.append((float(av), float(res["vanilla_accuracy"])))
    out = {
        "n_scorecard": len(sc_rows),
        "missing_in_results": missing,
        "rag": {
            "n": len(pairs_rag),
            "pct_agree_pm1": (sum(agree(a, b) for a, b in pairs_rag) / len(pairs_rag)) if pairs_rag else None,
        },
        "vanilla": {
            "n": len(pairs_van),
            "pct_agree_pm1": (sum(agree(a, b) for a, b in pairs_van) / len(pairs_van)) if pairs_van else None,
        },
        "kappa": "not_computed_single_annotator",
        "statement_es": "Acuerdo autor–juez, N=%s, no hay segundo anotador." % (len(pairs_rag) or "—"),
    }
    dest = Path(scorecard).with_name("human_agreement.json")
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "uso: python scripts/score_human_agreement.py "
            "docs/evaluation_runs/<run_id>/author_scorecard.csv "
            "docs/evaluation_runs/<run_id>/results.csv"
        )
    main(sys.argv[1], sys.argv[2])
