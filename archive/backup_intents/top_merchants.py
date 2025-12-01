# intents/top_merchants.py

import json
from typing import Dict, Any

from .utils_date import describe_period

INTENT_NAME = "top_merchants"
KEYWORDS = [
    "top merchants",
    "top vendors",
    "top stores",
    "most spent",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    raw = retriever.query(question)
    data = json.loads(raw)

    merchants = data.get("top_merchants", [])
    period_label = describe_period(question)

    if merchants:
        formatted = ", ".join([f"{m} (${v:.2f})" for m, v in merchants])
        answer = f"Your top merchants in {period_label} are: {formatted}."
    else:
        answer = f"I couldn't find any top merchants for {period_label}."

    details = {
        "matches": data.get("matches", 0),
        "top_merchants": merchants,
        "top_categories": data.get("top_categories", []),
        "top_cuisines": data.get("top_cuisines", []),
    }

    chart = None
    if merchants:
        chart = {
            "type": "bar",
            "labels": [m for m, _ in merchants],
            "values": [v for _, v in merchants],
            "title": "Top Merchants",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
