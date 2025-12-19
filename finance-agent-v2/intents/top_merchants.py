from typing import Dict, Any, List

INTENT_NAME = "top_merchants"
KEYWORDS = [
    "top merchants",
    "top merchant",
    "largest merchants",
    "biggest merchants",
    "favorite merchants",
    "top spend",
]


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


def handle(question: str, intent_name: str, metadata, retriever) -> Dict[str, Any]:
    """
    Top merchants intent.

    Examples:
      "What are my top merchants in FY25?"
      "Top merchants in August?"
      "Who did I spend the most with in June?"
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

    # Build a human-friendly list of top names
    if top_restaurants:
        names = [m["merchant"] for m in top_restaurants[:3]]
        name_list = ", ".join(names)
        answer = (
            f"Your top merchants by spend are {name_list}, "
            f"with a total of ${total:,.2f} across {matches} transactions."
        )
    else:
        answer = (
            f"I found ${total:,.2f} in spend across {matches} transactions, "
            "but could not identify distinct top merchants."
        )

    details: Dict[str, Any] = {
        "matches": matches,
        "total_spend": round(total, 2),
        "top_restaurants": top_restaurants,  # merchants
        "top_categories": top_categories,
        "top_cuisines": top_cuisines,
    }

    chart = None
    if top_restaurants:
        chart = {
            "title": "Top merchants by spend",
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

