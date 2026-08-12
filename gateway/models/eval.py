"""Módulo de métricas para los embeddings

Este módulo define la métricas utilizadas pra gestionar la evaluacion del arquitectura RAG
en el desarrollo de software
"""

from pydantic import Field
from .base import Base
from sqlalchemy import Column, String


class RetrievalEval(Base):
    """
    Modelo de datos para almacenar las métricas de evaluación del rendimiento de recuperación
    (Retrieval). Se utiliza generalmente en sistemas RAG (Retrieval-Augmented Generation) para medir
    qué tan bien el sistema encuentra los documentos o contextos correctos.
    """

    __tablename__ = "retrieval_evals"

    id = Column(String, primary_key=True, index=True)
    # MRR (Mean Reciprocal Rank): Evalúa la posición en la que aparece el primer resultado
    # relevante.
    mrr: float = Field(
        description="Rango recíproco medio: media de todas las palabras clave"
    )

    # NDCG (Normalized Discounted Cumulative Gain): Mide la calidad del ranking de los resultados
    # obtenidos.
    ndcg: float = Field(description="Ganancia acumulada descontada normalizada")

    # Contador de palabras clave que el sistema de recuperación logró encontrar
    # exitosamente.
    keywords_found: int = Field(
        description="Número de palabras clave encontradas exitosamente"
    )

    # Total de palabras clave esperadas o que el sistema debía buscar en total.
    total_keywords: int = Field(
        description="Número total de palabras clave que hay que buscar"
    )

    # Ratio o porcentaje que representa la cobertura (keywords_found / total_keywords).
    keyword_coverage: float = Field(
        description="Porcentaje de palabras clave encontradas"
    )


class AnswerEval(Base):
    """
    Modelo de datos para la evaluación de la calidad de la respuesta generada por un LLM.
    Diseñado específicamente para ser utilizado en un enfoque de 'LLM-as-a-judge' (LLM como juez),
    donde un modelo evalúa la respuesta final en base a distintos criterios.
    """

    __tablename__ = "answer_evals"

    id = Column(String, primary_key=True, index=True)
    # Retroalimentación cualitativa general. Justifica las puntuaciones que se darán a continuación.
    feedback: str = Field(
        description="Comentarios concisos sobre la calidad de la respuesta, comparándola con la respuesta de referencia y evaluándola en función del contexto obtenido"
    )

    # Métrica de exactitud fáctica: penaliza severamente las alucinaciones o datos incorrectos.
    accuracy: float = Field(
        description="¿En qué medida es correcta la respuesta desde el punto de vista fáctico en comparación con la respuesta de referencia? De 1 (incorrecta; cualquier respuesta incorrecta debe puntuar con un 1) a 5 (ideal: totalmente correcta). Una respuesta aceptable obtendría una puntuación de 3."
    )

    # Métrica de exhaustividad: asegura que no se omita ninguna parte de la pregunta original.
    completeness: float = Field(
        description="¿En qué medida aborda la respuesta todos los aspectos de la pregunta? De 1 (muy deficiente: falta información clave) a 5 (ideal: se proporciona toda la información de la respuesta de referencia de forma completa). Responde 5 solo si se incluye TODA la información de la respuesta de referencia."
    )

    # Métrica de relevancia: asegura que la respuesta sea directa y no incluya "relleno" o temas irrelevantes.
    relevance: float = Field(
        description="¿En qué medida es relevante la respuesta a la pregunta concreta que se ha formulado? De 1 (muy poco relevante —fuera de tema—) a 5 (ideal —responde directamente a la pregunta y no aporta información adicional—). Responde con un 5 solo si la respuesta es totalmente relevante para la pregunta y no aporta información adicional."
    )
