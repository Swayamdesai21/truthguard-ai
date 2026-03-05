"""
Consistency Checker Agent — Detects cross-claim contradictions and hallucination risks.

Input:  list of claim verdicts (from fact_checker)
Output: enriched list with hallucination_risk and cross-contradiction flags

Two checks:
1. Cross-claim self-contradictions (via LLM)
2. Risk tagging based on verdict (contradicted = high risk, unsupported = medium)
"""
from __future__ import annotations
import json
import re
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """You are a logical consistency checker. Given a list of factual claims, \
identify pairs that directly contradict each other.

Return ONLY a valid JSON object:
{
  "contradictions": [
    {
      "claim_a_index": 0,
      "claim_b_index": 2,
      "explanation": "brief reason why they contradict"
    }
  ]
}

If no contradictions exist, return: {"contradictions": []}
"""


def check_consistency(verdicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich claim verdicts with hallucination risk levels and cross-contradiction flags.

    Returns the same list with added fields:
        - hallucination_risk: "high" | "medium" | "low"
        - cross_contradiction: bool
        - cross_contradiction_with: list[int] (indices)
    """
    if not verdicts:
        return []

    # Step 1: Tag risk based on individual verdict
    enriched = []
    for v in verdicts:
        verdict = v.get("verdict", "unsupported")
        confidence = v.get("confidence", 0.5)

        if verdict == "contradicted":
            risk = "high"
        elif verdict == "unsupported" or confidence < 0.5:
            risk = "medium"
        else:
            risk = "low"

        enriched.append({
            **v,
            "hallucination_risk": risk,
            "cross_contradiction": False,
            "cross_contradiction_with": [],
        })

    # Step 2: Check cross-claim contradictions (only if ≥2 claims)
    if len(verdicts) < 2:
        return enriched

    claims_text = "\n".join(
        f"[{i}] {v['claim']}" for i, v in enumerate(verdicts)
    )

    user_message = f"""Check these claims for logical contradictions:

{claims_text}

Return the JSON object with any contradicting pairs."""

    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.0)
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])

        raw = response.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            contradictions = parsed.get("contradictions", [])

            for contradiction in contradictions:
                idx_a = contradiction.get("claim_a_index", -1)
                idx_b = contradiction.get("claim_b_index", -1)
                if 0 <= idx_a < len(enriched) and 0 <= idx_b < len(enriched):
                    enriched[idx_a]["cross_contradiction"] = True
                    enriched[idx_a]["cross_contradiction_with"].append(idx_b)
                    enriched[idx_b]["cross_contradiction"] = True
                    enriched[idx_b]["cross_contradiction_with"].append(idx_a)
                    # Escalate risk
                    if enriched[idx_a]["hallucination_risk"] == "low":
                        enriched[idx_a]["hallucination_risk"] = "medium"
                    if enriched[idx_b]["hallucination_risk"] == "low":
                        enriched[idx_b]["hallucination_risk"] = "medium"
    except Exception:
        # Non-fatal: consistency check is best-effort
        pass

    return enriched
