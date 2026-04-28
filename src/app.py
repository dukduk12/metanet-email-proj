import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta, date
import sys

# Ensure src directory is in path
sys.path.append(str(Path(__file__).parent.parent))

from src.logging_config import setup_logger
from src.email_client import fetch_emails_list, download_pdf_for_email
from src.pdf_parser import extract_text_from_pdf
from src.summarizer import summarize_text
from src.word_cloud_gen import generate_word_cloud

# Initialize logger
setup_logger()

st.set_page_config(page_title="업무 메일 PDF 분석기", page_icon="📧", layout="wide")

st.title("📧 업무 메일 PDF 분석 및 요약기")
st.markdown("목록을 먼저 확인한 뒤, 원하는 말머리를 골라 메일만 개별적으로 분석할 수 있습니다.")

# --- 1. Date Range Selection ---
st.header("1. 기간 설정 및 메일 목록 조회")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작일", value=date.today() - timedelta(days=7))
with col2:
    end_date = st.date_input("종료일", value=date.today())

import json
from src.config import settings

# --- Processed State Management ---
PROCESSED_FILE = settings.output_dir / "processed_emails.json"

def load_processed_data():
    if PROCESSED_FILE.exists():
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_processed_data(msg_id, results):
    data = load_processed_data()
    
    # Convert Path objects to strings for JSON serialization
    serialized_results = []
    for item in results:
        new_item = item.copy()
        if 'wc_path' in new_item and new_item['wc_path']:
            new_item['wc_path'] = str(new_item['wc_path'])
        serialized_results.append(new_item)
        
    data[msg_id] = serialized_results
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Session states
if "email_list" not in st.session_state:
    st.session_state.email_list = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}

if "unique_tags" not in st.session_state:
    st.session_state.unique_tags = []
if "selected_tags" not in st.session_state:
    st.session_state.selected_tags = []

if st.button("목록 조회", type="primary"):
    with st.spinner("메일 목록을 가져오는 중..."):
        all_emails = fetch_emails_list(start_date, end_date)
        st.session_state.email_list = all_emails
        st.session_state.analysis_results = {}
        
        tags = set()
        for e in all_emails:
            for t in e.get("tags", []):
                tags.add(t)
        st.session_state.unique_tags = sorted(list(tags))
        
        if "[업무 협조]" in st.session_state.unique_tags:
            st.session_state.selected_tags = ["[업무 협조]"]
        else:
            st.session_state.selected_tags = st.session_state.unique_tags[:1] if st.session_state.unique_tags else []
        
    if not st.session_state.email_list:
        st.warning("해당 기간에 말머리([...])가 포함된 메일이 없습니다.")
    else:
        st.success(f"말머리가 있는 {len(st.session_state.email_list)}개의 메일을 찾았습니다.")

# --- 2. Email List & Individual Analysis ---
if st.session_state.email_list is not None and len(st.session_state.email_list) > 0:
    st.header("2. 개별 메일 분석")
    st.markdown("원하는 말머리를 선택한 후, 첨부파일이 있는 메일의 **'이 메일 분석하기'** 버튼을 클릭하세요.")
    
    st.session_state.selected_tags = st.multiselect(
        "분석할 말머리 선택 (여러 개 선택 가능)", 
        options=st.session_state.unique_tags, 
        default=st.session_state.selected_tags
    )
    
    filtered_emails = []
    for e in st.session_state.email_list:
        if any(tag in st.session_state.selected_tags for tag in e.get("tags", [])):
            filtered_emails.append(e)
            
    if not filtered_emails:
         st.info("선택한 말머리에 해당하는 메일이 없습니다.")
    
    processed_data = load_processed_data()
    
    for email_meta in filtered_emails:
        e_id = email_meta['id']
        msg_id = email_meta.get('message_id', e_id)
        has_att = email_meta.get('has_attachment', False)
        
        with st.container():
            att_icon = "📎" if has_att else ""
            st.markdown(f"#### {att_icon} 📄 {email_meta['subject']}")
            st.markdown(f"*수신일:* {email_meta['date']} | *보낸사람:* {email_meta['sender']}")
            
            if msg_id in processed_data:
                st.success("✅ 이미 분석이 완료된 메일입니다. (저장된 결과를 불러옵니다)")
                results = processed_data[msg_id]
                
                with st.expander("저장된 분석 결과 보기", expanded=True):
                    for item in results:
                        if "error" in item:
                            st.warning(f"**{item.get('file', '문서')}**: {item['error']}")
                        else:
                            st.markdown(f"**파일:** `{item['file']}`")
                            st.info("💡 **요약 결과**")
                            st.write(item['summary'])
                            
                            if item.get('wc_path') and Path(item['wc_path']).exists():
                                st.image(item['wc_path'], caption=f"워드 클라우드 - {item['file']}")
                                
                            with st.popover("원본 텍스트 보기"):
                                st.text(item['text'])
            else:
                # 개별 분석 버튼
                if not has_att:
                    st.info("이 메일에는 첨부파일이 없습니다.")
                else:
                    if st.button("이 메일 분석하기", key=f"btn_{e_id}"):
                        with st.spinner("해당 메일의 PDF를 다운로드하고 분석하는 중..."):
                            pdf_paths = download_pdf_for_email(e_id)
                            
                            if not pdf_paths:
                                # PDF가 없는 경우 에러를 저장
                                save_processed_data(msg_id, [{"error": "이 메일에는 PDF 첨부파일이 없습니다."}])
                                st.rerun()
                            else:
                                results = []
                                for pdf_path in pdf_paths:
                                    text = extract_text_from_pdf(pdf_path)
                                    if not text.strip():
                                        results.append({"file": pdf_path.name, "error": "텍스트를 추출할 수 없습니다."})
                                        continue
                                        
                                    summary = summarize_text(text)
                                    wc_filename = f"wordcloud_{e_id}_{pdf_path.name}.png"
                                    wc_path = generate_word_cloud(text, output_filename=wc_filename)
                                    
                                    results.append({
                                        "file": pdf_path.name,
                                        "text": text,
                                        "summary": summary,
                                        "wc_path": wc_path
                                    })
                                save_processed_data(msg_id, results)
                                st.rerun()
            st.markdown("---")
            st.markdown("---")
