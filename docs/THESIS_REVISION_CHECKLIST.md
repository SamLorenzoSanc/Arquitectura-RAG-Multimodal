# Auditoría y checklist de revisión de la memoria TFM

Fecha de revisión del repositorio: 10-08-2026.

## Estado de la fuente

No se encontró una fuente identificable de la memoria en `.tex`, `.md` o `.docx`, ni un PDF cuyo nombre lo identifique como memoria/TFM. Los PDF presentes pertenecen al corpus o a fixtures y no se modificaron. Por tanto, las correcciones de páginas 21 y 26 no pueden aplicarse de forma segura desde este workspace.

Convención:

- `[x]` evidencia/corrección incorporada en documentación del repositorio;
- `[ ]` pendiente de aplicar o de aportar evidencia en la fuente de memoria.

## Correcciones editoriales

- [ ] Elegir un título canónico y copiarlo literalmente en portada, cabeceras, metadatos y referencias internas. Variante propuesta por el plan: **«Impacto de la Arquitectura RAG en las Alucinaciones de los LLMs»**. Si se conserva el título largo del README, usar exactamente esa variante en todos los lugares.
- [ ] Página 21: eliminar literalmente `Comentado [SL1]`.
- [ ] Página 26: sustituir `Memoria No Paramétrica` por `Memoria Paramétrica`.
- [ ] Renombrar la Tabla 1 como **«Comparación de arquitecturas y enfoques NLP»**.
- [x] En la documentación técnica se usa “reduce/mitiga las alucinaciones en los casos evaluados”; revisar toda la memoria y sustituir “elimina”, “erradica”, “por completo” y equivalentes absolutos.
- [x] Sustituir “entorno productivo real” por **«prototipo funcional contenedorizado»** salvo que se aporte validación productiva.
- [ ] Revisar también citas o capturas del corpus: hay documentos del knowledge base que afirman “erradicación” y mencionan ChromaDB, aunque la arquitectura operativa usa PostgreSQL/pgvector. No tratarlos como descripción del sistema real.

## Tabla de configuración experimental

Insertar una tabla que distinga parámetros iniciales y finales. Valores verificados:

| Campo | Valor verificable | Evidencia/limitación |
|---|---|---|
| Generador RAG | `llama3` por defecto | `RAG_GENERATION_MODEL` y `RAGService`; chat puede seleccionar otro modelo. |
| Generador de chat web | `llama3.2:latest` por defecto | Ruta de chat. Tag/digest instalado no consta. |
| Generador de evaluación | `llama3.2` por defecto | Request de evaluación. |
| Embedding | `qwen3-embedding:latest` | Tag móvil; digest y dimensión efectiva pendientes. |
| Cross-Encoder | `BAAI/bge-reranker-v2-m3` | Revisión Hugging Face no fijada; `max_length=512`, batch 16. |
| Chunk size/overlap | 1000/150 caracteres | No son tokens. |
| Dense top-k inicial | 10 | `retrieval_k`. |
| BM25 top-k inicial | 10 | `bm25_k`. |
| RRF | `k=60` | Hasta 15 candidatos. |
| Top-k final | 3 en servicio; 5 en simulador/evaluación | El “top-k=10” pedido no es el contexto final actual. |
| Temperatura | **No verificable** | El esquema declara 0, pero `RAGService` no la envía al cliente. |
| FastAPI | 0.139.0 bloqueado | `gateway/uv.lock`. |
| pgvector Python | 0.5.0 bloqueado | No equivale a versión de extensión PostgreSQL. |
| SQLAlchemy | 2.0.51 bloqueado | `gateway/uv.lock`. |
| OpenAI client | 2.48.0 bloqueado | `gateway/uv.lock`. |
| LangChain text splitters | 1.1.2 bloqueado | `gateway/uv.lock`. |
| RAGAS | 0.4.3 bloqueado, **sin uso** | Dependencia presente; no hay imports/ejecución. |
| PostgreSQL | imagen `postgres:15` | Parche/digest pendiente. |
| Ollama | imagen `latest` | Versión del servidor y digests de modelos pendientes. |
| SentenceTransformers/rank-bm25 | importados en código | No aparecen como dependencias directas verificables en `pyproject.toml`; versión efectiva pendiente y riesgo de entorno. |

- [ ] Antes de cerrar la memoria, exportar `ollama --version`, `ollama list`, digests, `docker image inspect`, versión de extensión `vector`, GPU/CPU y lockfile del run.
- [ ] Confirmar la temperatura realmente enviada o cambiar la tabla a “predeterminado del servidor Ollama”.

## Dataset y siete categorías

[x] El banco versionado actual contiene **21 filas y 19 preguntas únicas**, no 150. Dos preguntas de `relationship` están duplicadas.

| Categoría | Filas | Únicas | Ejemplo real del banco |
|---|---:|---:|---|
| `direct_fact` | 6 | 6 | Ayuda por hectárea de aguacate bajo POSEI |
| `temporal` | 4 | 4 | Cambio de superficies no productivas BCAM 8 |
| `relationship` | 5 | 3 | Módulo asociado a Alejandro Castro |
| `spanning` | 3 | 3 | Reducción de ayuda sobre 50 ha de tomate |
| `regulatory_compliance` | 1 | 1 | BCAM para pimiento y frutales |
| `regulatory_fact` | 1 | 1 | Volumen máximo de riego |
| `traceability` | 1 | 1 | Página/anexo para jóvenes agricultores |

- [ ] Decidir si la memoria describe el dataset actual (21/19) o aportar el dataset congelado de 150 con fingerprint y procedencia.
- [ ] Eliminar duplicados antes del análisis y actualizar N por categoría.
- [ ] Vincular cada pregunta regulatoria a documento oficial, versión/vigencia, página y chunk. Las respuestas del JSONL no prueban por sí mismas veracidad.

## Validación de las “150 sintéticas” y referencias

No hay evidencia versionada sobre validador, procedimiento o muestra. Texto seguro para insertar mientras siga pendiente:

> **Evidencia pendiente.** El repositorio versiona actualmente 21 filas (19 preguntas únicas). No se ha localizado el artefacto de 150 preguntas ni documentación que identifique quién validó las preguntas sintéticas, qué cualificación tenía, cómo se contrastaron las respuestas de referencia o qué proporción se revisó. Estas afirmaciones no se consideran demostradas hasta incorporar el dataset, protocolo y registro de revisión.

- [ ] Identificar personas por rol (y nombre solo con consentimiento), experiencia y ausencia/conflicto de interés.
- [ ] Describir generación, muestreo, doble revisión, resolución de desacuerdos y control de vigencia.
- [ ] Publicar referencias primarias y anotaciones, o justificar restricciones de acceso.

## Métricas: redacción obligatoria

- [x] **Propias:** Recall@1/@K, Precision@K, MRR, nDCG@K, keywords, falsos positivos, fallos y latencia.
- [x] **LLM-as-a-Judge:** accuracy, completeness y relevance (1–5).
- [x] **RAGAS:** dependencia instalada, sin integración/ejecución visible; no atribuir resultados.
- [ ] Corregir el juez para incluir pregunta, referencia, respuesta y contexto antes de denominar sus scores corrección o groundedness.
- [ ] Añadir exactitud de citas, coincidencia numérica, groundedness/faithfulness y abstención con definiciones explícitas.

## Comparación LLM sin RAG frente a con RAG

El único CSV real (`run_9`) contiene cuatro filas exploratorias, categorías `general`/vacía y un juez metodológicamente incompleto. Sus promedios de accuracy son RAG 3.00 y sin RAG 4.25; no representan el banco de siete categorías ni permiten una conclusión causal.

- [ ] Ejecutar comparación pareada sobre el dataset curado con mismo modelo, prompt base, temperatura efectiva y juez.
- [ ] Informar N, medias, dispersión/intervalos y resultados por categoría.
- [ ] Mantener la tabla principal marcada **PENDIENTE** hasta disponer del artefacto; no reutilizar `run_9` como resultado final.

## Dos fallos holísticos reales

No hay dos fallos documentables con la evidencia versionada. `run_9` marca sus cuatro filas como no fallidas y no guarda chunks/respuestas en el CSV.

- [ ] Fallo 1: añadir ID/run, pregunta, chunks íntegros con fuentes/páginas/scores, respuesta, referencia, dictamen y causa raíz demostrada.
- [ ] Fallo 2: mismo formato, preferiblemente una causa distinta.
- [ ] No reconstruir chunks ni respuestas a partir de la referencia esperada.

## Resultados por categoría

- [ ] Ejecutar y publicar las siete categorías. Actualmente solo existen conteos del banco, no resultados.
- [ ] No promediar duplicados como observaciones independientes.
- [ ] Separar retrieval, generación, groundedness, seguridad numérica y abstención.
- [ ] Indicar categorías con N=1: cualquier media es solo el resultado de un caso.

## Muestra experta y concordancia

No se encontró tamaño de muestra, anotaciones expertas ni kappa.

- [ ] Definir muestra antes de observar resultados e informar N y composición por categoría.
- [ ] Publicar rúbrica y pares `score_experto`/`score_juez`.
- [ ] Calcular acuerdo porcentual y, según escala, kappa ponderado o Spearman con intervalo de confianza.
- [ ] No inventar tamaño, nombres, experiencia ni coeficiente.

## Multimodalidad

Texto recomendado:

> El prototipo conserva un corpus histórico derivado de documentos, imágenes y vídeos. El runtime actual no implementa ingesta ni almacenamiento de archivos nuevos. Retrieval, generación y evaluación operan sobre texto y embeddings ya persistidos; no demuestran razonamiento visual end-to-end.

- [ ] Si se desea reivindicar razonamiento multimodal, añadir un dataset con preguntas que dependan de tablas/imágenes, baseline textual, métricas y trazas del modelo visual.

## Reordenación de la memoria

- [ ] Actualizar la sección “Estructura de la memoria”.
- [ ] Orden recomendado:
  1. Introducción y objetivos.
  2. Estado del arte.
  3. Datos y metodología.
  4. Arquitectura y diseño.
  5. Implementación.
  6. Despliegue operativo del prototipo contenedorizado.
  7. Evaluación y resultados.
  8. Discusión, amenazas a la validez y fallos.
  9. Conclusiones y trabajo futuro.
- [ ] Mover despliegue, implementación y resultados antes de conclusiones.

## Bloqueos que requieren material externo

1. Fuente editable de la memoria para aplicar cambios de páginas/título/estructura.
2. Dataset declarado de 150 y registro de validación.
3. Ejecución reproducible sobre siete categorías.
4. Respuestas y chunks de dos fallos reales.
5. Anotaciones expertas pareadas para concordancia.
6. Versiones/digests de modelos y temperatura efectiva.
7. Evidencia de HNSW y de trazabilidad de página.

Hasta resolverlos, las afirmaciones deben limitarse al repositorio: monolito contenedorizado con corpus histórico, evaluación textual, dataset actual de 21 filas/19 preguntas únicas y resultados exploratorios no concluyentes.
