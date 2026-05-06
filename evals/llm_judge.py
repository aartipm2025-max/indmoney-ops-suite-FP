import sys
import time
import json
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq


def _call_with_retry(prompt: str, max_retries: int = 4) -> str:
    """Call Groq with exponential backoff on rate-limit errors."""
    client = Groq()
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            if attempt < max_retries - 1 and (
                "rate" in str(exc).lower() or "429" in str(exc)
            ):
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                raise
    return ""


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM response, tolerating markdown code fences."""
    text = raw.strip()
    # Strip ```json ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        # Last resort: extract first number after "score"
        m = re.search(r'"score"\s*:\s*([01](?:\.\d+)?)', text)
        return {"score": float(m.group(1)) if m else 0.0, "reasoning": "parse fallback"}


def judge_faithfulness(question: str, answer: str, sources: list[str]) -> dict:
    """Judge if answer stays within provided sources."""
    prompt = f"""You are evaluating RAG faithfulness. Check if the answer only uses information from the cited sources.

Question: {question}
Answer: {answer}
Sources cited: {', '.join(sources) if sources else '(none)'}

Score 1.0 if ALL facts in the answer can be traced to cited sources.
Score 0.5 if MOST facts are supported.
Score 0.0 if answer contains facts NOT in sources, or if no sources are cited.

Reply ONLY with JSON:
{{"score": 0.0 or 0.5 or 1.0, "reasoning": "brief explanation"}}
"""
    raw = _call_with_retry(prompt)
    return _parse_json(raw)


def judge_relevance(question: str, answer: str, expected_contains: list[str]) -> dict:
    """Judge if answer actually answers the question."""
    prompt = f"""You are evaluating RAG relevance. Check if the answer addresses the user's question.

Question: {question}
Answer: {answer}
Expected concepts: {', '.join(expected_contains)}

Score 1.0 if answer directly addresses the question and covers expected concepts.
Score 0.5 if partially relevant but misses key concepts.
Score 0.0 if off-topic or doesn't address the question.

Reply ONLY with JSON:
{{"score": 0.0 or 0.5 or 1.0, "reasoning": "brief explanation"}}
"""
    raw = _call_with_retry(prompt)
    return _parse_json(raw)
