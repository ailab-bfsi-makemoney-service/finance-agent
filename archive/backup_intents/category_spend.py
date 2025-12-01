# intents/category_spend.py

import json
from typing import Dict, Any

from .utils_date import describe_period

INTENT_NAME = "category_spend"
KEYWORDS = [
    "category",
    "shopping",
    "utilities",
    "bills",
    "gas",
    "groceries",
    "grocery",
    "health",
    "travel",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    raw = retriever.query(question)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)
    period_label = describe_period(question)

    cats = data.get("top_categories", [])
    category_name = cats[0][0] if cats else None

    if category_name:
        answer = (
            f"You spent ${total:,.2f} in '{category_name}' during {period_label}, "
            f"across {matches} transactions."
        )
    else:
        answer = (
            f"Category spend in {period_label} is ${total:,.2f} "
            f"across {matches} transactions."
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
            "title": "Category Breakdown",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
