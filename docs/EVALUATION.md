# Evaluación: método y evidencia

## Tres familias que no deben mezclarse

### Métricas propias deterministas

El gateway implementa directamente:

- Recall@1 y Recall@K: presencia de al menos un chunk relevante en primera posición o top K;
- Precision@K: proporción de IDs recuperados que están anotados como relevantes;
- MRR: inverso del rango del primer relevante;
- nDCG@K: ganancia descontada con relevancia binaria;
- cobertura y MRR de keywords: coincidencia textual normalizada;
- falsos positivos para preguntas marcadas fuera de conocimiento;
- fallos y latencia total de retrieval.

Estas son funciones locales, no métricas RAGAS. La coincidencia por keywords es auxiliar y puede favorecer textos que repiten literalmente la referencia.

### LLM-as-a-Judge

`RAGService.evaluate_answer` solicita al mismo ecosistema de modelos una puntuación 1–5 de:

- `accuracy`;
- `completeness`;
- `relevance`.

Es LLM-as-a-Judge, no evaluación humana y no RAGAS. En la instantánea revisada, el prompt del juez incluye pregunta y respuesta generada, pero **no incorpora la respuesta de referencia ni el contexto recuperado**, aunque el método recibe `retrieved_docs`. Por ello no mide de forma fiable corrección contra referencia ni groundedness.

### RAGAS

`ragas>=0.4.3` está declarado en `gateway/pyproject.toml`, pero no se encontraron imports, configuración ni ejecuciones RAGAS en Python. No hay evidencia para atribuir Faithfulness, Context Precision, Context Recall o Answer Relevancy a RAGAS.

Estado correcto para la memoria:

> RAGAS está disponible como dependencia prevista, pero los resultados versionados proceden de métricas propias y de un LLM-as-a-Judge. No se presentan métricas RAGAS hasta integrar y ejecutar explícitamente la librería.

## Dataset versionado

Se revisaron tres copias:

- `gateway/routes/tests.jsonl`: un array JSON de 21 filas;
- `gateway/core/tests.jsonl`: 21 líneas JSONL;
- `src/evaluation/tests.jsonl`: 21 líneas JSONL del evaluador legado.

Las tres representan el mismo banco general. Hay 21 filas, pero solo 19 preguntas únicas por texto exacto: dos preguntas de `relationship` aparecen duplicadas una vez cada una. No existe evidencia versionada de 150 preguntas.

### Siete categorías actuales

| Categoría | Filas | Preguntas únicas | Ejemplo real abreviado |
|---|---:|---:|---|
| `direct_fact` | 6 | 6 | “¿Cuál es la ayuda por hectárea… para aguacates… POSEI?” |
| `temporal` | 4 | 4 | “¿Qué cambios normativos entraron en vigor… BCAM 8?” |
| `relationship` | 5 | 3 | “¿Qué módulo… está asociado al perfil de Alejandro Castro?” |
| `spanning` | 3 | 3 | “Si una cooperativa supera las 50 hectáreas de tomate…” |
| `regulatory_compliance` | 1 | 1 | “¿Qué requisitos… PAC… pimiento con frutales…?” |
| `regulatory_fact` | 1 | 1 | “¿Cuál es el volumen máximo de riego…?” |
| `traceability` | 1 | 1 | “¿En qué página y anexo… jóvenes agricultores?” |
| **Total** | **21** | **19** | |

Los ejemplos y respuestas son datos del banco, no hechos validados externamente. Varias referencias regulatorias carecen en el dataset de URL, documento, versión, página o chunk relevante. No deben describirse como “oficiales” o correctas sin validar contra la fuente primaria.

## Artefacto real disponible: run 9

`gateway/storage/evaluation_runs/run_9/comparative_results.csv` conserva cuatro filas, no 21 ni 150. Sus categorías son tres `general` y una vacía; todas tienen `failure=False`. Promedios calculados del CSV:

| Métrica del juez (1–5) | RAG | Sin RAG |
|---|---:|---:|
| Accuracy | 3.00 | 4.25 |
| Completeness | 3.20 | 4.00 |
| Relevance | 3.75 | 4.75 |

Estos valores son resultados reales del artefacto, pero **no permiten concluir que RAG sea peor o mejor** porque:

- solo hay cuatro filas y preguntas repetidas;
- no corresponden a las siete categorías del banco;
- no consta modelo/tag/digest, temperatura efectiva ni fingerprint recuperable en el CSV;
- el juez no recibió referencia ni contexto;
- no hay revisión humana ni intervalos de incertidumbre;
- el Markdown agregado copia MRR/Precision/nDCG en las columnas RAG y Vanilla aunque retrieval no aplica al modelo sin RAG.

No debe trasladarse esta tabla a resultados principales sin etiquetarla como ejecución exploratoria no concluyente.

## Tabla RAG frente a sin RAG para la memoria

No hay evidencia suficiente para completar la comparación principal sobre el banco de siete categorías. Use esta plantilla solo después de una nueva ejecución reproducible:

| Alcance | N | Modelo/digest | Temperatura efectiva | Métrica | Sin RAG | Con RAG | Diferencia | Evidencia |
|---|---:|---|---:|---|---:|---:|---:|---|
| **PENDIENTE** | — | — | — | Exactitud/groundedness | — | — | — | run y CSV |

No rellene guiones con los cuatro resultados de `run_9` como si fueran el experimento final.

## Resultados por siete categorías

No existe un artefacto versionado que contenga resultados de las siete categorías. La tabla de memoria debe permanecer pendiente:

| Categoría | N válido | Recall@10 | Precision@10 | MRR | nDCG@10 | Groundedness | Accuracy juez | Accuracy experta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `direct_fact` | 6 antes de curación | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `temporal` | 4 | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `relationship` | 3 únicas | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `spanning` | 3 | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `regulatory_compliance` | 1 | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `regulatory_fact` | 1 | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |
| `traceability` | 1 | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. | PEND. |

## Fallos holísticos

El feedback pide dos fallos con pregunta, chunks, respuesta y causa raíz. No pueden construirse con la evidencia actual:

- `run_9` no contiene el texto de chunks ni respuestas generadas;
- sus cuatro filas marcan `failure=False`;
- el banco contiene referencias, pero no salidas de una ejecución.

Ficha obligatoria para cada fallo real futuro:

1. ID de run, dataset y pregunta.
2. IDs, fuente, página y texto íntegro de los chunks recuperados con scores/rangos.
3. Respuesta generada y respuesta de referencia.
4. Resultado de métricas y revisión experta.
5. Causa raíz demostrada: recuperación, chunking/OCR, vigencia documental, reranking, prompt, generación o anotación.
6. Corrección y prueba de regresión.

## Validación humana y concordancia

No se encontró evidencia de:

- identidad/rol de quienes validaron “150 preguntas sintéticas”;
- protocolo de generación y revisión de referencias;
- tamaño de muestra experta;
- anotaciones individuales;
- acuerdo porcentual, kappa o Spearman.

No inventar nombres, tamaños ni coeficientes. Para calcular concordancia se necesita un fichero pareado por ítem con score experto y score automático, escala/rúbrica y tratamiento de desacuerdos. Use kappa ponderado para escalas ordinales, Spearman para orden/rango o acuerdo porcentual para etiquetas exactas; justifique la elección y publique N e intervalo de confianza.

## Protocolo mínimo recomendado

1. Curar duplicados y vincular cada referencia a fuente/chunk verificable.
2. Congelar `dev` y `holdout` con fingerprint.
3. Fijar modelo, digest/tag, temperatura efectiva y parámetros.
4. Desactivar/vaciar caché o registrar estado.
5. Ejecutar sin RAG y con RAG bajo el mismo protocolo.
6. Guardar detalle por pregunta, chunks, respuesta, referencia y latencias por fase.
7. Evaluar métricas propias y un juez grounded que reciba pregunta, referencia, respuesta y contexto.
8. Si se integra RAGAS, guardar configuración y columnas RAGAS separadas.
9. Revisar una muestra experta predefinida y calcular concordancia.
10. Informar por categoría y global, incluyendo N, fallos y limitaciones.
