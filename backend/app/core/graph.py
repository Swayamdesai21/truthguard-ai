"""
LangGraph Orchestration — TruthGuard AI Agent Graph

Flow:
  retrieve_context
       ↓
  generate_answer
       ↓
  extract_claims
       ↓
  fact_check_claims
       ↓
  web_verify_claims     ← NEW: DuckDuckGo cross-referencing
       ↓
  check_consistency
       ↓
  refine_answer
       ↓
  [END]
"""
from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from app.services.embedding_service import hybrid_search
from app.services.vector_store import get_session
from app.agents.answer_generator import generate_answer
from app.agents.claim_extractor import extract_claims
from app.agents.fact_checker import verify_claims
from app.agents.web_verifier import web_verify_claims
from app.agents.consistency_checker import check_consistency
from app.agents.answer_refiner import refine_answer
from app.core.config import TOP_K_RETRIEVAL


# ── State Schema ──────────────────────────────────────────────────────────────

class TruthGuardState(TypedDict):
    session_id: str
    query: str

    # RAG
    context_chunks: List[Any]   # list of (text, meta, score)

    # Generation
    draft_answer: str
    sources: List[str]

    # Claim extraction
    claims: List[str]

    # Fact checking
    verdicts: List[Dict[str, Any]]

    # Consistency
    enriched_verdicts: List[Dict[str, Any]]

    # Web verification
    web_sources: List[Dict[str, Any]]

    # Final output
    refined_answer: str
    confidence_score: float
    document_confidence: float
    web_confidence: float
    removed_claims: List[str]
    cited_sources: List[str]

    # Error handling
    error: Optional[str]


# ── Node Functions ────────────────────────────────────────────────────────────

def node_retrieve_context(state: TruthGuardState) -> TruthGuardState:
    """Retrieve top-k relevant chunks from the session's vector store."""
    session_id = state["session_id"]
    query = state["query"]

    store = get_session(session_id)
    if store is None or not store.chunks:
        return {**state, "context_chunks": [], "error": "No documents found for this session. Please upload documents first."}

    chunks = hybrid_search(query, store, top_k=TOP_K_RETRIEVAL)
    return {**state, "context_chunks": chunks, "error": None}


def node_generate_answer(state: TruthGuardState) -> TruthGuardState:
    """Generate a draft answer from context chunks."""
    if state.get("error"):
        return state

    result = generate_answer(state["query"], state["context_chunks"])
    return {
        **state,
        "draft_answer": result["answer"],
        "sources": result["sources"],
    }


def node_extract_claims(state: TruthGuardState) -> TruthGuardState:
    """Split the draft answer into atomic verifiable claims."""
    if state.get("error"):
        return state

    claims = extract_claims(state["draft_answer"])
    return {**state, "claims": claims}


def node_fact_check_claims(state: TruthGuardState) -> TruthGuardState:
    """Verify each claim against the knowledge base."""
    if state.get("error"):
        return state

    verdicts = verify_claims(state["claims"], state["session_id"])
    return {**state, "verdicts": verdicts}


def node_check_consistency(state: TruthGuardState) -> TruthGuardState:
    """Detect cross-claim contradictions and assign hallucination risk."""
    if state.get("error"):
        return state

    enriched = check_consistency(state["verdicts"])
    return {**state, "enriched_verdicts": enriched}


def node_web_verify_claims(state: TruthGuardState) -> TruthGuardState:
    """Cross-check claims against live web search results."""
    if state.get("error"):
        return state

    # Web-verify the enriched verdicts
    web_enriched = web_verify_claims(state["enriched_verdicts"])

    # Collect all unique web sources
    all_web_sources = []
    seen_urls = set()
    for v in web_enriched:
        for ws in v.get("web_sources", []):
            url = ws.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_web_sources.append(ws)

    return {
        **state,
        "enriched_verdicts": web_enriched,
        "web_sources": all_web_sources,
    }


def node_refine_answer(state: TruthGuardState) -> TruthGuardState:
    """Rewrite the answer with citations and remove unsupported claims."""
    if state.get("error"):
        return state

    result = refine_answer(
        state["draft_answer"],
        state["enriched_verdicts"],
        state["sources"],
    )
    return {
        **state,
        "refined_answer": result["refined_answer"],
        "confidence_score": result["confidence_score"],
        "document_confidence": result["document_confidence"],
        "web_confidence": result["web_confidence"],
        "removed_claims": result["removed_claims"],
        "cited_sources": result["cited_sources"],
    }


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(TruthGuardState)

    graph.add_node("retrieve_context", node_retrieve_context)
    graph.add_node("generate_answer", node_generate_answer)
    graph.add_node("extract_claims", node_extract_claims)
    graph.add_node("fact_check_claims", node_fact_check_claims)
    graph.add_node("check_consistency", node_check_consistency)
    graph.add_node("web_verify_claims", node_web_verify_claims)
    graph.add_node("refine_answer", node_refine_answer)

    graph.set_entry_point("retrieve_context")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", "extract_claims")
    graph.add_edge("extract_claims", "fact_check_claims")
    graph.add_edge("fact_check_claims", "check_consistency")
    graph.add_edge("check_consistency", "web_verify_claims")
    graph.add_edge("web_verify_claims", "refine_answer")
    graph.add_edge("refine_answer", END)

    return graph.compile()


# Compiled graph — singleton
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_pipeline(session_id: str, query: str) -> Dict[str, Any]:
    """
    Run the full TruthGuard pipeline and return a structured result dict.
    """
    graph = get_graph()

    initial_state: TruthGuardState = {
        "session_id": session_id,
        "query": query,
        "context_chunks": [],
        "draft_answer": "",
        "sources": [],
        "claims": [],
        "verdicts": [],
        "enriched_verdicts": [],
        "web_sources": [],
        "refined_answer": "",
        "confidence_score": 0.0,
        "document_confidence": 0.0,
        "web_confidence": 0.0,
        "removed_claims": [],
        "cited_sources": [],
        "error": None,
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as exc:
        # Catch Groq rate limits, connection errors, and any other pipeline failure
        err_msg = str(exc)
        # Make the error message human-readable
        if "rate_limit_exceeded" in err_msg or "429" in err_msg:
            err_msg = (
                "Groq API daily token limit reached (100k tokens/day on free tier). "
                "Please wait a few minutes and try again, or switch to a smaller model "
                "(e.g. llama3-8b-8192) in backend/app/core/config.py."
            )
        elif "APIConnectionError" in type(exc).__name__ or "Connection error" in err_msg:
            err_msg = (
                "Cannot connect to Groq API. Please check your internet connection "
                "and verify your GROQ_API_KEY in the .env file."
            )
        return {"error": err_msg}

    if final_state.get("error"):
        return {"error": final_state["error"]}

    return {
        "session_id": session_id,
        "query": query,
        "draft_answer": final_state.get("draft_answer", ""),
        "refined_answer": final_state.get("refined_answer", ""),
        "confidence_score": final_state.get("confidence_score", 0.0),
        "document_confidence": final_state.get("document_confidence", 0.0),
        "web_confidence": final_state.get("web_confidence", 0.0),
        "claims": final_state.get("enriched_verdicts", []),
        "sources": final_state.get("cited_sources", []),
        "web_sources": final_state.get("web_sources", []),
        "removed_claims": final_state.get("removed_claims", []),
    }
