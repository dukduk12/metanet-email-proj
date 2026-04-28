from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, date
import sys
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Add src to python path for Airflow
sys.path.append("/opt/airflow")

def process_daily_emails(**context):
    from src.email_client import fetch_emails_list, download_pdf_for_email
    from src.pdf_parser import extract_text_from_pdf
    from src.summarizer import summarize_text
    from src.db_client import ChromaClient
    
    target_date = date.today()
    logger.info(f"Processing emails for TODAY'S date: {target_date}")
    
    # Fetch emails with tag [업무 협조]
    emails = fetch_emails_list(target_date, target_date)
    target_emails = [e for e in emails if "[업무 협조]" in e.get("tags", [])]
    
    if not target_emails:
        logger.info(f"No target emails found for {target_date}")
        return
        
    client = ChromaClient()
    if not client.collection:
        logger.error("Could not connect to ChromaDB")
        return
        
    if client.collection.count() == 0:
        logger.info("ChromaDB is empty! Initializing dummy data first...")
        try:
            from scripts.init_chroma import init_dummy_data
            init_dummy_data()
            logger.info("Dummy data initialized successfully during DAG run.")
        except Exception as e:
            logger.error(f"Failed to initialize dummy data: {e}")
        
    for email_meta in target_emails:
        e_id = email_meta['id']
        msg_id = email_meta.get('message_id', e_id)
        has_att = email_meta.get('has_attachment', False)
        subject = email_meta['subject']
        sender = email_meta['sender']
        
        text_to_summarize = ""
        
        if has_att:
            pdf_paths = download_pdf_for_email(e_id)
            for pdf_path in pdf_paths:
                extracted = extract_text_from_pdf(pdf_path)
                if extracted:
                    text_to_summarize += extracted + "\n"
        else:
            text_to_summarize = email_meta.get("body_snippet", "")
            
        if not text_to_summarize.strip():
            logger.warning(f"No text to summarize for email {e_id}")
            continue
            
        logger.info(f"Summarizing email: {subject}")
        summary = summarize_text(text_to_summarize)
        
        # Add to ChromaDB
        client.add_email(
            email_id=msg_id,
            title=subject,
            summary=summary,
            date=str(target_date),
            sender=sender
        )
        logger.info(f"Added email {msg_id} to ChromaDB")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'email_embedding_daily_job',
    default_args=default_args,
    description='Daily job to fetch emails, summarize, and embed into ChromaDB',
    schedule_interval='@daily',
    start_date=datetime(2026, 4, 20),
    catchup=False,
    tags=['email', 'chromadb', 'rag'],
) as dag:

    process_emails_task = PythonOperator(
        task_id='process_daily_emails',
        python_callable=process_daily_emails,
        provide_context=True,
    )

    process_emails_task
