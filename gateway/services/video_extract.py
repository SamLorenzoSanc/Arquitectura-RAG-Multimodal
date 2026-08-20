"""Transcripción de vídeo y audio para indexar el habla en el RAG."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEO_SUFFIXES = {
    ".mp4",
    ".webm",
    ".mov",
    ".mkv",
    ".avi",
    ".mpeg",
    ".mpg",
    ".m4v",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
}

MAX_UPLOAD_BYTES = 100 * 1024 * 1024

_MODEL = None
_MODEL_KEY: tuple[str, str, str] | None = None


def is_video_file(filename: str | None, mime_type: str | None = None) -> bool:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    suffix = Path(name).suffix
    return (
        suffix in VIDEO_SUFFIXES
        or mime.startswith("video/")
        or mime.startswith("audio/")
    )


def _whisper_model():
    global _MODEL, _MODEL_KEY
    name = os.getenv("RAG_WHISPER_MODEL", "tiny").strip() or "tiny"
    device = os.getenv("RAG_WHISPER_DEVICE", "cpu").strip() or "cpu"
    default_compute = "int8" if device == "cpu" else "float16"
    compute = os.getenv("RAG_WHISPER_COMPUTE", default_compute).strip() or default_compute
    key = (name, device, compute)
    if _MODEL is None or _MODEL_KEY != key:
        from faster_whisper import WhisperModel

        logger.info("Cargando Whisper %s (%s/%s)", name, device, compute)
        _MODEL = WhisperModel(name, device=device, compute_type=compute)
        _MODEL_KEY = key
    return _MODEL


def transcribe_video_segments(content: bytes, filename: str) -> list[str]:
    """Devuelve fragmentos de habla con marca de tiempo. Requiere ffmpeg."""
    suffix = Path(filename or "").suffix.lower() or ".mp4"
    handle, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(handle, content)
        os.close(handle)
        language = os.getenv("RAG_WHISPER_LANGUAGE", "es").strip()
        kwargs: dict = {"beam_size": 1, "vad_filter": True}
        if language:
            kwargs["language"] = language
        try:
            segments, _info = _whisper_model().transcribe(path, **kwargs)
        except Exception as exc:
            raise ValueError(
                "No se pudo transcribir el vídeo. Comprueba que ffmpeg está "
                f"instalado y que el archivo no esté corrupto: {exc}"
            ) from exc
        parts: list[str] = []
        for segment in segments:
            text = (getattr(segment, "text", None) or "").strip()
            if not text:
                continue
            start = getattr(segment, "start", None)
            end = getattr(segment, "end", None)
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                parts.append(f"[{start:.1f}s–{end:.1f}s] {text}")
            else:
                parts.append(text)
        if not parts:
            raise ValueError(
                "El vídeo no contiene habla transcribible. "
                "Prueba con un archivo que tenga voz o sube la transcripción en texto."
            )
        return parts
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def transcribe_video_text(
    content: bytes, filename: str, max_chars: int = 400_000
) -> str:
    text = "\n".join(transcribe_video_segments(content, filename)).strip()
    return text[:max_chars]
