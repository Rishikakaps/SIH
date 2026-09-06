from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass
class OcrResult:
    text: str
    confidence: float


def ocr_image_bytes(data: bytes) -> OcrResult:
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError("EasyOCR is not installed. Install backend OCR requirements before running document upload.") from exc

    suffix = ".png"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        results = _reader(easyocr).readtext(str(tmp_path), detail=1, paragraph=False)
    finally:
        tmp_path.unlink(missing_ok=True)

    lines: list[str] = []
    confidences: list[float] = []
    for _bbox, text, confidence in results:
        cleaned = " ".join(str(text).split())
        if cleaned:
            lines.append(cleaned)
            confidences.append(float(confidence))
    score = sum(confidences) / len(confidences) if confidences else 0.0
    return OcrResult(text="\n".join(lines), confidence=round(score, 3))


@lru_cache(maxsize=1)
def _reader(easyocr_module):
    return easyocr_module.Reader(["en"], gpu=False, verbose=False)
