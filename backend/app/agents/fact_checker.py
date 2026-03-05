"""
Fact Checker Agent — Verifies each claim against retrieved evidence using LLM-based NLI.

For each claim:
  1. Retrieves top-k evidence chunks from the session store
  2. Prompts Groq to classify: ENTAILED / CONTRADICTED / NEUTRAL
  3. Returns verdict + confidence + supporting evidence

This LLM-based NLI approach is:
- More accurate than small HF cross-encoder models for complex claims
- Fully serverless-compatible (no heavy model weights)
- Explainable (returns reasoning)
"""
from __future__ import annotations
import json
import re
from typing import List, Dict, Any, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.embedding_service import hybrid_search
from app.services.vector_store import get_session
from app.core.config import GROQ_API_KEY, GROQ_MODEL, TOP_K_CLAIM_EVIDENCE


VERDICT_MAP = {
    "entailed": "supported",
    "supported": "supported",
    "contradicted": "contradicted",
    "contradiction": "contradicted",
    "neutral": "unsupported",
    "not enough evidence": "unsupported",
    "insufficient": "unsupported",
}

SYSTEM_PROMPT = """You are a precise fact-checking assistant. You will be given:
1. A factual claim to verify
2. Evidence passages retrieved from a document

Your task: Determine if the evidence ENTAILS, CONTRADICTS, or is NEUTRAL toward the claim.

Definitions:
- ENTAILED: The evidence directly supports and confirms the claim
- CONTRADICTED: The evidence directly contradicts or disproves the claim
- NEUTRAL: The evidence doesn't directly address the claim (insufficient evidence)

Return ONLY a valid JSON object with these exact fields:
{
  "verdict": "ENTAILED" | "CONTRADICTED" | "NEUTRAL",
  "confidence": 0.0 to 1.0,
  "reasoning": "one-sentence explanation"
}
"""


def verify_claim(
    claim: str,
    session_id: str,
    top_k: int = TOP_K_CLAIM_EVIDENCE,
) -> Dict[str, Any]:
    """
    Verify a single claim against the session's document store.

    Returns:
        {
            "claim": str,
            "verdict": "supported" | "contradicted" | "unsupported",
            "confidence": float,
            "reasoning": str,
            "evidence": list[str],
        }
    """
    base_result = {
        "claim": claim,
        "verdict": "unsupported",
        "confidence": 0.0,
        "reasoning": "No documents available for verification.",
        "evidence": [],
    }

    store = get_session(session_id)
    if store is None or not store.chunks:
        return base_result

    # Retrieve evidence chunks for this specific claim
    evidence_chunks = hybrid_search(claim, store, top_k=top_k)
    if not evidence_chunks:
        return base_result

    evidence_texts = [chunk for chunk, _, _ in evidence_chunks]

    # Build evidence block
    evidence_block = "\n\n".join(
        f"[Evidence {i+1}]: {text}" for i, text in enumerate(evidence_texts)
    )

    user_message = f"""Claim to verify: "{claim}"

Evidence passages:
{evidence_block}

Classify the claim. Return ONLY the JSON object."""

    llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.0)
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    raw = response.content.strip()

    # Parse JSON response
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            raw_verdict = parsed.get("verdict", "NEUTRAL").lower()
            verdict = VERDICT_MAP.get(raw_verdict, "unsupported")
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")

            return {
                "claim": claim,
                "verdict": verdict,
                "confidence": round(confidence, 3),
                "reasoning": reasoning,
                "evidence": evidence_texts,
            }
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    # Fallback: parse text response
    raw_lower = raw.lower()
    if "entailed" in raw_lower or "supported" in raw_lower:
        verdict = "supported"
        confidence = 0.7
    elif "contradicted" in raw_lower or "contradiction" in raw_lower:
        verdict = "contradicted"
        confidence = 0.7
    else:
        verdict = "unsupported"
        confidence = 0.4

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": raw[:200],
        "evidence": evidence_texts,
    }


def verify_claims(claims: List[str], session_id: str) -> List[Dict[str, Any]]:
    """Verify a list of claims, returning a verdict for each."""
    return [verify_claim(claim, session_id) for claim in claims]
