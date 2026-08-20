# -*- coding: utf-8 -*-
"""Corrida congelada: LLM sin RAG vs RAG híbrido local sobre knowledge-base.

Escribe docs/evaluation_runs/<run_id>/{config.json,results.csv,summary.json,failures.json}.
No inventa métricas si Ollama no responde.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge-base"
GOLD = KB / "gold_tests.jsonl"
OUT_ROOT = ROOT / "docs" / "evaluation_runs"

OLLAMA = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434").rstrip("/")
GEN_MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2:latest")
EMB_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1400"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
DENSE_K = 10
BM25_K = 10
FINAL_K = int(os.getenv("RAG_FINAL_K", "8"))
RRF_K = 60
USE_RERANKER = os.getenv("RAG_USE_RERANKER", "false").lower() in {"1", "true", "yes"}
TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0"))


def http_json(url: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), 16):
        batch = texts[i : i + 16]
        try:
            data = http_json(
                f"{OLLAMA}/api/embed",
                {"model": EMB_MODEL, "input": batch},
                timeout=120,
            )
            embs = data.get("embeddings") or []
        except Exception:
            embs = []
            for text in batch:
                data = http_json(
                    f"{OLLAMA}/api/embeddings",
                    {"model": EMB_MODEL, "prompt": text},
                    timeout=120,
                )
                embs.append(data["embedding"])
        out.extend(embs)
    return out


def ollama_chat(messages: list[dict], fmt: dict | None = None, timeout: int = 180) -> str:
    payload: dict = {
        "model": GEN_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    if fmt:
        payload["format"] = fmt
    data = http_json(f"{OLLAMA}/api/chat", payload, timeout=timeout)
    return (data.get("message") or {}).get("content") or ""


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü0-9]+", (text or "").casefold())


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += max(1, size - overlap)
    return chunks


def load_gold() -> list[dict]:
    rows = []
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_kb_chunks() -> list[dict]:
    """Solo asesor-canarias: el oro de la memoria está anclado a POSEI/GIP/vademécum de cultivo."""
    chunks = []
    corpus = KB / "asesor-canarias"
    for path in sorted(corpus.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_text(encoding="utf-8", errors="replace")
        for idx, piece in enumerate(chunk_text(raw, CHUNK_SIZE, CHUNK_OVERLAP)):
            chunks.append({"id": f"{rel}#{idx}", "source": rel, "text": piece})
    return chunks


def bm25_rank(query: str, chunks: list[dict], k: int) -> list[int]:
    q_terms = tokenize(query)
    if not q_terms:
        return []
    docs = [tokenize(c["text"]) for c in chunks]
    N = len(docs) or 1
    avgdl = sum(len(d) for d in docs) / N
    df: dict[str, int] = defaultdict(int)
    for d in docs:
        for t in set(d):
            df[t] += 1
    scores = []
    k1, b = 1.5, 0.75
    for i, d in enumerate(docs):
        tf = Counter(d)
        dl = len(d) or 1
        s = 0.0
        for t in q_terms:
            if tf[t] == 0:
                continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        scores.append((s, i))
    scores.sort(reverse=True)
    return [i for s, i in scores[:k] if s > 0]


def rrf(rank_lists: list[list[int]], k: int = 60) -> list[int]:
    scores: dict[int, float] = defaultdict(float)
    for ranks in rank_lists:
        for rank, idx in enumerate(ranks, start=1):
            scores[idx] += 1.0 / (k + rank)
    return [idx for idx, _ in sorted(scores.items(), key=lambda x: -x[1])]


def ir_metrics(keywords: list[str], texts: list[str], k: int = 10) -> dict:
    needles = [t.casefold() for t in keywords if t.strip()]
    ranked = texts[:k]
    if not needles:
        return {"mrr": 0.0, "ndcg": 0.0, "coverage": 0.0}

    def hit_rank(needle: str) -> int | None:
        for i, blob in enumerate(ranked, start=1):
            if needle in blob.casefold():
                return i
        return None

    rr = []
    dcg = []
    idcg = []
    found = 0
    for needle in needles:
        r = hit_rank(needle)
        if r:
            found += 1
            rr.append(1.0 / r)
            dcg.append(1.0 / math.log2(r + 1))
        else:
            rr.append(0.0)
            dcg.append(0.0)
        idcg.append(1.0 / math.log2(min(found or 1, k) + 1))
    ndcg = (sum(dcg) / sum(idcg)) if sum(idcg) else 0.0
    return {
        "mrr": sum(rr) / len(rr),
        "ndcg": ndcg,
        "coverage": found / len(needles),
    }


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {"type": "string"},
        "accuracy": {"type": "number"},
        "completeness": {"type": "number"},
        "relevance": {"type": "number"},
        "faithfulness": {"type": "number"},
        "is_hallucination": {"type": "boolean"},
    },
    "required": [
        "feedback",
        "accuracy",
        "completeness",
        "relevance",
        "faithfulness",
        "is_hallucination",
    ],
}


def judge(question: str, generated: str, reference: str, context: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": "Eres un evaluador. Responde solo JSON. Escala 1-5. is_hallucination=true si hay hechos no soportados por el contexto (si no hay contexto, si contradicen la referencia o inventan cifras).",
        },
        {
            "role": "user",
            "content": (
                f"Pregunta: {question}\n\nReferencia: {reference}\n\n"
                f"Respuesta: {generated}\n\nContexto:\n{context or 'SIN CONTEXTO'}"
            ),
        },
    ]
    raw = ollama_chat(messages, fmt=JUDGE_SCHEMA)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "feedback": raw[:500],
            "accuracy": 1,
            "completeness": 1,
            "relevance": 1,
            "faithfulness": 1,
            "is_hallucination": True,
        }
    for key in ("accuracy", "completeness", "relevance", "faithfulness"):
        data[key] = max(1.0, min(5.0, float(data.get(key, 1))))
    data["is_hallucination"] = bool(data.get("is_hallucination"))
    return data


def generate(question: str, context: str | None) -> str:
    if context:
        system = (
            "Eres un asistente documental. Responde solo con el contexto. "
            "Si no está, di que no consta. No inventes cifras ni artículos."
        )
        user = f"Contexto:\n{context}\n\nPregunta: {question}"
    else:
        system = (
            "Eres un asistente sobre agricultura canaria y AgroLLM. "
            "Si no sabes la respuesta con certeza, dilo. No inventes cifras."
        )
        user = question
    return ollama_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )


def snapshot_ollama() -> dict:
    try:
        req = urllib.request.Request(f"{OLLAMA}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        models = [
            {"name": m.get("name"), "digest": m.get("digest"), "size": m.get("size")}
            for m in tags.get("models") or []
        ]
        return {"ok": True, "models": models}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    out = OUT_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    gold = load_gold()
    ollama_info = snapshot_ollama()
    config = {
        "run_id": run_id,
        "retriever": "local_hybrid_asesor_canarias",
        "note": "Misma receta que el chat (denso+BM25+RRF, reranker off) sobre knowledge-base/asesor-canarias. No es Graph RAG ni visión. RAGAS no se ejecuta en esta corrida.",
        "ragas": "not_run",
        "generation_model": GEN_MODEL,
        "embedding_model": EMB_MODEL,
        "chunk_size_chars": CHUNK_SIZE,
        "chunk_overlap_chars": CHUNK_OVERLAP,
        "dense_k": DENSE_K,
        "bm25_k": BM25_K,
        "rrf_k": RRF_K,
        "final_k": FINAL_K,
        "reranker": USE_RERANKER,
        "temperature": TEMPERATURE,
        "n_gold": len(gold),
        "ollama": ollama_info,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not ollama_info.get("ok"):
        (out / "FAILED.txt").write_text(
            "Ollama no responde. No hay métricas.\n" + json.dumps(ollama_info),
            encoding="utf-8",
        )
        print("FAIL ollama", out)
        return

    print("indexing", KB)
    chunks = load_kb_chunks()
    cache_path = OUT_ROOT / "_embed_cache.json"
    key = hashlib.sha256(
        f"{EMB_MODEL}|{CHUNK_SIZE}|{CHUNK_OVERLAP}|{len(chunks)}".encode()
    ).hexdigest()
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    if cache.get("key") == key:
        embeddings = cache["embeddings"]
        print("embed cache hit", len(embeddings))
    else:
        print("embedding", len(chunks), "chunks")
        embeddings = ollama_embed([c["text"] for c in chunks])
        cache_path.write_text(
            json.dumps({"key": key, "embeddings": embeddings}),
            encoding="utf-8",
        )

    fieldnames = [
        "item_id",
        "category",
        "split",
        "source_file",
        "page",
        "question",
        "reference_answer",
        "keywords",
        "retrieved_sources",
        "retrieved_preview",
        "rag_answer",
        "vanilla_answer",
        "mrr",
        "ndcg",
        "coverage",
        "rag_accuracy",
        "rag_completeness",
        "rag_relevance",
        "rag_faithfulness",
        "rag_is_hallucination",
        "vanilla_accuracy",
        "vanilla_completeness",
        "vanilla_relevance",
        "vanilla_faithfulness",
        "vanilla_is_hallucination",
        "error",
    ]
    rows = []
    t0 = time.time()
    for i, item in enumerate(gold, start=1):
        print(f"[{i}/{len(gold)}] {item['category']} {item['question'][:60]}")
        row = {k: "" for k in fieldnames}
        row.update(
            {
                "item_id": i,
                "category": item["category"],
                "split": item.get("split", ""),
                "source_file": item.get("source_file", ""),
                "page": item.get("page", ""),
                "question": item["question"],
                "reference_answer": item["reference_answer"],
                "keywords": " | ".join(item.get("keywords") or []),
            }
        )
        try:
            q_emb = ollama_embed([item["question"]])[0]
            dense = sorted(
                ((cosine(q_emb, emb), idx) for idx, emb in enumerate(embeddings)),
                reverse=True,
            )
            dense_ids = [idx for _, idx in dense[:DENSE_K]]
            bm25_ids = bm25_rank(item["question"], chunks, BM25_K)
            fused = rrf([dense_ids, bm25_ids], RRF_K)[:FINAL_K]
            retrieved = [chunks[idx] for idx in fused]
            context = "\n\n".join(
                f"[{c['source']}]\n{c['text']}" for c in retrieved
            )
            row["retrieved_sources"] = " | ".join(c["source"] for c in retrieved)
            row["retrieved_preview"] = " || ".join(c["text"][:240] for c in retrieved[:3])
            ir = ir_metrics(item.get("keywords") or [], [c["text"] for c in retrieved], FINAL_K)
            row["mrr"] = f"{ir['mrr']:.4f}"
            row["ndcg"] = f"{ir['ndcg']:.4f}"
            row["coverage"] = f"{ir['coverage']:.4f}"

            rag_answer = generate(item["question"], context)
            vanilla_answer = generate(item["question"], None)
            row["rag_answer"] = rag_answer
            row["vanilla_answer"] = vanilla_answer
            rag_j = judge(item["question"], rag_answer, item["reference_answer"], context)
            van_j = judge(item["question"], vanilla_answer, item["reference_answer"], "")
            row["rag_accuracy"] = rag_j["accuracy"]
            row["rag_completeness"] = rag_j["completeness"]
            row["rag_relevance"] = rag_j["relevance"]
            row["rag_faithfulness"] = rag_j["faithfulness"]
            row["rag_is_hallucination"] = rag_j["is_hallucination"]
            row["vanilla_accuracy"] = van_j["accuracy"]
            row["vanilla_completeness"] = van_j["completeness"]
            row["vanilla_relevance"] = van_j["relevance"]
            row["vanilla_faithfulness"] = van_j["faithfulness"]
            row["vanilla_is_hallucination"] = van_j["is_hallucination"]
        except Exception as exc:
            row["error"] = str(exc)[:500]
            print("  ERROR", exc)
        rows.append(row)
        with (out / "results.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def mean(key: str, pred) -> float | None:
        vals = [float(r[key]) for r in rows if r[key] not in {"", None} and not r["error"] and pred(r)]
        return (sum(vals) / len(vals)) if vals else None

    ok = [r for r in rows if not r["error"]]
    by_cat = defaultdict(list)
    for r in ok:
        by_cat[r["category"]].append(r)

    def avg(vals: list[float]) -> float | None:
        return (sum(vals) / len(vals)) if vals else None

    summary = {
        "run_id": run_id,
        "n_total": len(rows),
        "n_ok": len(ok),
        "elapsed_s": round(time.time() - t0, 1),
        "global": {
            "mrr": avg([float(r["mrr"]) for r in ok]),
            "ndcg": avg([float(r["ndcg"]) for r in ok]),
            "coverage": avg([float(r["coverage"]) for r in ok]),
            "rag_accuracy": avg([float(r["rag_accuracy"]) for r in ok]),
            "vanilla_accuracy": avg([float(r["vanilla_accuracy"]) for r in ok]),
            "rag_hallucination_rate": avg(
                [1.0 if str(r["rag_is_hallucination"]).lower() == "true" else 0.0 for r in ok]
            ),
            "vanilla_hallucination_rate": avg(
                [1.0 if str(r["vanilla_is_hallucination"]).lower() == "true" else 0.0 for r in ok]
            ),
        },
        "by_category": {},
    }
    for cat, group in sorted(by_cat.items()):
        summary["by_category"][cat] = {
            "n": len(group),
            "mrr": avg([float(r["mrr"]) for r in group]),
            "rag_accuracy": avg([float(r["rag_accuracy"]) for r in group]),
            "vanilla_accuracy": avg([float(r["vanilla_accuracy"]) for r in group]),
            "rag_hallucination_rate": avg(
                [1.0 if str(r["rag_is_hallucination"]).lower() == "true" else 0.0 for r in group]
            ),
        }

    def as_failure(r: dict) -> dict:
        return {
            "item_id": r["item_id"],
            "category": r["category"],
            "question": r["question"],
            "retrieved_sources": r["retrieved_sources"],
            "retrieved_preview": r["retrieved_preview"],
            "rag_answer": r["rag_answer"],
            "reference_answer": r["reference_answer"],
            "mrr": r["mrr"],
            "rag_accuracy": r["rag_accuracy"],
            "cause_hint": "recuperación débil" if float(r["mrr"] or 0) < 0.5 else "generación/juez",
        }

    preferred = sorted(
        [r for r in ok if r["category"] in {"spanning", "traceability"}],
        key=lambda r: (float(r["mrr"]), float(r["rag_accuracy"])),
    )
    rest = sorted(ok, key=lambda r: (float(r["mrr"]), float(r["rag_accuracy"])))
    seen: set[str] = set()
    failures = []
    for r in preferred + rest:
        key = str(r["item_id"])
        if key in seen:
            continue
        seen.add(key)
        failures.append(as_failure(r))
        if len(failures) == 2:
            break
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    config["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (out / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE", out)
    print(json.dumps(summary["global"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
