# intents/overall_spend.py
import json
from typing import Dict, Any, Union

from .utils_date import describe_period

INTENT_NAME = "overall_spend"
KEYWORDS = [
    "overall",
    "total spend",
    "how much did i spend",
    "all categories",
    "everything",
]


def _safe_load(raw: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Accepts either a JSON string or a dict.
    Ensures output is always a Python dict.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            pass
    # fallback empty structure
    return {}


def handle(question: str, retriever) -> Dict[str, Any]:
    """
    Computes overall spend across all categories and merchants.
    """

    # Encourage maximum recall from retriever
    q2 = question + " include all categories"

    raw = retriever.query(q2)
    data = _safe_load(raw)

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

    # Build chart ONLY if categories exist
    chart = None
    top_cats = data.get("top_categories")
    if top_cats:
        chart = {
            "type": "bar",
            "labels": [c for c, _ in top_cats],
            "values": [v for _, v in top_cats],
            "title": "Category Breakdown",
        }

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data,
    }
