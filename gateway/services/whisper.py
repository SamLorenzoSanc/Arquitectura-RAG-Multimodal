from __future__ import annotations

import numpy as np
import torch
import whisper


class WhisperEngine:

    def __init__(self, model_name: str = "base"):
        # Selecciona automáticamente GPU si está disponible, sino CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Cargando modelo Whisper ({model_name}) en dispositivo: {self.device}")

        self.model = whisper.load_model(model_name, device=self.device)

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Recibe un array numpy de float32 normalizado a 16kHz y devuelve la transcripción de texto.
        """
        if audio.size == 0:
            return ""

        # Whisper acepta directamente arrays numpy en float32
        result = self.model.transcribe(
            audio,
            language="es",
            fp16=(self.device == "cuda"),
            without_timestamps=True,
            task="transcribe",
        )

        return result.get("text", "").strip()
