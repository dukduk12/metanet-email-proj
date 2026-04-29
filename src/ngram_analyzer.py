import re
from collections import Counter
from itertools import islice
from typing import Dict, List, Tuple, Optional

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os
from pathlib import Path
from loguru import logger

from src.config import settings

STOPWORDS = {
    "이", "가", "은", "는", "을", "를", "의", "에", "에서", "와", "과",
    "도", "만", "로", "으로", "에게", "한", "하는", "하여", "하고",
    "있는", "없는", "것", "수", "그", "저", "제", "및", "등", "또", "또한",
    "그리고", "위해", "위한", "대한", "관련", "통해", "따라", "대해",
    "있다", "없다", "합니다", "있습니다", "됩니다", "하다", "되다",
    "이에", "이를", "년", "월", "일", "시", "분", "호", "번", "개",
    "명", "건", "원", "해당", "사항", "내용", "경우", "통한", "하기",
    "하며", "위하여", "바랍니다", "드립니다", "입니다", "습니다",
    "으며", "으로", "에도", "부터", "까지", "이후", "이전", "각",
    "전", "후", "중", "위", "아래", "때", "곳", "어", "저희", "우리",
}

_FONT_PATH = "C:/Windows/Fonts/malgun.ttf"


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}", text)
    return [t for t in tokens if t not in STOPWORDS]


def extract_frequency(text: str, top_n: int = 30) -> List[Tuple[str, int]]:
    tokens = _tokenize(text)
    return Counter(tokens).most_common(top_n)


def extract_ngrams(text: str, n: int = 2, top_n: int = 20) -> List[Tuple[str, int]]:
    tokens = _tokenize(text)
    grams = zip(*[tokens[i:] for i in range(n)])
    phrases = [" ".join(g) for g in grams]
    return Counter(phrases).most_common(top_n)


def _font_prop():
    if os.path.exists(_FONT_PATH):
        return fm.FontProperties(fname=_FONT_PATH)
    return None


def generate_frequency_chart(
    freq: List[Tuple[str, int]],
    title: str = "상위 키워드 빈도",
    output_filename: str = "freq_chart.png",
    color: str = "#4C72B0",
) -> Optional[Path]:
    if not freq:
        return None
    fp = _font_prop()
    words = [w for w, _ in reversed(freq)]
    counts = [c for _, c in reversed(freq)]
    try:
        fig, ax = plt.subplots(figsize=(8, max(4, len(words) * 0.45)))
        bars = ax.barh(words, counts, color=color, height=0.65)
        ax.set_xlabel("빈도", fontproperties=fp, fontsize=10)
        ax.set_title(title, fontproperties=fp, pad=12)
        if fp:
            for lbl in ax.get_yticklabels():
                lbl.set_fontproperties(fp)
        for bar, cnt in zip(bars, counts):
            ax.text(bar.get_width() + max(counts) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    str(cnt), va="center", ha="left", fontsize=8)
        ax.set_xlim(right=max(counts) * 1.18)
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        out = settings.output_dir / output_filename
        plt.savefig(out, bbox_inches="tight", dpi=120)
        plt.close()
        return out
    except Exception as e:
        logger.error(f"빈도 차트 생성 실패: {e}")
        plt.close()
        return None


def generate_ngram_chart(
    ngrams: List[Tuple[str, int]],
    n: int = 2,
    title: str = "",
    output_filename: str = "ngram_chart.png",
    color: str = "#55A868",
) -> Optional[Path]:
    if not ngrams:
        return None
    label = f"{n}-gram" if not title else title
    return generate_frequency_chart(
        ngrams, title=f"상위 {label} 빈도", output_filename=output_filename, color=color
    )
