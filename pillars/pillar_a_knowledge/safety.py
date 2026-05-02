"""Hard refusal layer - deterministic safety checks."""

import re

# Investment advice keywords
INVESTMENT_ADVICE_PATTERNS = [
    r'\b(should i|recommend|best|which.*better|which.*invest|predict|forecast|will.*give|guaranteed.*return)',
    r'\b(buy|sell|hold|invest in|pick|choose.*fund|good time|right time)',
    r'\b(beat.*market|maximum.*profit|highest.*return|outperform)',
    r'\b(20%|30%|guaranteed|promise|sure.*return)',
    r'\b(will.*be|will.*become|tomorrow|next week|next month|future|going to)',
]

# PII request keywords
PII_PATTERNS = [
    r'\b(ceo|manager|advisor).*\b(email|phone|contact|mobile|number)',
    r'\b(account.*detail|account.*number|pan|aadhaar|aadhar)',
    r'\b(give me.*email|share.*email|tell.*phone|customer.*email)',
]


def is_investment_advice_request(query: str) -> bool:
    """Deterministic check for investment advice."""
    query_lower = query.lower()
    for pattern in INVESTMENT_ADVICE_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    return False


def is_pii_request(query: str) -> bool:
    """Deterministic check for PII requests."""
    query_lower = query.lower()
    for pattern in PII_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    return False


def check_safety(query: str) -> dict:
    """
    Hard safety check - returns refusal if unsafe.

    Returns:
        {"safe": True} or {"safe": False, "reason": "...", "message": "..."}
    """
    if is_investment_advice_request(query):
        return {
            "safe": False,
            "reason": "investment_advice",
            "message": (
                "I cannot provide investment advice or recommendations. "
                "I can only share factual information about mutual fund schemes from official sources. "
                "For investment decisions, please consult a SEBI-registered financial advisor."
            ),
        }

    if is_pii_request(query):
        return {
            "safe": False,
            "reason": "pii_request",
            "message": (
                "I cannot share personal information, contact details, or account information. "
                "For support inquiries, please visit the official INDmoney website or app."
            ),
        }

    return {"safe": True}
