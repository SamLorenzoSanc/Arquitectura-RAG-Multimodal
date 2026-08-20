from unittest.mock import MagicMock
import sys

import pytest

from services.pdf_extract import (
    corpus_looks_corrupted,
    extract_pdf_text,
    is_readable_text,
    looks_like_pdf_internals,
)


pytestmark = pytest.mark.unit

READABLE = (
    "Resolución del segundo pago de la subvención POSEI 2025 publicada "
    "en el Boletín Oficial de Canarias para platanera."
)


def test_is_readable_spanish_official_text():
    assert is_readable_text(READABLE)


def test_rejects_tofu_and_private_use():
    assert not is_readable_text("\ufffd" * 80)
    assert not is_readable_text("\ue000" * 60 + "abc")


def test_rejects_pdf_internal_streams():
    blob = "/Type /Font /Subtype /Type1 /FontName /AAAAAA /Length 1200 endobj stream xref"
    assert looks_like_pdf_internals(blob)
    assert not is_readable_text(blob)


def test_corpus_looks_corrupted_on_majority_junk():
    assert corpus_looks_corrupted(["\ufffd" * 80, "\ufffd" * 90, READABLE])
    assert not corpus_looks_corrupted([READABLE, READABLE, READABLE])


class _FakeTextPage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text_bounded(self) -> str:
        return self._text

    def close(self) -> None:
        return None


class _FakeBitmap:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def to_pil(self) -> str:
        return self.payload

    def close(self) -> None:
        return None


class _FakePage:
    def __init__(self, native: str, ocr: str) -> None:
        self._native = native
        self._ocr = ocr

    def get_textpage(self) -> _FakeTextPage:
        return _FakeTextPage(self._native)

    def render(self, scale: float = 2.0) -> _FakeBitmap:
        assert scale > 0
        return _FakeBitmap(self._ocr)

    def close(self) -> None:
        return None


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self._pages = pages

    def __len__(self) -> int:
        return len(self._pages)

    def __getitem__(self, index: int) -> _FakePage:
        return self._pages[index]

    def close(self) -> None:
        return None


def test_extract_pdf_uses_ocr_when_native_is_junk(monkeypatch):
    from services import pdf_extract as mod

    junk = "\ufffd" * 90
    pdf = _FakePdf([_FakePage(junk, READABLE)])
    fake_pdfium = MagicMock()
    fake_pdfium.PdfDocument.side_effect = lambda _content: pdf
    monkeypatch.setitem(sys.modules, "pypdfium2", fake_pdfium)
    monkeypatch.setattr(mod, "ocr_image", lambda image: image)
    text = extract_pdf_text(b"%PDF-junk", use_ocr=True)
    assert "POSEI" in text
    assert "\ufffd" not in text


def test_extract_pdf_keeps_native_when_readable(monkeypatch):
    from services import pdf_extract as mod

    pdf = _FakePdf([_FakePage(READABLE, "OCR no debería usarse")])
    fake_pdfium = MagicMock()
    fake_pdfium.PdfDocument.side_effect = lambda _content: pdf
    monkeypatch.setitem(sys.modules, "pypdfium2", fake_pdfium)
    monkeypatch.setattr(
        mod,
        "ocr_image",
        lambda _image: pytest.fail("OCR innecesario en página nativa legible"),
    )
    text = extract_pdf_text(b"%PDF-ok", use_ocr=True)
    assert "POSEI" in text
