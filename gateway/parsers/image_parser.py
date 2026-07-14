from __future__ import annotations

import base64
import logging
from pathlib import Path

from openai import OpenAI

from .base import FileParser

logger = logging.getLogger(__name__)


class ImageParser(FileParser):
    """
    Convierte una imagen en Markdown utilizando un modelo de visión.

    Compatible con Ollama (LLaVA, Qwen2.5-VL, etc.)
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434/v1",
    ):

        self.model = model

        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama",
        )

    async def parse(self, file: Path) -> str:

        if not file.exists():
            raise FileNotFoundError(file)

        logger.info("Parsing image %s", file)

        with open(file, "rb") as f:
            image = base64.b64encode(f.read()).decode()

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": "system",
                    "content": """
                        Eres un parser documental.

                        Analiza la imagen y conviértela a Markdown.

                        Debes:

                        - conservar títulos
                        - conservar listas
                        - describir tablas
                        - describir diagramas
                        - describir gráficos
                        - extraer todo el texto visible
                        - utilizar encabezados Markdown
                        - no inventar información
                        """,
                                        },
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Convierte la imagen a Markdown.",
                                                },
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": f"data:image/png;base64,{image}"
                                                    },
                                                },
                                            ],
                                        },
                                    ],
                                )
        return response.choices[0].message.content