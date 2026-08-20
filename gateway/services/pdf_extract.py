"""Extracción de texto PDF: nativo por página y OCR (RapidOCR) si el texto es basura.

Los BOC/resoluciones canarias suelen usar fuentes CID sin mapa ToUnicode.
pypdfium2 entonces devuelve tofu o un mapeo ilegible; el fallback latin-1
anterior indexaba streams internos del PDF. Aquí se descarta ese fallback
y se rasteriza solo las páginas ilegibles.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any

logger = logging.getLogger(__name__)

_LATIN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]")
_JUNK_RE = re.compile(r"[\ufffd\ue000-\uf8ff\uf000-\uf0ff]")
_PDF_INTERNAL_RE = re.compile(
    r"(/Type\s*/|/Length\s|endobj|endstream|\bxref\b|startxref|/FontName|/Subtype\s*/)",
    re.IGNORECASE,
)

_ENGINE: Any = None
_ENGINE_FAILED = False
_ENGINE_LOCK = threading.Lock()


def _ocr_enabled() -> bool:
    return os.getenv("RAG_PDF_OCR", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _ocr_scale() -> float:
    try:
        return min(3.0, max(1.25, float(os.getenv("RAG_PDF_OCR_SCALE", "2"))))
    except ValueError:
        return 2.0


def latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_LATIN_RE.findall(text)) / max(len(text), 1)


def junk_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_JUNK_RE.findall(text)) / max(len(text), 1)


def looks_like_pdf_internals(text: str) -> bool:
    return len(_PDF_INTERNAL_RE.findall(text or "")) >= 3


def is_readable_text(text: str, *, min_chars: int = 24) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < min_chars:
        return False
    if looks_like_pdf_internals(stripped):
        return False
    if junk_ratio(stripped) >= 0.08:
        return False
    if latin_ratio(stripped) < 0.28:
        return False
    vowels = len(re.findall(r"[aeiouáéíóúAEIOUÁÉÍÓÚ]", stripped))
    if vowels / max(len(stripped), 1) < 0.035 and latin_ratio(stripped) < 0.55:
        return False
    return True


def corpus_looks_corrupted(texts: list[str]) -> bool:
    samples = [item or "" for item in texts]
    if not samples:
        return True
    pdfish = sum(1 for item in samples if looks_like_pdf_internals(item))
    unreadable = sum(
        1 for item in samples if not is_readable_text(item, min_chars=40)
    )
    return pdfish >= 2 or unreadable * 2 >= len(samples)


def _get_engine() -> Any:
    global _ENGINE, _ENGINE_FAILED
    if _ENGINE_FAILED:
        return None
    if _ENGINE is not None:
        return _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE_FAILED:
            return None
        if _ENGINE is not None:
            return _ENGINE
        try:
            from rapidocr import RapidOCR

            _ENGINE = RapidOCR()
        except Exception:
            logger.exception("RapidOCR no está disponible; se omite el OCR de PDF")
            _ENGINE_FAILED = True
            return None
    return _ENGINE


def ocr_image(image: Any) -> str:
    engine = _get_engine()
    if engine is None:
        return ""
    try:
        import numpy as np

        array = image
        if hasattr(image, "convert"):
            array = np.asarray(image.convert("RGB"))
        result = engine(array, use_cls=False)
    except Exception:
        logger.exception("Falló RapidOCR sobre una página rasterizada")
        return ""
    if result is None:
        return ""
    txts = getattr(result, "txts", None)
    if txts:
        return "\n".join(str(item).strip() for item in txts if item and str(item).strip())
    if isinstance(result, tuple) and result:
        first = result[0]
        if first is None:
            return ""
        lines: list[str] = []
        for item in first:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                lines.append(str(item[1]).strip())
        return "\n".join(line for line in lines if line)
    return str(result).strip()


def _native_page_text(page: Any) -> str:
    textpage = page.get_textpage()
    try:
        raw = textpage.get_text_bounded() or ""
        if not str(raw).strip() and hasattr(textpage, "get_text_range"):
            raw = textpage.get_text_range() or ""
        return str(raw)
    finally:
        close = getattr(textpage, "close", None)
        if callable(close):
            close()


def _ocr_page(page: Any, scale: float) -> str:
    render = getattr(page, "render", None)
    if not callable(render):
        return ""
    bitmap = render(scale=scale)
    try:
        image = bitmap.to_pil() if hasattr(bitmap, "to_pil") else bitmap
        return ocr_image(image)
    finally:
        close = getattr(bitmap, "close", None)
        if callable(close):
            close()


def extract_pdf_text(
    content: bytes,
    *,
    max_pages: int = 120,
    max_chars: int = 400_000,
    use_ocr: bool | None = None,
) -> str:
    if not content:
        return ""
    ocr = _ocr_enabled() if use_ocr is None else bool(use_ocr)
    scale = _ocr_scale()
    parts: list[str] = []
    ocr_pages = 0
    native_pages = 0
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(content)
    except Exception:
        logger.exception("No se pudo abrir el PDF con pypdfium2")
        return ""
    try:
        total = len(pdf)
        limit = total if max_pages <= 0 else min(total, max_pages)
        for index in range(limit):
            page = pdf[index]
            try:
                native = _native_page_text(page)
                chosen = native
                if ocr and not is_readable_text(native, min_chars=24):
                    scanned = _ocr_page(page, scale)
                    if is_readable_text(scanned, min_chars=12) or (
                        scanned.strip() and latin_ratio(scanned) > latin_ratio(native)
                    ):
                        chosen = scanned
                        ocr_pages += 1
                    elif is_readable_text(native, min_chars=12):
                        native_pages += 1
                    else:
                        continue
                elif is_readable_text(native, min_chars=12):
                    native_pages += 1
                else:
                    continue
                stripped = chosen.strip()
                if stripped:
                    parts.append(stripped)
            finally:
                close = getattr(page, "close", None)
                if callable(close):
                    close()
    finally:
        close = getattr(pdf, "close", None)
        if callable(close):
            close()

    text = "\n\n".join(parts).strip()
    if ocr_pages or native_pages:
        logger.info(
            "PDF extraído: %s páginas nativas, %s con OCR, %s caracteres",
            native_pages,
            ocr_pages,
            len(text),
        )
    return text[:max_chars]
