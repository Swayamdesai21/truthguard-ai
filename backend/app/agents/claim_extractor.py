"""
Claim Extractor Agent — Splits an answer into atomic, verifiable claims.

Input:  answer (str)
Output: list[str] — each item is one atomic factual claim

Uses Groq with a few-shot prompt to extract claims that can be independently verified.
"""
from __future__ import annotations
import json
import re
from typing import List

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """You are a claim extraction specialist. Extract the MOST IMPORTANT atomic factual claims.

Rules:
- Each claim must be a single, self-contained factual statement
- Each claim must be independently verifiable
- Remove filler phrases like "According to...", "The document states..."
- Keep proper nouns, numbers, and specific details
- Return ONLY a valid JSON array of strings, no other text
- Extract a MAXIMUM of 8 claims total — choose the most important ones

Example:
Answer: "Tesla was founded in 2003 by Martin Eberhard. Elon Musk joined as chairman in 2004 and became CEO in 2008."

Output:
["Tesla was founded in 2003.", "Tesla was founded by Martin Eberhard.", "Elon Musk joined Tesla as chairman in 2004.", "Elon Musk became CEO of Tesla in 2008."]
"""


def extract_claims(answer: str) -> List[str]:
    """
    Extract atomic factual claims from a generated answer.

    Returns a list of claim strings.
    Falls back to sentence splitting if LLM fails to return valid JSON.
    """
    if not answer or len(answer.strip()) < 10:
        return []

    user_message = f"""Extract all atomic factual claims from this answer as a JSON array:

Answer: {answer}

Return ONLY the JSON array, nothing else."""

    llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.0)
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    raw = response.content.strip()

    # Try to parse JSON
    try:
        # Extract JSON array even if there's surrounding text
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            claims = json.loads(match.group())
            if isinstance(claims, list):
                # Hard cap at 8 claims to keep pipeline fast
                return [str(c).strip() for c in claims[:8] if c and len(str(c).strip()) > 5]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', answer.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]
