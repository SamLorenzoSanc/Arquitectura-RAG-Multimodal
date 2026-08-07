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
