"""
Vector Store Service — In-memory, per-session storage.
Stores chunks, BM25 index, and TF-IDF matrix for hybrid retrieval.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Global in-memory store keyed by session_id
_store: Dict[str, "SessionStore"] = {}


@dataclass
class SessionStore:
    session_id: str
    chunks: List[str] = field(default_factory=list)
    metadata: List[Dict[str, Any]] = field(default_factory=list)  # source info per chunk
    # BM25 and TF-IDF objects stored as opaque Any to avoid circular import
    bm25_index: Optional[Any] = None
    tfidf_vectorizer: Optional[Any] = None
    tfidf_matrix: Optional[Any] = None


def get_or_create_session(session_id: str) -> SessionStore:
    if session_id not in _store:
        _store[session_id] = SessionStore(session_id=session_id)
    return _store[session_id]


def get_session(session_id: str) -> Optional[SessionStore]:
    return _store.get(session_id)


def set_session(session_id: str, store: SessionStore) -> None:
    _store[session_id] = store


def delete_session(session_id: str) -> None:
    _store.pop(session_id, None)


def list_sessions() -> List[str]:
    return list(_store.keys())
