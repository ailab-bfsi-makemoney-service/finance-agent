# intents/large_purchases.py

import json
from typing import Dict, Any

INTENT_NAME = "large_purchases"
KEYWORDS = [
    "large purchases",
    "big transactions",
    "high value",
    "big spend",
]


def handle(question: str, retriever) -> Dict[str, Any]:
    """Placeholder: summarise overall spend, note that detailed breakdown isn't implemented."""
    raw = retriever.query(question)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)

    answer = (
        f"Your total spend in the selected period is ${total:,.2f} "
        f"across {matches} transactions. A detailed large-purchase breakdown "
        f"is not fully implemented yet in this version."
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
