import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Ensure src directory is in path
sys.path.append(str(Path(__file__).parent.parent))

from src.db_client import ChromaClient

st.set_page_config(page_title="Chroma DB 데이터 뷰어", page_icon="🗄️", layout="wide")

st.title("🗄️ Chroma DB 데이터 뷰어")
st.markdown("Airflow가 수집 및 분석하여 DB에 넣은 데이터를 표 형태로 편하게 확인하는 대시보드입니다.")

chroma_client = ChromaClient()
if chroma_client.collection:
    data = chroma_client.collection.get(include=['embeddings', 'metadatas', 'documents'])
    if data and data['ids']:
        st.success(f"총 {len(data['ids'])}개의 과거 메일 데이터가 적재되어 있습니다.")
        
        embeddings_preview = []
        if 'embeddings' in data and data['embeddings'] is not None:
            for emb in data['embeddings']:
                if emb is not None and len(emb) > 0:
                    preview = ", ".join([f"{x:.4f}" for x in emb[:4]])
                    embeddings_preview.append(f"[{preview}, ...] ({len(emb)}차원)")
                else:
                    embeddings_preview.append("임베딩 없음")
        else:
            embeddings_preview = ["임베딩 데이터 없음"] * len(data['ids'])
            
        db_df = pd.DataFrame({
            "메일 ID": data['ids'],
            "제목": [m.get('title', '') for m in data['metadatas']],
            "보낸사람": [m.get('sender', '') for m in data['metadatas']],
            "날짜(수신일)": [m.get('date', '') for m in data['metadatas']],
            "임베딩 벡터 (수치)": embeddings_preview,
            "AI 요약 내용": [m.get('summary', '') for m in data['metadatas']]
        })
        
        st.dataframe(
            db_df, 
            hide_index=True, 
            use_container_width=True,
            height=600
        )
    else:
        st.info("현재 Chroma DB에 저장된 과거 메일 데이터가 없습니다.")
else:
    st.error("Chroma DB 컨테이너에 연결할 수 없습니다. Docker가 켜져 있는지 확인하세요.")
