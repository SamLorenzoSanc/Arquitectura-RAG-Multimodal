# Guion oral — Defensa TFM AgroPS (15 min)

Abrir: `docs/presentacion_defensa/Defensa_TFM_AgroPS_15min.pptx` (11 diapositivas). Regenerar: `python docs/presentacion_defensa/build_pptx.py`.

El pie de **todas** las diapositivas es el mismo título que la portada. Las notas del orador (Vista → Notas) copian el «qué decir» de cada minuto.

**Título único (portada = pie):** *Impacto de la Arquitectura RAG en las Alucinaciones de los LLMs*.

**Demo:** 90–120 s al final (o vídeo pregrabado si Ollama tarda). Pregunta viva: «¿Qué significa POSEI?» y «¿N.º de registro de AGROIL en platanera?» — la segunda muestra el límite de trazabilidad.

| Min | Qué mostrar | Qué decir |
|-----|-------------|-----------|
| 0:00–0:40 | Portada | Título. «El problema no es la IA en general: es si RAG **mitiga** alucinaciones en normativa agraria.» |
| 0:40–2:00 | Pregunta | Leer: ¿en qué medida un RAG híbrido textual reduce alucinaciones frente al mismo LLM sin recuperación, en PAC/POSEI? Agenda: problema → arquitectura → corpus → cifras → demo. |
| 2:00–3:30 | Problema | LLM fluido inventa importes/plazos/códigos. Extrínseca vs intrínseca. Un asesor no puede auditar un chat sin fuentes. |
| 3:30–5:30 | Arquitectura | **Evaluado:** RAG textual modular (denso + BM25 + RRF). **Producto, no corrida:** LangGraph. **Fuera:** GraphRAG, visión end-to-end, RAGAS oficial, certificación. Citas: documento + sección + chunk. |
| 5:30–7:00 | Corpus + banco | 29 markdown `asesor-canarias` (destilados de consolidados POSEI 2025–2026). N=35 (7×5) con respuesta esperada y `source_file`. |
| 7:00–10:30 | Resultados | N=35, `run_20260819`. Hall. **31,4 % → 8,6 %**. Acc. **3,31 → 4,46**. MRR 0,81. **No es cero.** Hueco: trazabilidad (AGROIL inventa ES-01744). Juez ≠ humano. |
| 10:30–12:30 | **Demo o vídeo** | Chat con fuentes. Si el retrieve tarda, vídeo de 60–90 s. |
| 12:30–14:20 | Límites | N pequeño; mismo modelo genera y juzga; página PDF no siempre en el chunk. Mitigar ≠ certificar. |
| 14:20–15:00 | Cierre | Frase de defensa + preguntas. |

### Frase de defensa

«No prometemos cero alucinaciones. Demostramos un anclaje medible a evidencia recuperada, con abstención, citas (documento, sección, fragmento) y una comparación pareada LLM sin RAG frente a RAG.»

### Si preguntan

- **¿Por qué híbrido?** El denso cubre paráfrasis; BM25 clava códigos; RRF fusiona sin entrenar un ranker.
- **¿Por qué no GraphRAG / multimodal?** Están fuera del objeto experimental; el OCR solo alimenta texto.
- **¿RAGAS?** Definido en el estado del arte; no se ejecutó en la corrida congelada.
- **No mezclar** el run N=150 sintético con el oro N=35.

### Material

- Figuras: `diagrama-ingesta-rag.png`, `diagrama-respuesta-rag.png`
- Evidencia: `docs/evaluation_runs/run_20260819T165515Z/`
- Banco: `knowledge-base/gold_tests.jsonl`
