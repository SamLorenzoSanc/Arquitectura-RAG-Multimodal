# Memoria TFM (LaTeX / Overleaf)

Proyecto listo para subir a [Overleaf](https://www.overleaf.com/).

**Título canónico (portada y encabezados):**  
*Impacto de la Arquitectura RAG en las Alucinaciones de los LLMs*

## Contenido

| Archivo | Descripción |
|---|---|
| `main.tex` | Documento raíz |
| `chapters/` | Capítulos (orden: intro → … → implementación → despliegue → evaluación → conclusiones) |
| `figures/` | Carpeta para capturas (añadir y referenciar con `\includegraphics`) |

## Correcciones del tutor ya aplicadas en esta versión

1. Título unificado (incluye «de los LLMs»).
2. Sin comentarios Word / recuadros grises (proyecto nuevo LaTeX).
3. «Memoria Paramétrica» en sustituciones automáticas.
4. Tabla 1 renombrada a comparación de arquitecturas y enfoques NLP (vía reemplazo de leyenda).
5. Tabla de configuración experimental (`tab:config`).
6. Cuadro de siete categorías con N del banco versionado 21/19.
7. Texto honesto sobre validación de las «150» (evidencia pendiente).
8. Plantilla LLM sin RAG vs con RAG (pendiente de corrida reproducible).
9. Separación clara: métricas propias / LLM-as-a-Judge / RAGAS+`is_hallucination`.
10. Plantilla de dos fallos holísticos (pendiente de trazas).
11. Resultados por categoría (pendiente).
12. Concordancia experto–juez (pendiente).
13. Multimodal matizado (evaluación textual).
14. «elimina/erradica» → «mitiga … en los casos evaluados».
15. «entorno productivo real» → «prototipo funcional contenedorizado».
16. Despliegue e implementación **antes** de conclusiones; estructura actualizada.

## Subir a Overleaf

1. Comprime la carpeta `memoria-latex` (debe quedar `main.tex` en la raíz del zip).
2. Overleaf → *New Project* → *Upload Project*.
3. Compilador: **pdfLaTeX** (o XeLaTeX si prefieres fuentes del sistema).
4. Si faltan paquetes, usa la distribución TeX Live completa de Overleaf.

### PowerShell (desde la raíz del repo)

```powershell
Compress-Archive -Path "docs\memoria-latex\*" -DestinationPath "docs\TFM_Overleaf.zip" -Force
```

## Compilación local

En Windows **no suele haber** `pdflatex` instalado. Opciones:

### A) Overleaf (recomendado)

Sube `docs/TFM_Overleaf.zip` → *New Project* → *Upload Project*.

### B) Docker (sin instalar MiKTeX)

Desde PowerShell, en `docs/memoria-latex`:

```powershell
docker run --rm -v "${PWD}:/work" -w /work texlive/texlive:latest pdflatex -interaction=nonstopmode main.tex
docker run --rm -v "${PWD}:/work" -w /work texlive/texlive:latest pdflatex -interaction=nonstopmode main.tex
```

El PDF queda en `docs/memoria-latex/main.pdf`.

### C) MiKTeX / TeX Live en el PC

Instala [MiKTeX](https://miktex.org/) o TeX Live y vuelve a abrir la terminal; entonces sí existirá `pdflatex`.

## Honestidad de resultados

Las cifras globales antiguas del Word (p. ej. MRR 0,7911) pueden seguir apareciendo en texto migrado del capítulo 5; las **tablas principales nuevas** están marcadas como PEND. hasta una ejecución versionada. Antes de entregar al tribunal, conviene:

1. Ejecutar evaluación sobre las 7 categorías.
2. Sustituir PEND. por números y adjuntar CSV/run id.
3. Añadir 2 fallos holísticos con chunks reales.
4. Documentar validación experta si se reclama N=150.

## Figuras

Copia capturas a `figures/` (Chat, Documentos RAG, Compose, Evaluación) y referencia, por ejemplo:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.9\textwidth]{figures/chat-rag.png}
  \caption{Asistente RAG con citas al corpus documental.}
\end{figure}
```
