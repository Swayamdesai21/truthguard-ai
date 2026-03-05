"""
Embedding Service — BM25 + TF-IDF hybrid retrieval.

No external embedding API needed:
- BM25 (rank-bm25): keyword frequency scoring
- TF-IDF cosine similarity (scikit-learn): semantic approximation
- RRF fusion: combines both ranked lists
"""
from __future__ import annotations
from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi

from app.services.vector_store import SessionStore
from app.core.config import TOP_K_RETRIEVAL


def build_indices(chunks: List[str]) -> Tuple[BM25Okapi, TfidfVectorizer, np.ndarray]:
    """Build BM25 and TF-IDF indices from a list of text chunks."""
    # BM25 — tokenize by whitespace
    tokenized = [chunk.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized)

    # TF-IDF
    vectorizer = TfidfVectorizer(
        sublinear_tf=True,
        max_df=0.95,
        min_df=1,
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(chunks)

    return bm25, vectorizer, tfidf_matrix


def hybrid_search(
    query: str,
    store: SessionStore,
    top_k: int = TOP_K_RETRIEVAL,
) -> List[Tuple[str, dict, float]]:
    """
    Hybrid BM25 + TF-IDF retrieval with RRF fusion.

    Returns: list of (chunk_text, metadata, rrf_score) sorted by score desc.
    """
    chunks = store.chunks
    if not chunks:
        return []

    n = len(chunks)
    top_k = min(top_k, n)

    # ── BM25 scores ──────────────────────────────────────────────────────
    tokenized_query = query.lower().split()
    bm25_scores = store.bm25_index.get_scores(tokenized_query)
    bm25_ranked = np.argsort(bm25_scores)[::-1]  # indices sorted by score desc

    # ── TF-IDF cosine scores ──────────────────────────────────────────────
    query_vec = store.tfidf_vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, store.tfidf_matrix).flatten()
    tfidf_ranked = np.argsort(tfidf_scores)[::-1]

    # ── RRF Fusion (k=60 standard) ────────────────────────────────────────
    k = 60
    rrf_scores = np.zeros(n)
    for rank, idx in enumerate(bm25_ranked):
        rrf_scores[idx] += 1.0 / (k + rank + 1)
    for rank, idx in enumerate(tfidf_ranked):
        rrf_scores[idx] += 1.0 / (k + rank + 1)

    top_indices = np.argsort(rrf_scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if rrf_scores[idx] > 0:
            meta = store.metadata[idx] if idx < len(store.metadata) else {}
            results.append((chunks[idx], meta, float(rrf_scores[idx])))

    return results
