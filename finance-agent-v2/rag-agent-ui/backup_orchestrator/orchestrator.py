# orchestrator/orchestrator.py

import json
from typing import Dict, Any

from rag.retriever_v2 import RAGRetriever
from orchestrator.intent_router import IntentRouter

# Import intent modules
from intents import (
    restaurant_spend,
    overall_spend,
    category_spend,
    monthly_summary,
    compare_months,
    top_merchants,
    recurring_merchants,
    large_purchases,
    fallback,
)


class FinanceAgent:
    """FinanceAgent orchestrates:
      - Intent detection (IntentRouter)
      - Dispatch to per-intent handlers
      - Shared RAGRetriever instance for all handlers

    All handlers are RAG-driven: they call retriever.query(question)
    and then shape answer + details + chart + data.
    """

    def __init__(self):
        print("[INIT] Starting FinanceAgent orchestrator (v2, RAG-driven)...")

        self.router = IntentRouter()
        self.retriever = RAGRetriever()

        # Map intent name → handler function
        self.handlers = {
            "restaurant_spend": restaurant_spend.handle,
            "overall_spend": overall_spend.handle,
            "category_spend": category_spend.handle,
            "monthly_summary": monthly_summary.handle,
            "compare_months": compare_months.handle,
            "top_merchants": top_merchants.handle,
            "recurring_merchants": recurring_merchants.handle,
            "large_purchases": large_purchases.handle,
            "fallback": fallback.handle,
        }

    # ------------------------------------------------------------------
    # Main API used by /ask
    # ------------------------------------------------------------------
    def analyze(self, question: str) -> Dict[str, Any]:
        try:
            intent = self.router.detect(question)
        except Exception as e:
            print("[ERROR] Intent detection failed:", e)
            return {
                "intent": "error",
                "answer": f"Sorry, I couldn't detect what you're asking for ({e}).",
                "details": {},
                "chart": None,
                "data": {},
            }

        print(f"[ROUTER] Intent → {intent}")

        handler = self.handlers.get(intent, self.handlers["fallback"])

        try:
            result = handler(question, self.retriever)
        except Exception as e:
            print(f"[ERROR] Handler for intent '{intent}' failed:", e)
            # Fallback to generic RAG summary
            try:
                raw = self.retriever.query(question)
                data = json.loads(raw)
                answer = (
                    "I hit an internal error, but here's a basic summary:\n\n"
                    f"Spend: ${data.get('total_spend', 0):,.2f} "
                    f"from {data.get('matches', 0)} transactions."
                )
                return {
                    "intent": intent,
                    "answer": answer,
                    "details": {
                        "matches": data.get("matches", 0),
                        "top_merchants": data.get("top_merchants", []),
                        "top_categories": data.get("top_categories", []),
                        "top_cuisines": data.get("top_cuisines", []),
                    },
                    "chart": None,
                    "data": data,
                }
            except Exception as e2:
                print("[ERROR] Fallback RAG also failed:", e2)
                return {
                    "intent": intent,
                    "answer": "Something went wrong while answering this question.",
                    "details": {},
                    "chart": None,
                    "data": {},
                }

        # Ensure all keys exist
        result.setdefault("intent", intent)
        result.setdefault("answer", "")
        result.setdefault("details", {})
        result.setdefault("chart", None)
        result.setdefault("data", {})

        return result
