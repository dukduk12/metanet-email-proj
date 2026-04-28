import fitz # PyMuPDF
from pathlib import Path
from loguru import logger

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts text from a given PDF file using PyMuPDF.
    """
    logger.info(f"Extracting text from {pdf_path.name}")
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text() + "\n"
        logger.info(f"Successfully extracted {len(text)} characters from {pdf_path.name}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path.name}: {e}")
        return ""
