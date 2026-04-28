import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.pdf_parser import extract_text_from_pdf
from src.summarizer import summarize_text
from src.db_client import ChromaClient
from loguru import logger
import time

def init_dummy_data():
    client = ChromaClient()
    
    if client.collection is None:
        logger.error("Failed to connect to ChromaDB.")
        return
        
    pdf_path = settings.attachment_dir / "사업제안서.pdf"
    
    if not pdf_path.exists():
        logger.error(f"Cannot find {pdf_path}. Cannot initialize dummy data.")
        return
        
    logger.info("Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        logger.error("Failed to extract text from PDF.")
        return
        
    logger.info("Summarizing text...")
    summary = summarize_text(text)
    
    logger.info("Adding to ChromaDB...")
    success = client.add_email(
        email_id="dummy_email_001",
        title="[업무 협조] 사업 제안서",
        summary=summary,
        date="2026-04-28",
        sender="가짜 발신자 <dummy@company.com>"
    )
    
    if success:
        logger.info("Successfully loaded dummy data!")
    else:
        logger.error("Failed to load dummy data.")

if __name__ == "__main__":
    init_dummy_data()
