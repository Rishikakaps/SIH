from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock

ocr_lock = Lock()

@dataclass
class OcrResult:
    text: str
    confidence: float


def ocr_image_bytes(data: bytes, language: str = "en") -> OcrResult:
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not data:
        raise ValueError("The uploaded file is empty. Choose a PNG or JPEG image.")
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in {"PNG", "JPEG"}:
                raise ValueError("Only PNG and JPEG images are supported. Export PDF pages as images first.")
            if source.width * source.height > 20_000_000:
                raise ValueError("Image is too large. Resize it to under 20 megapixels.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("This file is not a readable PNG or JPEG image.") from exc
    try:
        import numpy as np
        with ocr_lock:
            results = _reader(language).readtext(np.array(image), detail=1, paragraph=False)
    except Exception as exc:
        raise RuntimeError("OCR is unavailable. Install backend requirements and run python setup_ocr.py with internet access to download the OCR models, then retry.") from exc
    lines, confidences = [], []
    for _bbox, text, confidence in results:
        cleaned = " ".join(str(text).split())
        if cleaned:
            lines.append(cleaned)
            confidences.append(float(confidence))
    if not lines:
        raise ValueError("No readable text found. Use a clear, upright photo of printed text with good lighting.")
    return OcrResult("\n".join(lines), round(sum(confidences) / len(confidences), 3))


@lru_cache(maxsize=2)
def _reader(language: str = "en"):
    import easyocr
    # English reports need the dedicated Latin recognizer for reliable numerals.
    model_dir = Path(os.environ.get("EASYOCR_MODEL_DIR", str(Path(__file__).resolve().parents[2] / ".ocr-models")))
    return easyocr.Reader(["hi", "en"] if language == "hi" else ["en"], gpu=False, verbose=False, model_storage_directory=str(model_dir), user_network_directory=str(model_dir / "user_network"))
