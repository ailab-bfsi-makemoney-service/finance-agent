# intents/compare_months.py

import json
from typing import Dict, Any

from .utils_date import MONTHS

INTENT_NAME = "compare_months"
KEYWORDS = [
    "compare months",
    "compare spending",
    "vs",
    "versus",
]


def _month_name(idx: int) -> str:
    for name, i in MONTHS.items():
        if i == idx:
            return name.title()
    return f"Month {idx}"


def handle(question: str, retriever) -> Dict[str, Any]:
    """Simple comparison between two mentioned months in 2025."""
    q = question.lower()
    months_found = [m for m, _ in MONTHS.items() if m in q]
    months_found = list(dict.fromkeys(months_found))  # dedupe, preserve order

    if len(months_found) < 2:
        # fallback to single-month summary behavior
        raw = retriever.query(question)
        data = json.loads(raw)
        total = data.get("total_spend", 0.0)
        matches = data.get("matches", 0)
        answer = (
            f"I couldn't clearly detect two months to compare. "
            f"Here's what I found: ${total:,.2f} from {matches} transactions."
        )
        details = {
            "matches": matches,
            "top_merchants": data.get("top_merchants", []),
            "top_categories": data.get("top_categories", []),
            "top_cuisines": data.get("top_cuisines", []),
        }
        return {
            "intent": INTENT_NAME,
            "answer": answer,
            "details": details,
            "chart": None,
            "data": data,
        }

    # take first two months mentioned
    m1_name, m2_name = months_found[0], months_found[1]

    q1 = f"How much did I spend overall in {m1_name} 2025?"
    q2 = f"How much did I spend overall in {m2_name} 2025?"

    raw1 = retriever.query(q1)
    raw2 = retriever.query(q2)
    d1 = json.loads(raw1)
    d2 = json.loads(raw2)

    t1 = d1.get("total_spend", 0.0)
    t2 = d2.get("total_spend", 0.0)

    answer = (
        f"In {m1_name.title()} 2025 you spent ${t1:,.2f}, "
        f"and in {m2_name.title()} 2025 you spent ${t2:,.2f}. "
    )
    if t1 > t2:
        answer += f"You spent ${t1 - t2:,.2f} more in {m1_name.title()}."
    elif t2 > t1:
        answer += f"You spent ${t2 - t1:,.2f} more in {m2_name.title()}."
    else:
        answer += "Your spending was the same in both months."

    details = {
        "matches": (d1.get("matches", 0) + d2.get("matches", 0)),
        "top_merchants": [],
        "top_categories": [],
        "top_cuisines": [],
    }

    chart = {
        "type": "bar",
        "labels": [f"{m1_name.title()} 2025", f"{m2_name.title()} 2025"],
        "values": [t1, t2],
        "title": "Month-over-Month Spend Comparison",
    }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": {
            "month1": {"name": f"{m1_name.title()} 2025", "total_spend": t1},
            "month2": {"name": f"{m2_name.title()} 2025", "total_spend": t2},
        },
    }
