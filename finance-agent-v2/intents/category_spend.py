from typing import Dict, Any, List

INTENT_NAME = "category_spend"
KEYWORDS = [
    "category",
    "categories",
    "shopping",
    "groceries",
    "grocery",
    "gas",
    "fuel",
    "bills",
    "utilities",
    "entertainment",
    "travel",
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
    Category spend intent.

    Examples:
      "How much did I spend on Shopping in June?"
      "Gas spend in August?"
      "What did I spend on Groceries in May?"
    """

    # Use same query pipeline; retriever will apply category filter based on question
    data = retriever.query(question)

    total = float(data.get("total_spend", 0.0))
    matches = int(data.get("matches", 0))

    top_merchants_raw = data.get("top_merchants", [])
    top_categories_raw = data.get("top_categories", [])
    top_cuisines_raw = data.get("top_cuisines", [])

    top_restaurants = _normalize_pairs(top_merchants_raw, "merchant")
    top_categories = _normalize_pairs(top_categories_raw, "category")
    top_cuisines = _normalize_pairs(top_cuisines_raw, "cuisine")

    # Try to infer category name from canonical map used by retriever
    requested_cats = retriever._requested_categories(question)  # type: ignore[attr-defined]
    if requested_cats:
        category_label = ", ".join(requested_cats)
    elif top_categories:
        category_label = top_categories[0]["category"]
    else:
        category_label = "the selected category"

    answer = (
        f"You spent ${total:,.2f} in {category_label} across {matches} transactions."
    )

    details: Dict[str, Any] = {
        "matches": matches,
        "total_spend": round(total, 2),
        "top_restaurants": top_restaurants,  # merchants
        "top_categories": top_categories,
        "top_cuisines": top_cuisines,
    }

    # Chart: for a single category, merchant breakdown is usually more interesting
    chart = None
    if top_restaurants:
        chart = {
            "title": f"Spend by merchant in {category_label}",
            "type": "bar",
            "labels": [m["merchant"] for m in top_restaurants],
            "values": [m["total_spend"] for m in top_restaurants],
        }
    elif top_categories:
        chart = {
            "title": f"{category_label} category breakdown",
            "type": "bar",
            "labels": [c["category"] for c in top_categories],
            "values": [c["total_spend"] for c in top_categories],
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
