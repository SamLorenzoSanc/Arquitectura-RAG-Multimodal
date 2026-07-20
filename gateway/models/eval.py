import sys
import os
import math
import json
import urllib.request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .base import Base

class RetrievalEval(BaseModel):
    """Evaluation metrics for retrieval performance."""

    mrr: float = Field(description="Rango recíproco medio: media de todas las palabras clave")
    ndcg: float = Field(description="Ganancia acumulada descontada normalizada (relevancia binaria)")
    keywords_found: int = Field(description="Número total de palabras clave que hay que buscar")
    total_keywords: int = Field(description="Número total de palabras clave que hay que buscar")
    keyword_coverage: float = Field(description="Porcentaje de palabras clave encontradas")


class AnswerEval(BaseModel):
    """LLM-as-a-judge evaluation of answer quality."""

    feedback: str = Field(
        description="Comentarios concisos sobre la calidad de la respuesta, comparándola con la respuesta de referencia y evaluándola en función del contexto obtenido"
    )
    accuracy: float = Field(
        description="¿En qué medida es correcta la respuesta desde el punto de vista fáctico en comparación con la respuesta de referencia? De 1 (incorrecta; cualquier respuesta incorrecta debe puntuar con un 1) a 5 (ideal: totalmente correcta). Una respuesta aceptable obtendría una puntuación de 3."
    )
    completeness: float = Field(
        description="¿En qué medida aborda la respuesta todos los aspectos de la pregunta? De 1 (muy deficiente: falta información clave) a 5 (ideal: se proporciona toda la información de la respuesta de referencia de forma completa). Responde 5 solo si se incluye TODA la información de la respuesta de referencia."
    )
    relevance: float = Field(
        description="¿En qué medida es relevante la respuesta a la pregunta concreta que se ha formulado? De 1 (muy poco relevante —fuera de tema—) a 5 (ideal —responde directamente a la pregunta y no aporta información adicional—). Responde con un 5 solo si la respuesta es totalmente relevante para la pregunta y no aporta información adicional."
    )