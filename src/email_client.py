import imaplib
import email
from email.header import decode_header
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from src.config import settings
import re

def decode_mime_words(s: str) -> str:
    if not s:
        return ""
    decoded_words = decode_header(s)
    text = ""
    for word, charset in decoded_words:
        if isinstance(word, bytes):
            if charset:
                try:
                    text += word.decode(charset)
                except LookupError:
                    text += word.decode('utf-8', errors='replace')
            else:
                text += word.decode('utf-8', errors='replace')
        else:
            text += word
    return text

def get_imap_connection():
    mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    mail.login(settings.gmail_email, settings.gmail_app_password)
    
    target_folder = "inbox"

    status, folders = mail.list()
    if status == "OK":
        for folder in folders:
            folder_str = folder.decode('utf-8', errors='ignore')
            if '\\All' in folder_str:
                match = re.search(r'"/"\s+(.+)$', folder_str)
                if match:
                    target_folder = match.group(1).strip()
                    break
    
    # 선택 시도
    status, _ = mail.select(target_folder)
    if status != "OK":
        mail.select("inbox")
            
    return mail

def fetch_emails_list(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    mail = get_imap_connection()
    email_list = []
    
    start_str = start_date.strftime("%d-%b-%Y")
    end_date_inclusive = end_date + timedelta(days=1)
    end_str = end_date_inclusive.strftime("%d-%b-%Y")
    
    search_criteria = f'(SINCE "{start_str}" BEFORE "{end_str}")'
    status, messages = mail.search(None, search_criteria)
    
    # 첨부파일이 있는 메일의 ID 목록을 별도로 가져옵니다 (Gmail 전용 기능)
    status_att, messages_att = mail.search('utf-8', f'(SINCE "{start_str}" BEFORE "{end_str}" X-GM-RAW "has:attachment")'.encode('utf-8'))
    attachment_ids = set()
    if status_att == "OK" and messages_att[0]:
        attachment_ids = set(messages_att[0].split())
    
    if status != "OK" or not messages[0]:
        mail.logout()
        return []
        
    email_ids = messages[0].split()
    if not email_ids:
        mail.logout()
        return []
        
    logger.info(f"Fetched {len(email_ids)} email IDs. Requesting headers in batch...")
    
    # 수천 개의 메일 헤더를 단 '한 번의' 네트워크 요청(Batch)으로 전부 가져오기
    fetch_str = b",".join(email_ids)
    status, msg_data = mail.fetch(fetch_str, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE FROM MESSAGE-ID)])')
    
    if status != "OK":
        mail.logout()
        return []
        
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            # response_part[0] 형태: b'123 (BODY[HEADER.FIELDS (SUBJECT DATE FROM MESSAGE-ID)] {34}'
            e_id_bytes = response_part[0].split()[0]
            msg = email.message_from_bytes(response_part[1])
            
            subject = decode_mime_words(msg.get("Subject", ""))
            
            # 정규표현식으로 대괄호 '[...]' 안의 말머리를 모두 추출합니다.
            tags = re.findall(r'\[(.*?)\]', subject)
            if not tags:
                continue  # 말머리가 없는 업무 메일은 제외합니다.
                
            has_attachment = e_id_bytes in attachment_ids
            
            msg_date = msg.get("Date", "Unknown Date")
            sender = decode_mime_words(msg.get("From", "Unknown Sender"))
            message_id = msg.get("Message-ID", e_id_bytes.decode())
            
            email_list.append({
                "id": e_id_bytes.decode(),
                "message_id": message_id,
                "subject": subject,
                "tags": [f"[{t.strip()}]" for t in tags if t.strip()], # 대괄호를 다시 붙여서 저장
                "date": msg_date,
                "sender": sender,
                "has_attachment": has_attachment
            })
                
    mail.logout()
    # 최신 메일이 먼저 표시되도록 ID 역순 정렬
    email_list.sort(key=lambda x: int(x["id"]), reverse=True)
    return email_list

def download_pdf_for_email(e_id: str) -> List[Path]:
    """
    특정 이메일(e_id)에서 PDF 첨부파일만 다운로드합니다.
    """
    pdf_paths = []
    try:
        mail = get_imap_connection()
        status, msg_data = mail.fetch(e_id.encode(), "(RFC822)")
        
        if status == "OK":
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_maintype() == "multipart":
                                continue
                            if part.get("Content-Disposition") is None:
                                continue
                                
                            filename = part.get_filename()
                            if filename:
                                filename = decode_mime_words(filename)
                                if filename.lower().endswith(".pdf"):
                                    filepath = settings.attachment_dir / filename
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    pdf_paths.append(filepath)
                                    logger.info(f"Downloaded PDF: {filename}")
        mail.logout()
        return pdf_paths
    except Exception as e:
        logger.error(f"Error downloading PDF for email {e_id}: {e}")
        return []
