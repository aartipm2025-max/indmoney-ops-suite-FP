import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
import json


def judge_faithfulness(question: str, answer: str, sources: list[str]) -> dict:
    """Judge if answer stays within provided sources."""

    client = Groq()

    prompt = f"""You are evaluating RAG faithfulness. Check if the answer only uses information from the cited sources.

Question: {question}
Answer: {answer}
Sources cited: {', '.join(sources)}

Score 1.0 if ALL facts in the answer can be traced to cited sources.
Score 0.5 if MOST facts are supported.
Score 0.0 if answer contains facts NOT in sources.

Reply ONLY with JSON:
{{"score": 0.0 or 0.5 or 1.0, "reasoning": "brief explanation"}}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    return json.loads(response.choices[0].message.content)


def judge_relevance(question: str, answer: str, expected_contains: list[str]) -> dict:
    """Judge if answer actually answers the question."""

    client = Groq()

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

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    return json.loads(response.choices[0].message.content)
