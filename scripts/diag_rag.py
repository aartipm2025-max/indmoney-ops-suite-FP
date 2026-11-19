from dotenv import load_dotenv; load_dotenv()
from pillars.pillar_a_knowledge.answerer import ask
import re, json

tests = [
    ("Q001", "What is the exit load for SBI Bluechip Fund?", ["0.25%", "30 days"]),
    ("Q002", "What is the exit load for the ELSS fund and why is there no exit load?", ["NIL", "3-year", "lock-in"]),
    ("Q005", "What is exit load and how is it calculated?", ["percentage", "NAV"]),
    ("Q006", "What is the benchmark for SBI Large Cap Fund?", ["Nifty", "BSE"]),
    ("Q008", "What is the taxation on ELSS fund redemptions?", ["LTCG", "tax"]),
    ("Q009", "What edge cases exist with exit loads?", ["edge", "lock-in"]),
]

for qid, q, expected in tests:
    r = ask(q)
    if r.get("error") or r.get("refused"):
        print(f"{qid}: FAIL — {str(r.get('message',''))[:100]}")
        continue
    answer = " ".join(b.get("text","") for b in r.get("bullets",[]))
    sources = re.findall(r"\[source:([^\]]+)\]", answer)
    hits = [k for k in expected if k.lower() in answer.lower()]
    faith = "PASS" if sources else "FAIL(no citations)"
    rel = "PASS" if len(hits)/len(expected) >= 0.5 else f"FAIL(hits={hits})"
    print(f"{qid}: faith={faith} rel={rel}")
