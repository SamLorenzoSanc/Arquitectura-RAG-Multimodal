"""Parchea el TFM .docx abierto en Microsoft Word (COM)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import win32com.client as win32

WD_REPLACE_ALL = 2
WD_FIND_CONTINUE = 1
WD_DO_NOT_SAVE_CHANGES = 0
WD_FORMAT_XML = 11

BACKUP_DIR = Path(
    r"c:\Users\Usuario\Desktop\MasterIA\Asignaturas\Segundo_Cuatrimestre\TFM\Arquitectura-RAG-Multimodal\docs"
)


def para_text(paragraph) -> str:
    return (
        paragraph.Range.Text.replace("\r", "")
        .replace("\x07", "")
        .replace("\x0b", " ")
        .strip()
    )


def set_para(paragraph, text: str) -> None:
    rng = paragraph.Range.Duplicate
    # Conserva la marca de párrafo (\r).
    if rng.End > rng.Start:
        rng.End = rng.End - 1
    rng.Text = text


def find_replace_stories(doc, old: str, new: str) -> int:
    changed = 0
    story = doc.StoryRanges(1)
    while story is not None:
        find = story.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        found = find.Execute(
            old,
            False,
            False,
            False,
            False,
            False,
            True,
            WD_FIND_CONTINUE,
            False,
            new,
            WD_REPLACE_ALL,
        )
        if found:
            changed += 1
        try:
            story = story.NextStoryRange
        except Exception:
            story = None
    return changed


def first_match(paragraphs, *needles: str):
    needles_l = [n.lower() for n in needles]
    for idx, p in enumerate(paragraphs):
        t = para_text(p)
        low = t.lower()
        if all(n in low for n in needles_l):
            return idx, p, t
    return None, None, None


def all_matches(paragraphs, *needles: str):
    needles_l = [n.lower() for n in needles]
    out = []
    for idx, p in enumerate(paragraphs):
        t = para_text(p)
        low = t.lower()
        if all(n in low for n in needles_l):
            out.append((idx, p, t))
    return out


def patch(doc) -> list[str]:
    log: list[str] = []
    paragraphs = list(doc.Paragraphs)

    def replace_one(label: str, new: str, *needles: str, must_start: str | None = None) -> bool:
        idx, p, old = first_match(paragraphs, *needles)
        if p is None:
            log.append(f"NO ENCONTRADO: {label}")
            return False
        if must_start and not para_text(p).startswith(must_start):
            # sigue buscando
            for i, cand, t in all_matches(paragraphs, *needles):
                if t.startswith(must_start):
                    idx, p, old = i, cand, t
                    break
            else:
                log.append(f"NO ENCONTRADO (prefijo): {label}")
                return False
        set_para(p, new)
        log.append(f"OK [{idx}] {label} ({len(old)} → {len(new)} chars)")
        return True

    # --- Portada / encabezados ---
    n = find_replace_stories(
        doc,
        "Impacto de las Alucinaciones de los LLMs",
        "Impacto de la Arquitectura RAG en las Alucinaciones de los LLMs",
    )
    log.append(f"Título (historias Word): {n} rangos con coincidencias")

    # --- Resumen ---
    replace_one(
        "Resumen ES",
        "El presente Trabajo de Fin de Máster evalúa la capacidad de la arquitectura Generación Aumentada por Recuperación (RAG) para mitigar la tasa de alucinaciones y mejorar la exactitud factual en Modelos de Lenguaje de Gran Escala (LLM) aplicados a documentación normativa y técnica del sector agrícola (PAC y POSEI). Se implementa un MVP contenedorizado de asistente documental: el usuario inicia sesión, sube documentos e interroga un RAG agéntico que decide cuándo consultar la base de conocimiento y responde con citas. El núcleo se construye con arquitectura hexagonal en FastAPI, PostgreSQL/pgvector, Ollama (Llama 3.2 y nomic-embed-text) y un front-end en React, Vite y Tailwind CSS. El banco de evaluación versionado contiene 21 ítems (19 preguntas únicas) en siete categorías. Los resultados exploratorios se resumen así: MRR global de 0,7911, exactitud media del juez de 4,21 sobre 5 y tasa de alucinación binaria de 0,19 con RAG frente a 0,62 sin recuperación. RAG mitiga las alucinaciones extrínsecas en consultas directas y temporales; en consultas transversales (spanning) el MRR cae a 0,4700 y se requiere evolucionar hacia grafos de conocimiento y verificación agéntica.",
        "evalúa cuantitativamente la capacidad",
        "150 casos",
    )
    replace_one(
        "Palabras clave",
        "Generación Aumentada por Recuperación (RAG), RAG agéntico, Alucinaciones, LLM, PostgreSQL/pgvector, Arquitectura hexagonal",
        "Alucinaciones de AI",
        "IA Explicable",
    )
    replace_one(
        "Abstract EN",
        "This Master's Thesis evaluates Retrieval-Augmented Generation (RAG) for mitigating factual hallucinations in LLMs applied to agricultural regulatory documentation (CAP/POSEI). The artefact is a containerized MVP: login, document ingest and an agentic RAG assistant with citations. The hexagonal backend uses FastAPI, PostgreSQL/pgvector and Ollama (Llama 3.2 and nomic-embed-text); the frontend uses React, Vite and Tailwind CSS. The versioned evaluation bank contains 21 items (19 unique questions). Exploratory scores include global MRR 0.7911, judge accuracy 4.21/5 and binary hallucination 0.19 with RAG versus 0.62 without retrieval. RAG does not eliminate hallucinations; it reduces extrinsic errors on direct queries and degrades on holistic spanning questions.",
        "This Master's Thesis quantitatively evaluates",
        "150 test cases",
    )
    replace_one(
        "Keywords",
        "Retrieval-Augmented Generation (RAG), Agentic RAG, AI Hallucinations, LLM, PostgreSQL/pgvector, Hexagonal architecture.",
        "Generative Artificial Intelligence, Vector Databases",
    )

    # --- Estructura ---
    replace_one(
        "Cap. 2 en estructura",
        "El Capítulo 2: Objetivos y planificación establece el objetivo general (diseñar, implementar y evaluar un MVP de asistente documental basado en RAG agéntico) y seis objetivos específicos, tratados como épicas Scrum y descompuestos en siete tareas sobre el prototipo real: FastAPI hexagonal, PostgreSQL/pgvector, Ollama (Llama 3.2), React/Vite y Tailwind CSS.",
        "El Capítulo 2: Objetivos del TFM",
    )
    replace_one(
        "Cap. 4 en estructura",
        "El Capítulo 4: Marco metodológico y arquitectura describe el método hexagonal (puertos y adaptadores) aplicado al bounded context RAG, los flujos del MVP (registro, login, documentos y chat) y el diseño experimental desacoplado entre recuperador y generador.",
        "El Capítulo 4:",
        "LangChain",
        "ChromaDB",
    )
    replace_one(
        "Cap. 5 en estructura",
        "El Capítulo 5: Arquitectura e implementación documenta el prototipo: dominio en gateway/rag, casos de uso AnswerQuestion, HybridRetrieve e IngestDocument, adaptadores PostgreSQL/pgvector, BM25 y Ollama, y la interfaz React/Vite/Tailwind con autenticación, catálogo documental y chat con fuentes. El despliegue se realiza con Docker Compose.",
        "El Capítulo 5:",
        "ChromaDB",
        "Django",
    )

    # --- Objetivos ---
    replace_one(
        "Objetivo general",
        "Diseñar, implementar y evaluar un MVP de asistente documental basado en RAG agéntico que mejore la precisión, la relevancia y la trazabilidad de las respuestas generadas por un LLM local sobre un corpus agrícola y normativo.",
        "Diseñar, implementar y evaluar un asistente inteligente para el sector agrícola",
    )
    replace_one(
        "Objetivo general (párrafo 2)",
        "Este objetivo engloba la finalidad última del proyecto: un prototipo mínimo usable —autenticación, ingesta de documentos y chat con citas— con el que medir si anclar la generación a evidencia recuperada reduce las alucinaciones frente a un LLM sin recuperación.",
        "Este objetivo engloba la finalidad última",
        "Cuaderno Digital",
    )
    replace_one(
        "OE1",
        "Analizar el estado del arte en arquitecturas RAG, sistemas agénticos y aplicaciones de inteligencia artificial en el sector agrario, identificando las limitaciones de las soluciones existentes y las oportunidades de mejora. Este objetivo se corresponde con el marco teórico y el estado del arte desarrollado en el Capítulo 3.",
        "Analizar el estado del arte",
        "Capítulo 2 del TFM",
    )
    replace_one(
        "OE2",
        "Diseñar la arquitectura del sistema, definiendo los componentes de ingestación de datos, recuperación semántica, orquestación agéntica, generación de respuestas y presentación de la información. Este objetivo se desarrolla en el Capítulo 5, donde se describen las decisiones de arquitectura y los componentes del sistema.",
        "Diseñar la arquitectura del sistema",
        "se desarrolla en el Capítulo 3",
    )
    replace_one(
        "OE3",
        "Implementar el prototipo funcional, integrando la base de datos vectorial (PostgreSQL/pgvector), el modelo de lenguaje (Llama 3.2 a través de Ollama), el núcleo RAG en FastAPI con arquitectura hexagonal y la interfaz de usuario desarrollada con React, Vite y Tailwind CSS. Este objetivo se aborda en los Capítulos 5 y 6 (implementación y despliegue).",
        "Implementar el prototipo funcional",
        "LangChain",
        "PostgresDB",
    )
    idx, p, old = first_match(paragraphs, "Desarrollar el módulo de trazabilidad")
    if p is not None and "no se garantiza" not in old.lower():
        set_para(
            p,
            old.rstrip()
            + " Las citas se muestran en el chat junto a cada respuesta. La página de origen se propaga cuando el parser la extrae; no se garantiza en todos los formatos.",
        )
        log.append(f"OK [{idx}] OE4 (añadida salvedad de página)")
    else:
        log.append("OE4: sin cambio o ya parcheado")
    replace_one(
        "OE5",
        "Evaluar el rendimiento del sistema en términos de fidelidad, relevancia, latencia y uso de recursos, utilizando métricas propias de recuperación, un LLM-as-a-judge, un adaptador RAGAS y pruebas en hardware local. Este objetivo se cumple en el capítulo de evaluación.",
        "Evaluar el rendimiento del sistema",
        "framework RAGAS",
        "Capítulo 5",
    )

    replace_one(
        "Intro tareas",
        "Cada objetivo específico se gestiona como una épica Scrum. El trabajo se reduce a siete tareas, ordenadas por dependencia. El prototipo del MVP usa FastAPI hexagonal, PostgreSQL/pgvector, Ollama (Llama 3.2), React/Vite y Tailwind CSS.",
        "Cada objetivo específico queda como tarea",
    )
    replace_one(
        "Tarea 1",
        "Tarea 1. Documentación e investigación (OE1): revisar LLMs, alucinaciones, RAG y sistemas agénticos; comparar LangChain, LlamaIndex, Haystack y una implementación hexagonal propia; redactar el estado del arte.",
        "Tarea 1. Documentación e Investigación",
    )
    replace_one(
        "Tarea 2",
        "Tarea 2. Diseño del prototipo, entidades y dominio (OE2): definir los flujos del MVP (registro, login, documentos y chat); delimitar el hexágono RAG; modelar RetrievedChunk, RetrievalQuery y RetrievalBundle y los puertos ChunkRepository y LlmPort, sin dependencia de FastAPI ni SQLAlchemy.",
        "Tarea 2. Diseño del prototipo web",
    )
    replace_one(
        "Tarea 3",
        "Tarea 3. Back-end (OE3): implementar gateway/rag/domain; casos de uso AnswerQuestion, HybridRetrieve, IngestDocument, EvaluateRetrieval y EvaluateAnswer; adaptadores pgvector, BM25, Ollama y Cross-Encoder; controladores FastAPI de autenticación, documentos y chat; fachada AgenticRAGService y composition root build_rag_container.",
        "Tarea 3. Backend-end",
    )
    replace_one(
        "Tarea 4",
        "Tarea 4. Front-end (OE3): autenticación y panel con dos vistas del MVP: documentos (subida, listado y borrado) y asistente conversacional con RAG agéntico y visualización de fuentes.",
        "Tarea 4. Front-end",
    )
    replace_one(
        "Tarea 5",
        "Tarea 5. Trazabilidad y citación (OE4): enriquecer fragmentos con documento de origen; mostrar fuentes en el chat; registrar traces de pregunta, contexto y respuesta; declarar falta de evidencia en lugar de inventar.",
        "Tarea 5. Trazabilidad y citación",
    )
    replace_one(
        "Tarea 6",
        "Tarea 6. Evaluación (OE5): banco de pruebas del dominio agrario (21 ítems versionados, 19 preguntas únicas); métricas de recuperación, LLM-as-a-judge, adaptador RAGAS, comparación con y sin RAG, y latencia en local.",
        "Tarea 6. Evaluación",
    )
    replace_one(
        "Tarea 7",
        "Tarea 7. Memoria y presentación final (OE6): redactar la memoria, la guía de arranque con Docker Compose y la defensa (problema, hexágono, demostración del asistente y resultados).",
        "Tarea 7. Memoria y presentación final",
    )

    # Alcance: insertar después de Tarea 7 si no existe.
    if not first_match(paragraphs, "Quedan fuera de alcance de esta edición")[1]:
        idx, p, _ = first_match(paragraphs, "Tarea 7. Memoria y presentación final (OE6)")
        if p is not None:
            p.Range.InsertAfter(
                "\rQuedan fuera de alcance de esta edición el razonamiento visual end-to-end, la certificación industrial del despliegue, el reentrenamiento del LLM, y los módulos de organización, cuaderno de campo, OpenData y laboratorio de evaluación en la interfaz. Si aparecen en capturas, se presentan como extensión del prototipo, no como requisito del MVP.\r"
            )
            log.append("OK inserción: fuera de alcance (tras Tarea 7)")
            paragraphs = list(doc.Paragraphs)
        else:
            log.append("NO ENCONTRADO: ancla para fuera de alcance")
    else:
        log.append("Fuera de alcance: ya existía")

    # --- Método ---
    replace_one(
        "RAGAS método",
        "La evaluación automática combina tres familias que no deben mezclarse: (1) métricas propias de recuperación (Recall@K, Precision@K, MRR, nDCG); (2) un LLM-as-a-judge local (exactitud, exhaustividad y relevancia en escala 1–5); (3) un adaptador RAGAS (faithfulness, answer relevancy, context precision, context recall) con marca binaria de alucinación. Si la librería RAGAS no está operativa en el entorno, el adaptador aplica un fallback heurístico etiquetado como tal; esas puntuaciones no se presentan como métricas RAGAS oficiales.",
        "framework especializado RAGAS",
        "escala continua",
    )
    replace_one(
        "Panel PAC",
        "No se incluye en esta edición un panel de inspectores PAC ni un coeficiente de acuerdo interanotador. La validación humana queda como trabajo futuro; los resultados numéricos proceden del juez automático y de las métricas de recuperación sobre el banco versionado.",
        "panel de evaluación formado por técnicos",
    )
    replace_one(
        "ChromaDB indexación",
        "En esta fase inicial, la muestra de N = 20 documentos oficiales en formato PDF se somete a fragmentación contextual e indexación densa en PostgreSQL/pgvector, con un índice léxico BM25 por tenant. El modelo de embeddings de la demo contenedorizada es nomic-embed-text; la generación usa Llama 3.2 a través de Ollama.",
        "ChromaDB",
        "qwen3-embedding",
    )

    # --- Conclusiones ---
    replace_one(
        "Conclusiones intro",
        "El presente Trabajo de Fin de Máster se planteó con la finalidad de evaluar, medir y validar cuantitativamente la capacidad de la arquitectura Retrieval-Augmented Generation (RAG) para mitigar el problema de las alucinaciones factuales en Modelos de Lenguaje de Gran Escala (LLMs) aplicados a la documentación normativa y técnica del sector agrícola, centrándose específicamente en la Política Agraria Común (PAC) y el Programa POSEI. Tras la ejecución del protocolo experimental sobre el prototipo contenedorizado, se cubren los seis objetivos específicos del Capítulo 2 en el alcance de un MVP: estado del arte, diseño hexagonal, implementación FastAPI/React, citación de fuentes, evaluación exploratoria y documentación.",
        "consecución plena y sistemática",
    )
    replace_one(
        "Conclusiones OE1",
        "OE1 (estado del arte) se cumple con el capítulo de marco teórico, que sitúa RAG, alucinaciones y alternativas de orquestación, y justifica una implementación hexagonal propia frente a LangChain o LlamaIndex. El corpus de demostración ronda 20 documentos PAC/POSEI (~50 páginas equivalentes).",
        "primer objetivo específico",
        "cumplido al 100%",
    )
    replace_one(
        "Conclusiones OE2",
        "OE2 y OE3 (diseño e implementación) se cumplen con el MVP: autenticación, ingesta documental e índice híbrido (pgvector + BM25 + RRF), generación local con Llama 3.2 y chat con fuentes.",
        "segundo objetivo específico",
        "cumplimiento del 100%",
    )
    replace_one(
        "Conclusiones OE3/dataset",
        "OE4 (trazabilidad) se cumple al mostrar las fuentes recuperadas junto a cada respuesta. La citación por página depende de los metadatos extraídos en la ingesta y no está garantizada en todos los formatos.",
        "tercer objetivo específico",
        "150 pruebas",
    )
    replace_one(
        "Conclusiones OE4/RAGAS",
        "OE5 (evaluación) se cumple de forma exploratoria, no como auditoría legal. Sobre 21 ítems (19 preguntas únicas) el recuperador obtuvo MRR 0,7911 y nDCG@10 0,8244. El juez automático asignó exactitud 4,21, exhaustividad 3,94 y relevancia 4,38 sobre 5. La tasa binaria de alucinación pasó de 0,62 sin RAG a 0,19 con recuperación. Estos valores no deben atribuirse a un dataset de 150 pruebas ni a un cómputo RAGAS oficial sin corrida versionada.",
        "cuarto objetivo específico",
        "marco RAGAS",
    )
    replace_one(
        "Conclusiones objetivo general",
        "OE6 se cumple con esta memoria, el repositorio y la guía de arranque con Docker Compose. El objetivo general se alcanza en el sentido del MVP: hay un prototipo usable que ancla la generación a evidencia recuperada y permite comparar el LLM con y sin RAG. No se afirma que RAG elimine las alucinaciones. Resultados exploratorios: exactitud factual 4,21; relevancia 4,38; MRR global 0,7911.",
        "Finalmente, la consecución",
        "Exactitud Factual",
    )

    replace_one(
        "Prospectiva agéntica",
        "El MVP ya incorpora un orquestador agéntico con la herramienta search_knowledge_base. El trabajo futuro consiste en especializar agentes de ruteo, cálculo numérico y verificación jurídica, y en explorar GraphRAG para consultas transversales. También se propone ampliar el corpus a boletines autonómicos y reglamentos de la Unión Europea.",
        "evolución del sistema hacia un esquema de RAG Agéntico",
    )
    replace_one(
        "Despliegue Docker",
        "Con el propósito de validar de forma práctica los hallazgos y demostrar el MVP, se contenedorizó AgroPS con Docker Compose. El entorno de demo orquesta frontend (Nginx/React), API FastAPI, PostgreSQL/pgvector y Ollama. El arranque local se describe en docs/DOCKER.md y scripts/demo_up.ps1. El sistema mitiga alucinaciones en los casos evaluados; no las erradica.",
        "erradicación de alucinaciones factuales",
        "Docker Compose",
    )
    replace_one(
        "Anexo repositorio",
        "Todo el código fuente desarrollado durante este Trabajo Fin de Máster, incluyendo la implementación hexagonal del RAG, la indexación documental, el procesamiento de PDFs, la generación de embeddings, el adaptador de evaluación y los scripts de despliegue Docker, se encuentra disponible en el siguiente repositorio de GitHub: https://github.com/SamLorenzoSanc/Arquitectura-RAG-Multimodal",
        "repositorio de GitHub",
        "RAGAS",
    )

    idx, p, old = first_match(paragraphs, "ChromaDB:", "base de datos vectorial")
    if p is not None and "este prototipo" not in old.lower():
        set_para(
            p,
            old.rstrip()
            + " En este prototipo la base vectorial operativa es PostgreSQL con la extensión pgvector, no ChromaDB.",
        )
        log.append(f"OK [{idx}] glosario ChromaDB")
    else:
        log.append("Glosario ChromaDB: sin cambio o ya parcheado")

    idx, p, old = first_match(paragraphs, "LangChain:", "Framework de desarrollo")
    if p is not None and "gateway/rag" not in old.lower():
        set_para(
            p,
            old.rstrip()
            + " LangChain se revisó en el estado del arte; el prototipo no lo usa como orquestador. El núcleo RAG es propio (gateway/rag).",
        )
        log.append(f"OK [{idx}] glosario LangChain")

    for idx, p, old in all_matches(paragraphs, "Gestión de la Organización"):
        if old.lower().startswith("ilustración") and "mvp" not in old.lower():
            set_para(
                p,
                old.rstrip()
                + " Extensión del prototipo; queda fuera del alcance del MVP de esta edición.",
            )
            log.append(f"OK [{idx}] pie organización")
    for idx, p, old in all_matches(paragraphs, "representada en Grafo"):
        if old.lower().startswith("ilustración") and "mvp" not in old.lower():
            set_para(
                p,
                old.rstrip()
                + " Extensión del prototipo; queda fuera del alcance del MVP de esta edición.",
            )
            log.append(f"OK [{idx}] pie grafo")

    banco = (
        "El banco versionado contiene 21 ítems (19 preguntas únicas) en siete categorías: "
        "direct_fact (6), temporal (4), relationship (5), spanning (3), regulatory_compliance (1), "
        "regulatory_fact (1) y traceability (1). No se aporta en el repositorio un dataset congelado de 150 preguntas."
    )
    paragraphs = list(doc.Paragraphs)
    for idx, p, old in all_matches(paragraphs, "150"):
        low = old.lower()
        if "21 ítems" in old or "no deben atribuirse" in low or "no se aporta" in low:
            continue
        if old.startswith("OE") or old.startswith("Tarea 6"):
            continue
        if any(k in low for k in ("prueba", "casos", "dataset", "test cases", "test case")):
            set_para(p, banco)
            log.append(f"OK [{idx}] dataset 150 -> 21 items")

    globals_ = [
        ("Memoria No Paramétrica", "Memoria Paramétrica"),
        ("erradicación de alucinaciones", "mitigación de alucinaciones"),
        ("elimina por completo", "elimina de forma general"),
        ("entorno productivo real", "prototipo funcional contenedorizado"),
        ("cumplido al 100%", "cubierto en el alcance del MVP"),
        ("cumplió al 100%", "se cubrió en el alcance del MVP"),
        ("cumplimiento del 100%", "cobertura en el alcance del MVP"),
    ]
    for old, new in globals_:
        n = find_replace_stories(doc, old, new)
        if n:
            log.append(f"Global '{old}' -> '{new}': {n} historias")

    paragraphs = list(doc.Paragraphs)
    for idx, p, old in all_matches(paragraphs, "Django"):
        if old.startswith("LangChain") or old.startswith("Django"):
            continue
        if "Framework" in old and len(old) < 40:
            continue
        set_para(p, old.replace("Django", "FastAPI"))
        log.append(f"OK [{idx}] Django -> FastAPI")

    return log


def restore_from_backup(word):
    import shutil

    backup = BACKUP_DIR / "TFM_Samuel_Lorenzo_Sanchez_backup_20260819_102749.docx"
    local_src = Path(
        r"c:\Users\Usuario\OneDrive - Universidad Alfonso X el Sabio\TFM_Samuel_Lorenzo_Sanchez.docx"
    )
    if not backup.exists():
        raise SystemExit(f"No encuentro el backup {backup}")

    wd_do_not_save = 0
    for i in range(word.Documents.Count, 0, -1):
        candidate = word.Documents(i)
        name = candidate.Name
        if "TFM_Samuel_Lorenzo_Sanchez" in name and "backup" not in name.lower():
            candidate.Close(wd_do_not_save)

    try:
        shutil.copy2(backup, local_src)
        opened = word.Documents.Open(str(local_src))
    except Exception:
        opened = word.Documents.Open(str(backup))
        try:
            opened.SaveAs(str(local_src))
        except Exception as exc:
            print(f"SaveAs OneDrive fallo ({exc}); trabajo sobre el backup abierto.")
    print(f"RESTAURADO desde {backup}")
    return opened


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    word = win32.GetActiveObject("Word.Application")
    word.DisplayAlerts = 0
    doc = restore_from_backup(word)

    word.ScreenUpdating = False
    try:
        log = patch(doc)
    finally:
        word.ScreenUpdating = True

    def text(p):
        return p.Range.Text.replace("\r", "").replace("\x07", "").strip()

    for p in doc.Paragraphs:
        t = text(p)
        if t == "Licenciae":
            set_para(p, "Licencia")
            log.append("fix Licencia")
        elif t.startswith("Implementar el prototipo funcional") and (
            "LangChain" in t or "PostgresDB" in t
        ):
            set_para(
                p,
                "Implementar el prototipo funcional, integrando la base de datos vectorial (PostgreSQL/pgvector), el modelo de lenguaje (Llama 3.2 a través de Ollama), el núcleo RAG en FastAPI con arquitectura hexagonal y la interfaz de usuario desarrollada con React, Vite y Tailwind CSS. Este objetivo se aborda en los Capítulos 5 y 6 (implementación y despliegue).",
            )
            log.append("fix OE3")

    doc.Save()
    print("SAVED", doc.FullName)
    print("---- LOG ----")
    for line in log:
        print(line)


if __name__ == "__main__":
    main()
