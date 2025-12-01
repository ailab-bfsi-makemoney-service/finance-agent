# intents/recurring_merchants.py

import json
from typing import Dict, Any

INTENT_NAME = "recurring_merchants"
KEYWORDS = [
    "recurring",
    "subscriptions",
    "bills every month",
    "regular payments",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    """Heuristic recurring merchants based on top merchants."""
    raw = retriever.query(question)
    data = json.loads(raw)

    merchants = data.get("top_merchants", [])
    matches = data.get("matches", 0)
    total = data.get("total_spend", 0.0)

    if merchants:
        formatted = ", ".join([f"{m} (${v:.2f})" for m, v in merchants])
        answer = (
            f"Based on your spend, these merchants are likely recurring: {formatted}.\n"
            f"(Heuristic based on top merchants across {matches} transactions, "
            f"totaling ${total:,.2f}.)"
        )
    else:
        answer = "I couldn't identify any likely recurring merchants based on the current data."

    details = {
        "matches": matches,
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
            "title": "Likely Recurring Merchants",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
