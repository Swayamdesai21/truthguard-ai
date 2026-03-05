"""
Answer Refiner Agent — Rewrites the draft answer using claim verdicts.

Computes DUAL confidence scores:
  - document_confidence: based on document-only fact-check verdicts
  - web_confidence: based on web verification verdicts
  - overall_confidence: weighted combination of both
"""
from __future__ import annotations
import json
import re
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """You are a precise fact-checking editor. Your job is to rewrite an answer \
based on verified claim information.

Rules:
- Keep claims marked as "supported" (they are verified)
- Remove or mark claims as [UNVERIFIED] if they are "unsupported"
- Add [CONTRADICTED] before claims that are contradicted by sources
- Add citation numbers [1], [2] etc. when evidence is available
- Keep the answer natural and readable
- Do NOT add new information
- Return ONLY a valid JSON object, no other text
"""


def compute_document_confidence(verdicts: List[Dict[str, Any]]) -> float:
    """
    Confidence score based on document-only fact-checking.

    Formula:
        - supported: +1.0 × confidence
        - unsupported: +0.0
        - contradicted: -0.5 × confidence
    Normalized to [0, 1].
    """
    if not verdicts:
        return 0.0

    total = len(verdicts)
    score = 0.0

    for v in verdicts:
        verdict = v.get("verdict", "unsupported")
        confidence = v.get("confidence", 0.5)

        if verdict == "supported":
            score += confidence
        elif verdict == "contradicted":
            score -= 0.5 * confidence

    normalized = score / total if total > 0 else 0.0
    return round(max(0.0, min(1.0, normalized)), 3)


def compute_web_confidence(verdicts: List[Dict[str, Any]]) -> float:
    """
    Confidence score based on web verification results.

    Formula:
        - web_verdict "supported": +1.0 × web_confidence
        - web_verdict "inconclusive": +0.3 × web_confidence
        - web_verdict "contradicted": -0.5 × web_confidence
    Normalized to [0, 1].
    """
    if not verdicts:
        return 0.0

    total = 0
    score = 0.0

    for v in verdicts:
        web_verdict = v.get("web_verdict", "")
        web_conf = v.get("web_confidence", 0.0)

        if not web_verdict:
            continue

        total += 1
        if web_verdict == "supported":
            score += web_conf
        elif web_verdict == "inconclusive":
            score += 0.3 * web_conf
        elif web_verdict == "contradicted":
            score -= 0.5 * web_conf

    if total == 0:
        return 0.0

    normalized = score / total
    return round(max(0.0, min(1.0, normalized)), 3)


def compute_overall_confidence(doc_conf: float, web_conf: float) -> float:
    """
    Weighted combination: 60% document, 40% web.
    If no web results, use document-only.
    """
    if web_conf == 0.0:
        return doc_conf
    return round(0.6 * doc_conf + 0.4 * web_conf, 3)


def refine_answer(
    original_answer: str,
    verdicts: List[Dict[str, Any]],
    sources: List[str],
) -> Dict[str, Any]:
    """
    Rewrite the original answer with verified claim information.
    Returns dual confidence scores.
    """
    doc_confidence = compute_document_confidence(verdicts)
    web_confidence = compute_web_confidence(verdicts)
    overall_confidence = compute_overall_confidence(doc_confidence, web_confidence)

    if not verdicts:
        return {
            "refined_answer": original_answer,
            "confidence_score": overall_confidence,
            "document_confidence": doc_confidence,
            "web_confidence": web_confidence,
            "removed_claims": [],
            "cited_sources": sources,
        }

    # Build verdict summary for the prompt
    verdict_lines = []
    removed_claims = []
    for v in verdicts:
        line = (
            f"- [{v['verdict'].upper()}] \"{v['claim']}\" "
            f"(doc_conf: {v.get('confidence', 0):.0%}, "
            f"risk: {v.get('hallucination_risk', 'unknown')}"
        )
        # Add web verdict if available
        if v.get("web_verdict"):
            line += f", web: {v['web_verdict']} {v.get('web_confidence', 0):.0%}"
        line += ")"
        verdict_lines.append(line)

        if v.get("verdict") in ("unsupported", "contradicted"):
            removed_claims.append(v["claim"])

    verdict_summary = "\n".join(verdict_lines)
    sources_list = "\n".join(f"[{i+1}] {s}" for i, s in enumerate(sources))

    user_message = f"""Original answer to rewrite:
{original_answer}

Claim verification results:
{verdict_summary}

Available sources:
{sources_list}

Rewrite the answer incorporating the verification results. \
Return ONLY a JSON object with this structure:
{{
  "refined_answer": "the rewritten, fact-checked answer with citations",
  "cited_sources": ["source1", "source2"]
}}"""

    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.1)
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])

        raw = response.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {
                "refined_answer": parsed.get("refined_answer", original_answer),
                "confidence_score": overall_confidence,
                "document_confidence": doc_confidence,
                "web_confidence": web_confidence,
                "removed_claims": removed_claims,
                "cited_sources": parsed.get("cited_sources", sources),
            }
    except Exception:
        pass

    return {
        "refined_answer": original_answer,
        "confidence_score": overall_confidence,
        "document_confidence": doc_confidence,
        "web_confidence": web_confidence,
        "removed_claims": removed_claims,
        "cited_sources": sources,
    }
