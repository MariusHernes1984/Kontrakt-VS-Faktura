"""PDF tekstekstraksjon med OCR-fallback for skannede PDF-er."""
import logging
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

# Hvis vi får mindre enn dette antall tegn fra PyPDF2, antar vi at PDF-en
# er skannet/bildebasert og faller tilbake til OCR.
MIN_TEKST_TERSKEL = 100


def _ekstraher_med_pypdf2(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        tekst = ""
        for page in reader.pages:
            tekst += (page.extract_text() or "") + "\n"
        return tekst.strip()
    except Exception as e:
        logger.warning(f"PyPDF2 feilet: {e}")
        return ""


def _ekstraher_med_ocr(pdf_path: str) -> str:
    """OCR-fallback. Krever pytesseract + pdf2image + tesseract installert."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        logger.error(f"OCR-bibliotek mangler: {e}")
        return ""

    try:
        bilder = convert_from_path(pdf_path, dpi=200)
        tekst_deler = []
        for bilde in bilder:
            tekst_deler.append(
                pytesseract.image_to_string(bilde, lang="nor+eng")
            )
        return "\n".join(tekst_deler).strip()
    except Exception as e:
        logger.error(f"OCR feilet: {e}")
        return ""


def ekstraher_tekst(pdf_path: str):
    """Returnerer (tekst, brukte_ocr).

    Prøver PyPDF2 først. Hvis resultatet er for kort, faller vi tilbake til OCR.
    """
    tekst = _ekstraher_med_pypdf2(pdf_path)
    brukte_ocr = False

    if len(tekst) < MIN_TEKST_TERSKEL:
        logger.info(
            f"PyPDF2 returnerte {len(tekst)} tegn (< {MIN_TEKST_TERSKEL}). Forsøker OCR..."
        )
        ocr_tekst = _ekstraher_med_ocr(pdf_path)
        if len(ocr_tekst) > len(tekst):
            tekst = ocr_tekst
            brukte_ocr = True

    return tekst, brukte_ocr
