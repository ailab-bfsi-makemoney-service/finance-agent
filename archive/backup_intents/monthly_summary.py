# intents/monthly_summary.py

import json
from typing import Dict, Any

from .utils_date import describe_period

INTENT_NAME = "monthly_summary"
KEYWORDS = [
    "summary",
    "month summary",
    "spending summary",
    "monthly breakdown",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    raw = retriever.query(question)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)
    period_label = describe_period(question)

    cats = data.get("top_categories", [])
    if cats:
        top_cat_name, top_cat_val = cats[0]
        answer = (
            f"In {period_label}, you spent ${total:,.2f} across {matches} transactions. "
            f"Your top category was '{top_cat_name}' (${top_cat_val:,.2f})."
        )
    else:
        answer = (
            f"In {period_label}, you spent ${total:,.2f} across {matches} transactions."
        )

    details = {
        "matches": matches,
        "top_merchants": data.get("top_merchants", []),
        "top_categories": cats,
        "top_cuisines": data.get("top_cuisines", []),
    }

    chart = None
    if cats:
        chart = {
            "type": "bar",
            "labels": [c for c, _ in cats],
            "values": [v for _, v in cats],
            "title": f"Category Summary – {period_label}",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
