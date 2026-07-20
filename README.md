# 🌾 Asistente Inteligente RAG Multimodal para el Sector Agrícola

> Trabajo Fin de Máster (TFM)
>
> **Impacto de la Arquitectura Retrieval-Augmented Generation (RAG) Multimodal en la reducción de alucinaciones de los Large Language Models para el asesoramiento técnico y administrativo del sector agrícola.**

---

# 📖 Descripción

Este proyecto desarrolla un asistente inteligente basado en arquitecturas **Retrieval-Augmented Generation (RAG)** capaz de consultar documentación técnica y normativa del sector agrícola, especialmente relacionada con la **Política Agraria Común (PAC)** y el **Programa POSEI**.

El objetivo principal consiste en reducir las alucinaciones propias de los Large Language Models (LLM) mediante la recuperación de información procedente exclusivamente de documentación oficial.

El sistema incorpora capacidades multimodales para procesar:

- Documentos PDF
- Tablas
- Imágenes
- Diagramas técnicos
- Normativa administrativa

Todo ello ejecutándose completamente en entorno local para garantizar la privacidad de la información.

---

# 🎯 Objetivos

- Reducir la generación de respuestas alucinadas.
- Mejorar la precisión de las respuestas.
- Incorporar trazabilidad documental.
- Citar automáticamente documento y página.
- Procesar PDFs complejos con tablas e imágenes.
- Ejecutar completamente en local mediante Ollama.
- Evaluar el rendimiento utilizando RAGAS.

---

# 🏗 Arquitectura

```
                Usuario
                    │
                    ▼
           Consulta en lenguaje natural
                    │
                    ▼
              Embedding Query
                    │
                    ▼
         Base de Datos Vectorial
                    │
      Recuperación Top-K documentos
                    │
                    ▼
              Prompt Contextual
                    │
                    ▼
              Modelo LLM (Ollama)
                    │
                    ▼
          Respuesta + Fuente + Página
```

---

# 🚀 Tecnologías utilizadas

| Tecnología | Uso |
|------------|-----|
| Python | Desarrollo |
| LangChain | Orquestación |
| Ollama | Inferencia local |
| LlamaIndex | Indexación documental |
| ChromaDB / Qdrant | Base de datos vectorial |
| PyMuPDF | Extracción de PDFs |
| pdfplumber | Procesamiento documental |
| SentenceTransformers | Embeddings |
| RAGAS | Evaluación |
| Docker | Contenedores |

---

# 📂 Estructura del proyecto

```
Proyecto/

│
├── data/
│     ├── pdf/
│     ├── images/
│     └── embeddings/
│
├── src/
│     ├── ingest.py
│     ├── rag.py
│     ├── prompts.py
│     ├── embeddings.py
│     ├── retriever.py
│     ├── parser.py
│     └── evaluation.py
│
├── database/
│
├── models/
│
├── docker/
│
├── tests/
│
├── requirements.txt
│
├── docker-compose.yml
│
└── README.md
```

---

# ⚙ Instalación

## Clonar el repositorio

```bash
git clone https://github.com/USUARIO/NOMBRE_REPOSITORIO.git

cd NOMBRE_REPOSITORIO
```

---

## Crear entorno virtual

```bash
python -m venv venv
```

Windows

```bash
venv\Scripts\activate
```

Linux

```bash
source venv/bin/activate
```

---

## Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# 🐳 Docker

Construcción

```bash
docker-compose build
```

Inicio

```bash
docker-compose up
```

---

# 🤖 Instalación de Ollama

Instalar Ollama

https://ollama.com

Descargar un modelo

```bash
ollama pull llama3
```

o

```bash
ollama pull mistral
```

Comprobar funcionamiento

```bash
ollama run llama3
```

---

# 📄 Procesamiento documental

El sistema realiza automáticamente:

- Extracción del texto.
- Detección de tablas.
- Procesamiento de imágenes.
- Fragmentación (Chunking).
- Creación de Embeddings.
- Indexación vectorial.

---

# 🔍 Flujo RAG

1. Usuario realiza una pregunta.

2. La pregunta se transforma en embedding.

3. Se buscan los documentos más similares.

4. Se recuperan los fragmentos.

5. Se construye el prompt.

6. El LLM genera la respuesta.

7. Se devuelve:

- Respuesta
- Documento
- Página
- Fuente

---

# 📊 Evaluación

El proyecto utiliza RAGAS para medir:

- Faithfulness
- Context Precision
- Context Recall
- Answer Relevancy

También se realiza evaluación humana mediante juicio de expertos.

---

# 📈 Resultados esperados

- Reducción significativa de alucinaciones.
- Mayor precisión documental.
- Respuestas justificadas.
- Trazabilidad completa.
- Recuperación multimodal.

---

# 📚 Documentación utilizada

- Reglamentos PAC
- Reglamentos POSEI
- Manuales oficiales
- Guías técnicas agrícolas
- Documentación administrativa

---

# 🔒 Privacidad

Todo el procesamiento puede ejecutarse completamente en local.

No es necesario enviar información a servicios externos.

Compatible con:

- GDPR
- Ley Europea de IA
- Entornos On-Premise

---

# 👨‍💻 Autor

**Samuel Lorenzo Sánchez**

Trabajo Fin de Máster

Máster en Inteligencia Artificial

---

# 📜 Licencia

Este proyecto ha sido desarrollado con fines académicos como parte del Trabajo Fin de Máster.

Su reutilización deberá respetar la normativa de propiedad intelectual de la universidad correspondiente.

---

# 🙏 Agradecimientos

A los profesores, tutores y profesionales del sector agrícola que han contribuido al desarrollo de este proyecto, así como a la comunidad de software libre y de inteligencia artificial por las herramientas y recursos empleados durante la investigación.

---

# 📧 Contacto

Para cualquier consulta relacionada con este proyecto:

**Samuel Lorenzo Sánchez**

GitHub: https://github.com/TU_USUARIO

Correo electrónico: TU_EMAIL
