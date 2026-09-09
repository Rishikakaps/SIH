"""Download/cache Hindi and English OCR models before starting the app."""
from app.documents.ocr_engine import _reader

if __name__ == "__main__":
    print("Preparing Hindi + English OCR models. First download may take several minutes.")
    _reader()
    _reader("hi")
    print("OCR models are ready. You may now start the backend.")
