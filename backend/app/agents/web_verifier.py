"""
Web Verifier Agent — Cross-checks claims against live web search results.

For each claim (prioritizing contradicted/unsupported ones):
  1. Searches DuckDuckGo for the claim text (strict 5s timeout)
  2. Asks Groq to evaluate web snippets against the claim
  3. Enriches the verdict with web evidence + source URLs

Caps at MAX_WEB_VERIFY claims to keep total pipeline time under 60s.
"""
from __future__ import annotations
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.web_search_service import web_search
from app.core.config import GROQ_API_KEY, GROQ_MODEL

# Only web-verify the most important claims to keep response time reasonable
MAX_WEB_VERIFY = 5
# Total seconds allowed for ALL web verifications combined
WEB_VERIFY_TOTAL_TIMEOUT = 40

SYSTEM_PROMPT = """You are a web fact-checker. Given a claim and web search snippets, \
determine if the web evidence supports, contradicts, or is inconclusive about the claim.

Return ONLY valid JSON:
{
  "web_verdict": "supported" | "contradicted" | "inconclusive",
  "web_confidence": 0.0 to 1.0,
  "reasoning": "brief explanation citing which web source(s)"
}
"""

_INCONCLUSIVE = {
    "web_verdict": "inconclusive",
    "web_confidence": 0.0,
    "web_reasoning": "Web verification skipped.",
    "web_sources": [],
}


def web_verify_claim(claim: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Search the web for a claim and evaluate the results.
    Returns inconclusive immediately if web search yields nothing.
    """
    results = web_search(claim, max_results=max_results)
    if not results:
        return {**_INCONCLUSIVE, "web_reasoning": "No web search results found."}

    search_block = "\n\n".join(
        f"[{i+1}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for i, r in enumerate(results)
    )

    user_message = f"""Claim to verify: "{claim}"

Web search results:
{search_block}

Evaluate whether these web results support or contradict the claim. Return ONLY the JSON."""

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
            return {
                "web_verdict": parsed.get("web_verdict", "inconclusive"),
                "web_confidence": round(float(parsed.get("web_confidence", 0.5)), 3),
                "web_reasoning": parsed.get("reasoning", ""),
                "web_sources": results,
            }
    except Exception as e:
        print(f"[WebVerifier] Error: {e}")

    return {
        "web_verdict": "inconclusive",
        "web_confidence": 0.3,
        "web_reasoning": "Could not parse web verification result.",
        "web_sources": results,
    }


def web_verify_claims(verdicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich claim verdicts with web search verification.
    - Only verifies the top MAX_WEB_VERIFY most important claims
      (prioritizing contradicted > unsupported > supported)
    - Uses a thread pool with a hard total timeout to prevent hanging
    - All other claims get 'inconclusive' placeholders
    """
    # Sort by priority: contradicted first, then unsupported, then supported
    priority_order = {"contradicted": 0, "unsupported": 1, "neutral": 2, "supported": 3}
    indexed = list(enumerate(verdicts))
    indexed_sorted = sorted(
        indexed,
        key=lambda t: priority_order.get(t[1].get("verdict", "neutral"), 2)
    )

    # Pick top N to actually web-verify
    to_verify_indices = {idx for idx, _ in indexed_sorted[:MAX_WEB_VERIFY]}

    enriched = [None] * len(verdicts)

    def _verify_one(idx_verdict):
        idx, v = idx_verdict
        if idx not in to_verify_indices:
            return idx, {**v, **_INCONCLUSIVE}
        try:
            web_result = web_verify_claim(v["claim"])
        except Exception as e:
            print(f"[WebVerifier] Claim {idx} failed: {e}")
            web_result = _INCONCLUSIVE
        return idx, {
            **v,
            "web_verdict": web_result["web_verdict"],
            "web_confidence": web_result["web_confidence"],
            "web_reasoning": web_result["web_reasoning"],
            "web_sources": web_result["web_sources"],
        }

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_verify_one, iv) for iv in indexed]
            for future in futures:
                try:
                    idx, result = future.result(timeout=WEB_VERIFY_TOTAL_TIMEOUT)
                    enriched[idx] = result
                except FuturesTimeout:
                    print("[WebVerifier] Timed out waiting for a claim verification")
    except Exception as e:
        print(f"[WebVerifier] Pool error: {e}")

    # Fill any None slots (timed-out claims) with inconclusive placeholders
    for i, v in enumerate(verdicts):
        if enriched[i] is None:
            enriched[i] = {**v, **_INCONCLUSIVE}

    return enriched
