def judge_faithfulness_simple(answer: str, sources: list[str]) -> dict:
    """Simple check: Does answer have source citations?"""
    if not sources or len(sources) == 0:
        return {"score": 0.0, "reasoning": "No sources cited"}

    word_count = len(answer.split())
    if word_count > 200:
        return {"score": 0.5, "reasoning": "Answer may contain extra info"}

    return {"score": 1.0, "reasoning": "Sources present, length appropriate"}


def judge_relevance_simple(answer: str, expected_contains: list[str]) -> dict:
    """Simple check: Does answer contain expected keywords?"""
    answer_lower = answer.lower()

    matches = sum(1 for keyword in expected_contains if keyword.lower() in answer_lower)
    match_ratio = matches / len(expected_contains) if expected_contains else 0

    if match_ratio >= 0.5:
        return {"score": 1.0, "reasoning": f"Contains {matches}/{len(expected_contains)} expected concepts"}
    elif match_ratio >= 0.3:
        return {"score": 0.5, "reasoning": f"Partial match: {matches}/{len(expected_contains)}"}
    else:
        return {"score": 0.0, "reasoning": f"Missing key concepts: {matches}/{len(expected_contains)}"}


# Aliases for backward compatibility
def judge_faithfulness(question: str, answer: str, sources: list[str]) -> dict:
    return judge_faithfulness_simple(answer, sources)


def judge_relevance(question: str, answer: str, expected_contains: list[str]) -> dict:
    return judge_relevance_simple(answer, expected_contains)
