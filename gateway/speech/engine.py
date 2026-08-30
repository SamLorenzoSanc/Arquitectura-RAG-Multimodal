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


from silero_vad import load_silero_vad
from silero_vad import get_speech_timestamps

import torch


class VoiceActivityDetector:

    def __init__(self):

        self.model = load_silero_vad()

    def detect(
        self,
        audio: torch.Tensor,
        sample_rate: int = 16000,
    ):

        timestamps = get_speech_timestamps(
            audio,
            self.model,
            sampling_rate=sample_rate,
        )

        return timestamps



from collections import deque

import numpy as np
import torch



class SpeechSession:

    SAMPLE_RATE = 16000

    def __init__(self):

        self.vad = VoiceActivityDetector()
        self.whisper = WhisperEngine()

        # últimos 5 segundos
        self.window = deque(maxlen=self.SAMPLE_RATE * 5)

        self.last_partial = ""

        self.silence_counter = 0

    def reset(self):

        self.window.clear()
        self.last_partial = ""
        self.silence_counter = 0

    def add_audio(
        self,
        pcm: bytes,
    ):

        audio = (
            np.frombuffer(
                pcm,
                dtype=np.int16,
            ).astype(np.float32)
            / 32768.0
        )

        self.window.extend(audio.tolist())

    def current_audio(self):

        return np.asarray(
            self.window,
            dtype=np.float32,
        )

    def detect_voice(self):

        audio = torch.from_numpy(self.current_audio())

        timestamps = self.vad.detect(audio)

        return len(timestamps) > 0

    def transcribe(self):

        audio = self.current_audio()

        return self.whisper.transcribe(audio).strip()

    async def process(self):

        # todavía no tenemos suficiente audio

        if len(self.window) < self.SAMPLE_RATE:

            return None

        speech = self.detect_voice()

        if speech:

            self.silence_counter = 0

            text = self.transcribe()

            if text and text != self.last_partial:

                self.last_partial = text

                return {
                    "type": "partial",
                    "text": text,
                }

            return None

        self.silence_counter += 1

        if self.silence_counter < 5:

            return None

        if self.last_partial:

            final = self.last_partial

            self.reset()

            return {
                "type": "final",
                "text": final,
            }

        return None


class SpeechService:

    def create_session(self):

        return SpeechSession()
