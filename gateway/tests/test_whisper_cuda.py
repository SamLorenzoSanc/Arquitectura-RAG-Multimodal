"""
Smoke test manual de Faster-Whisper + CUDA.

No forma parte de la suite por defecto (ver pyproject.toml --ignore).
Ejecutar solo cuando haya GPU y el fixture de audio:

    uv run pytest tests/test_whisper_cuda.py -m slow -s
"""

from __future__ import annotations

from pathlib import Path

import pytest

AUDIO_CANDIDATES = (
    Path(__file__).with_name("test_audio.mp3"),
    Path(__file__).with_name("test_audio.mp4"),
    Path(__file__).resolve().parent / "fixtures" / "test_audio.wav",
    Path(__file__).resolve().parent / "fixtures" / "test_audio.mp3",
)


def _resolve_audio() -> Path | None:
    for path in AUDIO_CANDIDATES:
        if path.exists():
            return path
    return None


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


pytestmark = pytest.mark.slow


@pytest.mark.skipif(not _cuda_available(), reason="CUDA no disponible")
@pytest.mark.skipif(
    _resolve_audio() is None,
    reason="Falta audio de prueba (tests/fixtures/test_audio.wav o test_audio.mp3 junto al script)",
)
def test_faster_whisper_cuda_transcription():
    from faster_whisper import WhisperModel

    audio_path = _resolve_audio()
    assert audio_path is not None

    model = WhisperModel(
        "large-v3",
        device="cuda",
        compute_type="float16",
    )

    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
    )

    assert info is not None
    # El fixture puede ser silencio; basta con que la API no falle.
    list(segments)
