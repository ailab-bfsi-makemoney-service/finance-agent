# intents/fallback.py

import json
from typing import Dict, Any

INTENT_NAME = "fallback"
KEYWORDS = []  # never directly matched; router uses this as default


def handle(question: str, retriever) -> Dict[str, Any]:
    raw = retriever.query(question)
    data = json.loads(raw)

    total = data.get("total_spend", 0.0)
    matches = data.get("matches", 0)

    answer = (
        "Here's what I found based on your question.\n\n"
        f"Approximate spend: ${total:,.2f} from {matches} transactions."
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
