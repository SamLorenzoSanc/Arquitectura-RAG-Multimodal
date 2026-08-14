from __future__ import annotations

import re
import unicodedata

AGRO_SYNONYMS: dict[str, str] = {
    "riego": "riego irrigación gotero aspersión",
    "tomate": "tomate solanum lycopersicum",
    "plátano": "plátano banana musa",
    "platano": "plátano banana musa",
    "papaya": "papaya carica",
    "aguacate": "aguacate palta persea",
    "papa": "papa patata solanum tuberosum",
    "viña": "viña vid uva viticultura",
    "vina": "viña vid uva viticultura",
    "posei": "posei ayudas subvenciones canarias",
    "subvención": "subvención ayuda prima incentivo",
    "subvencion": "subvención ayuda prima incentivo",
    "plaga": "plaga insecto patogeno enfermedad fitosanitario",
    "fertilizante": "fertilizante abono nutriente npk",
    "suelo": "suelo edafologia materia organica",
    "sequía": "sequía deficit hidrico estres hidrico",
    "sequia": "sequía deficit hidrico estres hidrico",
    "gotero": "gotero goteros goteo filtro recambio taponamiento",
    "recambio": "recambio recambios pieza filtro junta fusible sonda gotero",
    "herramienta": "herramienta tijera podadora llave destornillador EPI",
    "cámara": "cámara camara frio reefer temperatura sonda",
    "camara": "cámara camara frio reefer temperatura sonda",
    "trips": "trips thrips insecto plaga platanera",
    "sigatoka": "sigatoka cercospora mancha foliar enfermedad",
    "nematodo": "nematodo nematodos radicicola suelo raiz",
    "salinidad": "salinidad salino conductividad cloruro",
    "viento": "viento alisio deshoje daño tutores",
    "clorosis": "clorosis amarilleo carencia hierro nitrogeno",
    "maleza": "maleza hierba adventicia desbroce",
}


def normalize_lexical(text: str | None) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def tokenize(text: str | None) -> list[str]:
    text = normalize_lexical(text)
    return re.findall(r"[^\W_]+(?:[-/][^\W_]+)*", text, flags=re.UNICODE)


def expand_agro_query(question: str) -> str:
    """Expande términos agrarios sin LLM."""
    lower = question.lower()
    extras = [
        expansion
        for term, expansion in AGRO_SYNONYMS.items()
        if term in lower
    ]
    if not extras:
        return question
    return f"{question} {' '.join(extras)}"


def should_rewrite_query(question: str) -> bool:
    q = " ".join(question.strip().split())
    if not q:
        return False
    words = q.split()
    if len(words) <= 10:
        return False
    q_lower = q.lower()
    simple_patterns = (
        "cuál es",
        "cual es",
        "quién es",
        "quien es",
        "qué es",
        "que es",
        "dónde está",
        "donde esta",
        "cuándo",
        "cuando",
        "cuánto",
        "cuanto",
        "cuántos",
        "cuantos",
        "cuántas",
        "cuantas",
        "qué fecha",
        "que fecha",
        "qué número",
        "que numero",
    )
    if any(q_lower.startswith(pattern) for pattern in simple_patterns):
        return False
    complex_patterns = (
        "compara",
        "comparar",
        "diferencia entre",
        "diferencias entre",
        "relaciona",
        "relacionar",
        "explica cómo",
        "explica como",
        "explica por qué",
        "explica por que",
        "analiza",
        "analizar",
        "resume",
        "resumir",
        "sintetiza",
        "sintetizar",
        "teniendo en cuenta",
        "a partir de",
        "qué relación",
        "que relacion",
        "cómo afecta",
        "como afecta",
        "en qué medida",
        "en que medida",
    )
    if any(pattern in q_lower for pattern in complex_patterns):
        return True
    return len(words) > 25
