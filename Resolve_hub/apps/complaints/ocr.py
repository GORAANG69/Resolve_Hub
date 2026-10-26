from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def extract_text_from_file(file_obj, filename: str) -> Tuple[str, bool]:
    """
    Extract text from an uploaded scanned document (image or PDF).
    Returns (extracted_text, is_ocr_success).
    Gracefully degrades if pytesseract, Pillow, pdf2image, or the system Tesseract binary is unavailable.
    """
    ext = Path(filename).suffix.lower()

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return (
            "OCR processor note: pytesseract or Pillow library not installed. Document queued for manual optical transcription.",
            False,
        )

    try:
        file_obj.seek(0)
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            image = Image.open(file_obj)
            text = pytesseract.image_to_string(image, lang="eng+hin")
            if text and text.strip():
                return text.strip(), True
            return "OCR notice: Image processed but no readable text detected.", False

        elif ext == ".pdf":
            try:
                from pdf2image import convert_from_bytes
                file_obj.seek(0)
                images = convert_from_bytes(file_obj.read(), first_page=1, last_page=3)
                combined_text = []
                for img in images:
                    t = pytesseract.image_to_string(img, lang="eng+hin")
                    if t.strip():
                        combined_text.append(t.strip())
                if combined_text:
                    return "\n\n".join(combined_text), True
                return "OCR notice: PDF pages converted, but no text detected.", False
            except Exception as pdf_err:
                logger.info("PDF OCR fallback: %s", pdf_err)
                return (
                    f"OCR notice: PDF optical scanning requires poppler and pdf2image ({pdf_err}). Document saved for manual transcription.",
                    False,
                )

        return "Unsupported file format for OCR.", False

    except Exception as exc:
        logger.warning("OCR scanning error: %s", exc)
        return (
            f"OCR notice: Optical recognition system encountered an error ({type(exc).__name__}). Document saved as attachment for manual review.",
            False,
        )
