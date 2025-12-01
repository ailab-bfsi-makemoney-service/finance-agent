# intents/overall_spend.py

import json
from typing import Dict, Any

from .utils_date import describe_period

INTENT_NAME = "overall_spend"
KEYWORDS = [
    "overall",
    "total spend",
    "how much did i spend",
    "all categories",
    "everything",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    # Encourage retriever to include all categories
    q2 = question + " include all categories"
    raw = retriever.query(q2)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)
    period_label = describe_period(question)

    answer = (
        f"Your overall spend in {period_label} is ${total:,.2f}, "
        f"across {matches} transactions."
    )

    details = {
        "matches": matches,
        "top_merchants": data.get("top_merchants", []),
        "top_categories": data.get("top_categories", []),
        "top_cuisines": data.get("top_cuisines", []),
    }

    chart = None
    if data.get("top_categories"):
        chart = {
            "type": "bar",
            "labels": [c for c, _ in data["top_categories"]],
            "values": [v for _, v in data["top_categories"]],
            "title": "Category Breakdown",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
