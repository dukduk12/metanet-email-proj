from functools import lru_cache
from typing import List
import numpy as np
from loguru import logger

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_MAX_CHARS = 1500  # 너무 긴 문서는 잘라서 속도 확보


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer
    logger.info(f"임베딩 모델 로딩: {_MODEL_NAME} (첫 실행 시 다운로드 ~400MB)")
    return SentenceTransformer(_MODEL_NAME)


def embed_texts(texts: List[str]) -> np.ndarray:
    model = _load_model()
    truncated = [t[:_MAX_CHARS] for t in texts]
    return model.encode(truncated, normalize_embeddings=True, show_progress_bar=False)


def cosine_sim_matrix(embeddings: np.ndarray) -> np.ndarray:
    # L2-정규화된 벡터끼리의 내적 = 코사인 유사도
    return np.clip(embeddings @ embeddings.T, -1.0, 1.0)
