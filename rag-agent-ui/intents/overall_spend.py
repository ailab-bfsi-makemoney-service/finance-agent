from typing import Dict, Any, List, Tuple

INTENT_NAME = "overall_spend"
KEYWORDS = ["overall", "total", "all", "everything", "spend"]


def _normalize_pairs(pairs: List[Any], key_name: str) -> List[Dict[str, Any]]:
    """Convert [(name, amount), ...] or mixed into [{key_name, total_spend}, ...]."""
    normalized: List[Dict[str, Any]] = []
    for item in pairs:
        if isinstance(item, dict):
            # Assume already normalized
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
    Overall spend intent.

    Examples:
      "How much did I spend overall in June?"
      "Total FY25 spend"
      "How much did I spend in August?"
    """
    data = retriever.query(question)

    total = float(data.get("total_spend", 0.0))
    matches = int(data.get("matches", 0))

    top_merchants_raw = data.get("top_merchants", [])
    top_categories_raw = data.get("top_categories", [])
    top_cuisines_raw = data.get("top_cuisines", [])

    # Normalize to object arrays for UI (reusing "top_restaurants" slot for merchants)
    top_restaurants = _normalize_pairs(top_merchants_raw, "merchant")
    top_categories = _normalize_pairs(top_categories_raw, "category")
    top_cuisines = _normalize_pairs(top_cuisines_raw, "cuisine")

    # Build human answer
    answer = f"You spent ${total:,.2f} overall across {matches} transactions."

    # Details for UI
    details: Dict[str, Any] = {
        "matches": matches,
        "total_spend": round(total, 2),
        "top_restaurants": top_restaurants,  # merchants
        "top_categories": top_categories,
        "top_cuisines": top_cuisines,
    }

    # Chart: prefer category breakdown; fallback to merchants
    chart = None
    if top_categories:
        chart = {
            "title": "Overall spend by category",
            "type": "bar",
            "labels": [c["category"] for c in top_categories],
            "values": [c["total_spend"] for c in top_categories],
        }
    elif top_restaurants:
        chart = {
            "title": "Overall spend by merchant",
            "type": "bar",
            "labels": [m["merchant"] for m in top_restaurants],
            "values": [m["total_spend"] for m in top_restaurants],
        }

    # Pass through original data + enriched bits
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
