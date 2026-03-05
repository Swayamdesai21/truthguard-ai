"""
Answer Generator Agent — Generates a draft answer using Groq LLM.

Input:  query (str), context_chunks (list of (text, metadata, score))
Output: {"answer": str, "sources": list[str]}
"""
from __future__ import annotations
from typing import List, Tuple, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """You are a precise research assistant. Your job is to answer questions \
based ONLY on the provided context passages. 

Rules:
- Only use information from the provided context
- If the context doesn't contain the answer, say "The provided documents don't contain enough information to answer this question."
- Be factual and specific
- Do NOT add information from your training data
- Write clear, concise paragraphs
"""


def generate_answer(
    query: str,
    context_chunks: List[Tuple[str, Dict[str, Any], float]],
) -> Dict[str, Any]:
    """
    Generate a draft answer from the query and retrieved context chunks.

    Returns:
        {
            "answer": str,
            "sources": list[str],   # source filenames used
        }
    """
    if not context_chunks:
        return {
            "answer": "No relevant documents found. Please upload source documents first.",
            "sources": [],
        }

    # Build numbered context
    context_parts = []
    sources = set()
    for i, (chunk, meta, score) in enumerate(context_chunks, 1):
        source = meta.get("source", "unknown")
        sources.add(source)
        context_parts.append(f"[{i}] ({source}): {chunk}")

    context_text = "\n\n".join(context_parts)

    user_message = f"""Context passages:
{context_text}

---
Question: {query}

Please write a comprehensive answer based strictly on the context above."""

    llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.1)
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    return {
        "answer": response.content.strip(),
        "sources": sorted(sources),
    }
