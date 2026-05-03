"""
pillars/pillar_a_knowledge/router.py

Routes user queries to the correct retrieval scope.
"""
from __future__ import annotations

import re
from typing import Literal

from core.llm_client import LLMClient
from core.logger import log

RouteResult = Literal["fact_only", "fee_only", "both", "refuse"]

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_ADVICE_RE = re.compile(
    r"\b(should\s+i\s+(buy|sell|invest|switch|redeem)"
    r"|which\s+fund\s+is\s+best"
    r"|recommend(ation|ed)?"
    r"|predict(ion|ed)?"
    r"|will\s+(returns?|nav|price)\s+(go|rise|fall|increase|decrease)"
    r"|best\s+fund|top\s+fund|better\s+fund)\b",
    re.IGNORECASE,
)

_PII_RE = re.compile(
    r"\b(email|phone\s+number|pan\s+number|aadhaar|account\s+number"
    r"|mobile\s+number|ceo\s+email|personal\s+details|contact\s+details"
    r"|manager\s+contact)\b",
    re.IGNORECASE,
)

# exit load + explanation-seeking word → both
_EXIT_LOAD_CONTEXT_RE = re.compile(
    r"\bexit\s+load\b.{0,60}\b(why|how|charged|charge|fee)\b"
    r"|\b(why|how|charged|charge|fee)\b.{0,60}\bexit\s+load\b",
    re.IGNORECASE,
)

_FEE_RE = re.compile(
    r"\b(fee|charge|cost|exit\s+load|expense\s+ratio\s+deduction|brokerage)\b",
    re.IGNORECASE,
)

_FUND_NAME_RE = re.compile(
    r"\bsbi\s+(bluechip|blue\s+chip|small\s*cap|equity\s+hybrid"
    r"|midcap|mid\s*cap|elss|long\s+term\s+equity|large\s*cap)\b",
    re.IGNORECASE,
)

_VALID_ROUTES: frozenset[str] = frozenset(["fact_only", "fee_only", "both"])

_ROUTER_SYSTEM_PROMPT = (
    "You are a query classifier for a mutual fund FAQ system. "
    "Classify the user query into exactly one category: "
    "fact_only (asking about a specific fund's details like NAV, AUM, holdings, SIP minimum), "
    "fee_only (asking about fees, charges, exit loads in general), "
    "or both (asking about a specific fund's fee AND wanting an explanation). "
    "Reply with ONLY the category word, nothing else."
)


def route_query(query: str, _safety_checked: bool = False) -> RouteResult:
    """Route a query. Pass _safety_checked=True if ask() already ran check_safety()."""
    preview = query[:80]

    # Safety check — skipped when ask() already ran it to avoid duplicate work
    if not _safety_checked:
        from pillars.pillar_a_knowledge.safety import check_safety
        safety_result = check_safety(query)
        if not safety_result["safe"]:
            log.info("router: query='{}...' → refuse (safety layer: {})", preview, safety_result["reason"])
            return "refuse"

    # Compiled-regex safety backstop (cheap, catches edge cases)
    if _ADVICE_RE.search(query):
        log.info("router: query='{}...' → refuse (investment advice pattern)", preview)
        return "refuse"
    if _PII_RE.search(query):
        log.info("router: query='{}...' → refuse (PII pattern)", preview)
        return "refuse"

    query_lower = query.lower()

    # Additional refusal patterns (edge cases not caught by compiled regex above)
    for pattern in (
        r'\b(should i|recommend|which.*better|predict|forecast)',
        r'\b(buy|sell|invest in|good time)',
        r'\b(email|phone|pan|aadhaar|account.*number)',
    ):
        if re.search(pattern, query_lower):
            log.info("router: query='{}...' → refuse (explicit pattern)", preview)
            return "refuse"

    # ── Fast boolean routing — order-agnostic, catches ~90% of queries ──────
    # Presence of a specific SBI fund name
    has_fund = bool(re.search(
        r'\b(sbi|bluechip|blue\s*chip|small\s*cap|midcap|mid\s*cap'
        r'|equity\s+hybrid|elss|long\s+term\s+equity)\b',
        query_lower,
    ))
    # Presence of any fee/cost keyword (expense ratio included)
    has_fee = bool(re.search(
        r'\b(exit\s+load|expense\s+ratio|redemption\s+(charge|fee)'
        r'|fee|charge|cost|tds|stamp\s+duty)\b',
        query_lower,
    ))

    if has_fund and has_fee:
        log.info("router: query='{}...' → both (fund + fee keyword)", preview)
        return "both"

    if has_fund:
        log.info("router: query='{}...' → fact_only (fund name, no fee keyword)", preview)
        return "fact_only"

    if has_fee:
        log.info("router: query='{}...' → fee_only (fee keyword, no fund name)", preview)
        return "fee_only"

    # ── Compiled-regex fallback (catches fund/fee patterns missed above) ─────
    if _EXIT_LOAD_CONTEXT_RE.search(query):
        log.info("router: query='{}...' → both (exit load + context)", preview)
        return "both"
    if _FEE_RE.search(query):
        log.info("router: query='{}...' → fee_only (compiled fee regex)", preview)
        return "fee_only"
    if _FUND_NAME_RE.search(query):
        log.info("router: query='{}...' → fact_only (compiled fund regex)", preview)
        return "fact_only"

    # LLM fallback — only fires when query has neither fund name nor fee keyword
    log.info("router: no regex match — calling LLM for query='{}'", preview)
    client = LLMClient()
    for attempt in range(2):
        try:
            raw = client.chat(
                messages=[
                    {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                model="fast",
                temperature=0.0,
                max_tokens=10,
            )
            route = raw.strip().lower()
            if route in _VALID_ROUTES:
                log.info(
                    "router: LLM attempt={} → {} for query='{}'",
                    attempt + 1,
                    route,
                    preview,
                )
                return route  # type: ignore[return-value]
            log.warning(
                "router: LLM returned invalid route '{}' (attempt {})", route, attempt + 1
            )
        except Exception as exc:
            log.warning(
                "router: LLM call failed attempt={} exc={}", attempt + 1, str(exc)[:100]
            )

    log.warning(
        "router: defaulting to 'both' after retries exhausted for query='{}'", preview
    )
    return "both"
