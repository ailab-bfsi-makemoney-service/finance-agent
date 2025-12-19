from typing import Dict, Any, List

INTENT_NAME = "restaurant_spend"
KEYWORDS = [
    "restaurant", "restaurants",
    "dining", "dine",
    "food", "meal", "meals",
    "eat", "ate", "eating",
    "cuisine", "cuisines",
    "lunch", "dinner", "breakfast"
]


def handle(question: str, intent: str, metadata: List[Any], retriever) -> Dict[str, Any]:
    """
    Handles restaurant spending queries.
    Standardized return shape for UI compatibility.
    """

    # Pull structured restaurant data from retriever
    data = retriever.get_restaurant_spend(question)

    # Extract known fields (retriever_v2 uses these names)
    total_spend = data.get("total_restaurant_spend", 0.0)
    total_visits = data.get("total_visits", 0)
    top_restaurants = data.get("top_restaurants", [])
    top_cuisines = data.get("top_cuisines", [])
    top_categories = data.get("top_categories", [])

    # UI summary answer
    answer = (
        f"You spent ${total_spend:,.2f} at restaurants "
        f"across {total_visits} visits."
    )

    # Details block for UI
    details = {
        "total_restaurant_spend": total_spend,
        "total_visits": total_visits,
        "top_restaurants": top_restaurants,
        "top_cuisines": top_cuisines,
        "top_categories": top_categories,
    }

    # Build chart data (UI expects dict with labels and values)
    labels = [r.get("merchant", "") for r in top_restaurants]
    values = [r.get("total_spend", 0.0) for r in top_restaurants]

    chart = {
        "labels": labels,
        "values": values
    }

    # Final return structure
    return {
        "intent": INTENT_NAME,
        "answer": answer,
        "details": details,
        "chart": chart,
        "data": data
    }

