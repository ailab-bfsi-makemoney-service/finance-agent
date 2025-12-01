from typing import Dict, Any
INTENT_NAME = "fallback"
KEYWORDS = []
def handle(question: str, intent_name: str, metadata, retriever):
    raw = retriever.query(question)
    import json
    data = raw if isinstance(raw, dict) else json.loads(raw)
    total = data.get("total_spend") or data.get("total") or 0.0
    matches = data.get("matches", 0)
    answer = f"You spent ${total:,.2f} across {matches} transactions."
    details = {
        "matches": matches,
        "top_merchants": data.get("top_merchants", []),
        "top_categories": data.get("top_categories", []),
        "top_cuisines": data.get("top_cuisines", []),
    }
    return {"intent": INTENT_NAME, "answer": answer, "details": details, "chart": None, "data": data}
