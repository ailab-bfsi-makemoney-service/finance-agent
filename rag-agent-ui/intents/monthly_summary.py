from typing import Dict, Any, List
import re

INTENT_NAME = "monthly_summary"
KEYWORDS = [
    "summary",
    "breakdown",
    "overview",
    "snapshot",
    "monthly",
]


MONTHS = {
    "january": "January",
    "february": "February",
    "march": "March",
    "april": "April",
    "may": "May",
    "june": "June",
    "july": "July",
    "august": "August",
    "september": "September",
    "october": "October",
    "november": "November",
    "december": "December",
}


def _normalize_pairs(pairs: List[Any], key_name: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in pairs:
        if isinstance(item, dict):
            if key_name in item and "total_spend" in item:
                normalized.append(item)
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            name, amt = item[0], item[1]
            try:
                amount = float(amt)
            except Exception:
                continue
            normalized.append({key_name: str(name), "total_spend": round(amount, 2)})
    return normalized


def _extract_month_label(question: str) -> str:
    q = question.lower()
    for key, label in MONTHS.items():
        if re.search(rf"\b{key}\b", q):
            return label
    return "this period"


def handle(question: str, intent_name: str, metadata, retriever) -> Dict[str, Any]:
    """
    Monthly summary intent.

    Examples:
      "Give me a summary for June"
      "What is my August breakdown?"
      "Monthly overview for September?"
    """
    data = retriever.query(question)

    total = float(data.get("total_spend", 0.0))
    matches = int(data.get("matches", 0))

    top_merchants_raw = data.get("top_merchants", [])
    top_categories_raw = data.get("top_categories", [])
    top_cuisines_raw = data.get("top_cuisines", [])

    top_restaurants = _normalize_pairs(top_merchants_raw, "merchant")
    top_categories = _normalize_pairs(top_categories_raw, "category")
    top_cuisines = _normalize_pairs(top_cuisines_raw, "cuisine")

    month_label = _extract_month_label(question)

    answer = (
        f"In {month_label}, you spent ${total:,.2f} across {matches} transactions. "
        "Here’s a breakdown by category and merchant."
    )

    details: Dict[str, Any] = {
        "matches": matches,
        "total_spend": round(total, 2),
        "top_restaurants": top_restaurants,  # merchants
        "top_categories": top_categories,
        "top_cuisines": top_cuisines,
    }

    chart = None
    if top_categories:
        chart = {
            "title": f"{month_label} spend by category",
            "type": "bar",
            "labels": [c["category"] for c in top_categories],
            "values": [c["total_spend"] for c in top_categories],
        }
    elif top_restaurants:
        chart = {
            "title": f"{month_label} spend by merchant",
            "type": "bar",
            "labels": [m["merchant"] for m in top_restaurants],
            "values": [m["total_spend"] for m in top_restaurants],
        }

    full_data = dict(data)
    full_data["total_spend"] = round(total, 2)
    full_data["top_restaurants"] = top_restaurants
    full_data["top_categories"] = top_categories
    full_data["top_cuisines"] = top_cuisines

    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": full_data,
    }
