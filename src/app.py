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
from src.db_client import ChromaClient
from src.tfidf_analyzer import extract_tfidf_keywords, generate_tfidf_chart
from src.network_viz import build_and_render_network

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
    st.header("2. 메일 선택 및 분석")
    st.markdown("분석할 메일을 테이블에서 선택한 뒤 **선택한 메일 분석하기** 버튼을 클릭하세요.")
    
    st.session_state.selected_tags = st.multiselect(
        "필터: 말머리 선택", 
        options=st.session_state.unique_tags, 
        default=st.session_state.selected_tags
    )
    
    show_only_pdf = st.checkbox("PDF 첨부된 메일만 보기", value=True)
    
    filtered_emails = []
    for e in st.session_state.email_list:
        if any(tag in st.session_state.selected_tags for tag in e.get("tags", [])):
            if show_only_pdf and not e.get("has_attachment", False):
                continue
            filtered_emails.append(e)
            
    if not filtered_emails:
         st.info("조건에 맞는 메일이 없습니다.")
    else:
        import pandas as pd
        
        df_data = []
        for e in filtered_emails:
            df_data.append({
                "선택": False,
                "id": e["id"],
                "날짜": e["date"],
                "보낸사람": e["sender"],
                "제목": e["subject"],
                "PDF 개수": e.get("pdf_count", 0),
                "첨부파일명": ", ".join(e.get("pdf_names", [])),
                "본문 미리보기": e.get("body_snippet", "")
            })
            
        df = pd.DataFrame(df_data)
        
        edited_df = st.data_editor(
            df,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False),
                "id": None, # Hide ID column
            },
            disabled=["날짜", "보낸사람", "제목", "PDF 개수", "첨부파일명", "본문 미리보기"],
            hide_index=True,
            use_container_width=True
        )
        
        selected_ids = edited_df[edited_df["선택"] == True]["id"].tolist()
        
        if st.button("선택한 메일 분석하기", type="primary", disabled=len(selected_ids)==0):
            st.session_state.analysis_triggered = True
            st.session_state.selected_email_ids = selected_ids
            
        if getattr(st.session_state, 'analysis_triggered', False):
            st.markdown("---")
            st.header("분석 결과")
            processed_data = load_processed_data()
            
            selected_emails = [e for e in filtered_emails if e["id"] in st.session_state.selected_email_ids]
            
            for email_meta in selected_emails:
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
                                    if item.get('file'):
                                        st.markdown(f"**파일:** `{item['file']}`")
                                    st.info("💡 **요약 결과**")
                                    st.write(item['summary'])
                                    
                                    if item.get('wc_path') and Path(item['wc_path']).exists():
                                        st.image(item['wc_path'], caption=f"워드 클라우드 - {item.get('file', '문서')}")
                                        
                                    with st.popover("원본 텍스트 보기"):
                                        st.text(item['text'])
                    else:
                        with st.spinner("해당 메일의 데이터를 다운로드하고 분석하는 중..."):
                            results = []
                            if has_att:
                                pdf_paths = download_pdf_for_email(e_id)
                                if not pdf_paths:
                                    results.append({"error": "이 메일에는 PDF 첨부파일이 없습니다."})
                                else:
                                    for pdf_path in pdf_paths:
                                        text = extract_text_from_pdf(pdf_path)
                                        if not text.strip():
                                            results.append({"file": pdf_path.name, "error": "텍스트를 추출할 수 없습니다."})
                                            continue
                                            
                                        summary = summarize_text(text)
                                        wc_filename = f"tfidf_{e_id}_{pdf_path.name}.png"
                                        
                                        # TF-IDF 차트 생성 로직으로 변경
                                        keywords_dict = extract_tfidf_keywords({pdf_path.name: text})
                                        keywords = keywords_dict.get(pdf_path.name, [])
                                        wc_path = generate_tfidf_chart(keywords, title=pdf_path.name, output_filename=wc_filename)
                                        
                                        results.append({
                                            "file": pdf_path.name,
                                            "text": text,
                                            "summary": summary,
                                            "wc_path": wc_path
                                        })
                            else:
                                text = email_meta.get("body_snippet", "")
                                if not text:
                                    results.append({"error": "분석할 텍스트가 없습니다."})
                                else:
                                    summary = summarize_text(text)
                                    results.append({
                                        "file": "메일 본문",
                                        "text": text,
                                        "summary": summary,
                                        "wc_path": ""
                                    })
                            
                            if results:
                                save_processed_data(msg_id, results)
                                st.rerun()
                                
                    # --- Similar Emails Recommendation ---
                    if msg_id in processed_data:
                        st.markdown("##### 💡 과거 유사 업무 메일 추천")
                        results = processed_data[msg_id]
                        if results and 'summary' in results[0]:
                            search_text = f"제목: {email_meta['subject']}\n요약: {results[0]['summary']}"
                            
                            with st.spinner("유사한 과거 메일을 검색하는 중..."):
                                chroma_client = ChromaClient()
                                similar_emails = chroma_client.query_similar(search_text, n_results=3)
                                
                                has_recommendation = False
                                if similar_emails:
                                    for idx, sim in enumerate(similar_emails):
                                        has_recommendation = True
                                        distance = sim.get('distance', 0.0)
                                        similarity = max(0, 100 - (distance * 100))
                                        
                                        st.info(f"**{sim['metadata'].get('title', '제목 없음')}** (유사도: {similarity:.1f}%)\n\n"
                                                f"📅 *날짜:* {sim['metadata'].get('date', '')} | 👤 *보낸사람:* {sim['metadata'].get('sender', '')}\n\n"
                                                f"{sim['metadata'].get('summary', '')}")
                                
                                if not has_recommendation:
                                    st.write("유사한 과거 메일이 없습니다.")
                                    
                st.markdown("---")

            # --- 선택 메일 전체 비교: TF-IDF + 네트워크 ---
            all_texts = {}
            sender_docs_net = {}
            for em in selected_emails:
                mid = em.get("message_id", em["id"])
                for item in processed_data.get(mid, []):
                    if item.get("text") and "error" not in item:
                        key = f"{em['subject'][:25]} / {item.get('file', '본문')}"
                        all_texts[key] = item["text"]
                        sender_docs_net.setdefault(em["sender"], []).append({
                            "file": item.get("file", "본문"),
                            "text": item["text"],
                            "email_subject": em["subject"],
                            "email_date": em["date"],
                        })

            tfidf_results = extract_tfidf_keywords(all_texts) if all_texts else {}

            if tfidf_results:
                st.header("📊 TF-IDF 핵심 키워드 비교")
                st.caption(f"선택한 {len(tfidf_results)}개 문서 동시 비교 — 각 문서에서만 특징적인 단어 추출")
                cols = st.columns(min(len(tfidf_results), 2))
                for idx, (doc_name, keywords) in enumerate(tfidf_results.items()):
                    with cols[idx % 2]:
                        safe = "".join(c if c.isalnum() else "_" for c in doc_name[:20])
                        chart_path = generate_tfidf_chart(
                            keywords, title=doc_name, output_filename=f"tfidf_cmp_{idx}_{safe}.png"
                        )
                        if chart_path and Path(chart_path).exists():
                            st.image(str(chart_path), caption=doc_name, use_container_width=True)

            if sender_docs_net:
                st.header("🕸️ 업무 관계 네트워크")
                st.caption("● 발신자  ■ PDF — 점선은 내용 유사도, 색깔은 업무 클러스터 | 첫 실행 시 모델 다운로드 ~400MB")
                with st.spinner("임베딩 계산 중... (문서 수에 따라 10~30초)"):
                    net_fig = build_and_render_network(sender_docs_net, tfidf_results)
                if net_fig:
                    st.plotly_chart(net_fig, use_container_width=True)
                else:
                    st.info("네트워크를 생성하기에 데이터가 부족합니다.")
