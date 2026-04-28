import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from loguru import logger
from src.config import settings

KOREAN_STOPWORDS = [
    "이", "가", "은", "는", "을", "를", "의", "에", "에서", "와", "과",
    "도", "만", "로", "으로", "에게", "께", "한", "하는", "하여", "하고",
    "있는", "없는", "것", "수", "그", "저", "제", "및", "등", "또", "또한",
    "그리고", "위해", "위한", "대한", "관련", "통해", "따라", "대해",
    "있다", "없다", "합니다", "있습니다", "없습니다", "됩니다",
    "하다", "되다", "같다", "이다", "아니다", "이에", "이를",
    "년", "월", "일", "시", "분", "호", "번", "개", "명", "건", "원",
    "해당", "사항", "내용", "경우", "통한", "하기", "하며", "위하여",
    "바랍니다", "드립니다", "입니다", "습니다", "으며", "으로", "에도",
]

_FONT_PATH = "C:/Windows/Fonts/malgun.ttf"


def extract_tfidf_keywords(
    texts: Dict[str, str], top_n: int = 15
) -> Dict[str, List[Tuple[str, float]]]:
    """
    texts: {문서이름: 텍스트}
    여러 문서를 동시에 넣을수록 IDF가 의미있어짐 (문서 간 비교)
    """
    if not texts:
        return {}

    doc_names = list(texts.keys())
    corpus = [texts[name] for name in doc_names]

    try:
        vectorizer = TfidfVectorizer(
            token_pattern=r"[가-힣]{2,}|[a-zA-Z]{3,}",
            stop_words=KOREAN_STOPWORDS,
            max_features=1000,
            sublinear_tf=True,  # log(1 + tf) 스무딩 — 빈도 폭발 완화
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = vectorizer.get_feature_names_out()

        result = {}
        for i, name in enumerate(doc_names):
            scores = tfidf_matrix[i].toarray()[0]
            top_indices = np.argsort(scores)[::-1][:top_n]
            result[name] = [
                (feature_names[idx], float(scores[idx]))
                for idx in top_indices
                if scores[idx] > 0
            ]
        return result
    except Exception as e:
        logger.error(f"TF-IDF 추출 실패: {e}")
        return {}


def generate_tfidf_chart(
    keywords: List[Tuple[str, float]],
    title: str,
    output_filename: str = "tfidf_chart.png",
) -> Optional[Path]:
    if not keywords:
        return None

    font_prop = None
    if os.path.exists(_FONT_PATH):
        font_prop = fm.FontProperties(fname=_FONT_PATH)

    try:
        words = [kw for kw, _ in reversed(keywords)]
        scores = [sc for _, sc in reversed(keywords)]

        fig, ax = plt.subplots(figsize=(8, max(4, len(words) * 0.45)))
        bars = ax.barh(words, scores, color="steelblue", height=0.6)

        ax.set_xlabel("TF-IDF 점수", fontproperties=font_prop, fontsize=10)
        short_title = title[:35] + ("…" if len(title) > 35 else "")
        ax.set_title(f"핵심 키워드: {short_title}", fontproperties=font_prop, pad=12)

        if font_prop:
            for label in ax.get_yticklabels():
                label.set_fontproperties(font_prop)

        for bar, score in zip(bars, scores):
            ax.text(
                bar.get_width() + max(scores) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{score:.3f}",
                va="center", ha="left", fontsize=8,
            )

        ax.set_xlim(right=max(scores) * 1.18)
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()

        output_path = settings.output_dir / output_filename
        plt.savefig(output_path, bbox_inches="tight", dpi=120)
        plt.close()
        logger.info(f"TF-IDF 차트 저장: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"TF-IDF 차트 생성 실패: {e}")
        plt.close()
        return None