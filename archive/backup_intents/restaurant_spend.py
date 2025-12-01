# intents/restaurant_spend.py

import json
from typing import Dict, Any

from .utils_date import describe_period

INTENT_NAME = "restaurant_spend"
KEYWORDS = [
    "restaurant",
    "restaurants",
    "dining",
    "food",
    "eat out",
    "lunch",
    "dinner",
    "cafe",
    "breakfast",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    raw = retriever.query(question)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)
    period_label = describe_period(question)

    answer = (
        f"You spent ${total:,.2f} at restaurants in {period_label} "
        f"across {matches} transactions."
    )

    details = {
        "matches": matches,
        "top_merchants": data.get("top_merchants", []),
        "top_categories": data.get("top_categories", []),
        "top_cuisines": data.get("top_cuisines", []),
    }

    chart = None
    if data.get("top_merchants"):
        chart = {
            "type": "bar",
            "labels": [m for m, _ in data["top_merchants"]],
            "values": [v for _, v in data["top_merchants"]],
            "title": "Top Restaurant Merchants",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
