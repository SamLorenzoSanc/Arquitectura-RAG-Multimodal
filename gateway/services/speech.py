from __future__ import annotations

from collections import deque

import numpy as np
import torch

from services.vad import VoiceActivityDetector
from services.whisper import WhisperEngine


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
