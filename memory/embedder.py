import os
import numpy as np
import logging
import pickle
from typing import List

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512
_backend = None
_model = None
_vectorizer = None
_VECTORIZER_PATH = "memory/tfidf_vectorizer.pkl"

_SEED = [
    "revenue quarterly earnings income financial performance apple microsoft tesla google amazon nvidia",
    "SEC EDGAR 10-K 10-Q annual report earnings per share EPS dividend buyback",
    "operating income net income gross profit cost of revenue operating expenses",
    "market sentiment positive negative neutral analyst rating upgrade downgrade price target",
    "risk assessment regulatory antitrust growth catalyst competitive moat valuation",
    "cloud revenue azure aws google cloud margin operating leverage subscription",
]

def _init_backend():
    global _backend, _model, _vectorizer, EMBEDDING_DIM

    if os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            _model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            _backend = "openai"
            EMBEDDING_DIM = 1536
            logger.info("Embedder: using OpenAI text-embedding-3-small (1536 dims)")
            return
        except Exception as e:
            logger.warning("OpenAI embedder init failed: %s", e)

    if os.getenv("USE_SENTENCE_TRANSFORMERS", "false").lower() == "true":
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            _backend = "sentence_transformers"
            EMBEDDING_DIM = 384
            logger.info("Embedder: using sentence-transformers all-MiniLM-L6-v2 (384 dims)")
            return
        except Exception as e:
            logger.warning("sentence-transformers init failed: %s", e)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        if os.path.exists(_VECTORIZER_PATH):
            with open(_VECTORIZER_PATH, "rb") as f:
                _vectorizer = pickle.load(f)
            logger.info("Embedder: loaded TF-IDF vectorizer from disk (512 dims)")
        else:
            _vectorizer = TfidfVectorizer(max_features=512, ngram_range=(1, 2), sublinear_tf=True)
            _vectorizer.fit(_SEED)
            os.makedirs("memory", exist_ok=True)
            with open(_VECTORIZER_PATH, "wb") as f:
                pickle.dump(_vectorizer, f)
            logger.info("Embedder: created new TF-IDF vectorizer (512 dims)")
        _backend = "tfidf"
        EMBEDDING_DIM = 512
    except Exception as e:
        logger.error("All embedder backends failed: %s", e)
        _backend = "zeros"
        EMBEDDING_DIM = 512


def embed(text: str) -> List[float]:
    if _backend is None:
        _init_backend()
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    try:
        if _backend == "openai":
            resp = _model.embeddings.create(model="text-embedding-3-small", input=text)
            vec = np.array(resp.data[0].embedding, dtype=np.float32)
        elif _backend == "sentence_transformers":
            vec = np.array(_model.encode(text, normalize_embeddings=True), dtype=np.float32)
        elif _backend == "tfidf":
            sparse = _vectorizer.transform([text]).toarray().flatten()
            vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
            n = min(len(sparse), EMBEDDING_DIM)
            vec[:n] = sparse[:n]
        else:
            return [0.0] * EMBEDDING_DIM
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
    except Exception as e:
        logger.warning("embed() failed: %s", e)
        return [0.0] * EMBEDDING_DIM


def embed_batch(texts: List[str]) -> List[List[float]]:
    return [embed(t) for t in texts]


def normalize_vector(vec: List[float]) -> List[float]:
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()
