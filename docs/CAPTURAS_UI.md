# Guion de capturas UI — AgroPS (TFM)

Capturar con ventana a **1280×800** o más, tema claro, idioma **ES**, sin datos personales reales.
Guardar en `docs/memoria-latex/figures/` con los nombres de la columna **Archivo**.

## Orden recomendado para la memoria / defensa

| # | Vista | URL / cómo llegar | Qué debe verse | Archivo | Pie de figura (propuesta) |
|---|--------|-------------------|----------------|---------|---------------------------|
| 1 | Landing | `/` | Hero AgroPS, CTAs | `ui-landing.png` | Página de inicio pública del prototipo. |
| 2 | Login | `/login` | Formulario email/contraseña | `ui-login.png` | Acceso autenticado al panel. |
| 3 | Panel | `/dashboard` | Resumen / actividad | `ui-dashboard.png` | Panel de inicio tras autenticación. |
| 4 | Documentos | `/dashboard/documentos` | Lista + subir PDF | `ui-documentos.png` | Catálogo documental e indexación. |
| 5 | Chat / Agentic | chat (panel o widget) | Pregunta, respuesta, fuentes, catálogo de tools | `ui-chat.png` | Asistente RAG con citas y tools. |
| 6 | Tools usadas | misma vista tras una pregunta | Marcas verdes / traza | `ui-chat-tools.png` | Herramientas disponibles y usadas en la respuesta. |
| 7 | Flujo RAG | `/dashboard/flujo-rag` | Grafo del pipeline | `ui-flujo-rag.png` | Visualización del pipeline de recuperación. |
| 8 | Embeddings 3D | `/dashboard/embeddings` | Nube UMAP | `ui-embeddings.png` | Visualización de embeddings (no GraphRAG). |
| 9 | Organización | `/dashboard/organization` | Orgs / departamentos | `ui-organizacion.png` | Gestión multi-organización. |
| 10 | Evaluación | `/dashboard/evaluacion` | Lab / banco | `ui-evaluacion.png` | Laboratorio de evaluación del prototipo. |
| 11 | Validación HITL | `/dashboard/validacion` | Cola humana | `ui-validacion.png` | Validación humana de respuestas. |
| 12 | Cuaderno (si expuesto) | ruta del cuaderno | Calendario / entradas | `ui-cuaderno.png` | Cuaderno de campo operativo. |
| 13 | Ajustes / i18n | `/dashboard/settings` | Perfil + idioma | `ui-ajustes.png` | Ajustes e internacionalización. |
| 14 | Docs ayuda | `/dashboard/docs` | Guía / API | `ui-ayuda.png` | Documentación de uso del MVP. |

## Tips de captura (Windows)

1. Arranca la app: `http://localhost` (Compose) o `http://localhost:5173` (Vite).
2. Win+Shift+S o herramienta de captura; preferible **ventana completa** del navegador.
3. Oculta pestañas personales y notificaciones.
4. Usa datos de demostración (corpus PAC/POSEI, org AgroTech).
5. Para el chat: una pregunta concreta tipo «¿Qué es el POSEI?» con fuentes visibles.

## Mínimo viable para tribunal (si no da tiempo a las 14)

Prioridad **alta**: 4 Documentos, 5 Chat, 9 Organización, 10 Evaluación, 7 Flujo RAG.  
Prioridad **media**: 3 Dashboard, 6 Tools, 8 Embeddings, 11 HITL.  
Prioridad **baja**: landing, login, ajustes, ayuda.

## Capturas de código / OCR (preprocesamiento)

| # | Contenido | Archivo | Pie propuesto |
|---|-----------|---------|---------------|
| C1 | Flujo OCR selectivo + patrones | `diagrama-ocr-selectivo.png` | OCR selectivo: texto nativo con pypdfium2 y RapidOCR solo en páginas ilegibles. |
| C2 | Decisión nativo vs OCR | `captura-codigo-ocr-decision.png` | Bucle por página: si `is_readable_text` falla, se rasteriza y aplica RapidOCR. |
| C3 | Motor RapidOCR | `captura-codigo-rapidocr.png` | Inicialización perezosa de RapidOCR y OCR sobre la página renderizada. |
| C4 | Heurística de legibilidad | `captura-codigo-is-readable.png` | Filtros anti-basura (CID, Unicode, ratio latino) antes de indexar. |
| C5 | Pipeline completo preproceso | `diagrama-preprocesamiento-docs.png` | Almacenamiento → extracción → limpieza → chunking 1400/120 → indexación → caché. |
| C6 | Orquestación HybridRetrieve | `captura-codigo-retrieval-hibrido.png` | Núcleo de `execute`: denso∥BM25 → RRF → top-$k$ (Alg. 2). |
| C6b | Clase HybridRetrieve (puertos) | `captura-codigo-hybrid-retrieve-class.png` | Caso de uso hexagonal con `ChunkRepository` y `LexicalIndexPort`. |
| C7 | Fórmula RRF en código | `captura-codigo-rrf-fusion.png` | `score += 1/(k_rrf + rank)` sobre cada ranking. |
| C8 | Paralelismo denso+BM25 | `captura-codigo-parallel-pair.png` | `asyncio.gather` de pgvector y BM25. |

Regenerar:

```powershell
python docs/memoria-latex/figures/compose_capturas_ocr_codigo.py
python docs/memoria-latex/figures/compose_diagrama_preprocesamiento.py
python docs/memoria-latex/figures/compose_capturas_retrieval_codigo.py
```

## Captura UI del retrieval (opcional)

| Vista | Cómo | Archivo sugerido |
|-------|------|------------------|
| Flujo RAG en vivo | Chat → pregunta → panel «Flujo RAG» / `/dashboard/flujo-rag` con nodo retrieve activo | `ui-retrieval-flujo.png` |
| Lab retrieval | `/dashboard/lab-retrieval` tras una sonda | `ui-retrieval-lab.png` |

## Inclusión en LaTeX

En `chapters/05_implementacion.tex`, sección «Capturas del prototipo AgroPS»,
añadir un `\begin{figure}...\end{figure}` por cada PNG (mismo patrón que
`fig:ui-docs` / `fig:ui-chat`).
