# orchestrator/orchestrator.py

import json
import inspect
from typing import Dict, Any

from rag.retriever_v2 import RAGRetriever  # MUST exist as class name
from orchestrator.intent_router import IntentRouter


class FinanceAgent:
    """
    FinanceAgent orchestrates:
      • Intent detection (IntentRouter)
      • Dispatch to per-intent handlers (intents/*.py)
      • Shared FAISS retriever for category/restaurant analysis

    Handlers may use ANY of these signatures:
      1) handle(question)
      2) handle(question, retriever)
      3) handle(question, intent_name, metadata, retriever)   ← newest standard
    """

    def __init__(self):
        print("[INIT] Starting FinanceAgent orchestrator (python-intents + RAG)...")

        # Shared FAISS retriever
        self.retriever = RAGRetriever()

        # Load handlers (names, keywords)
        self.router = IntentRouter()

    # ----------------------------------------------------------------------
    # Build details from data payload for UI
    # ----------------------------------------------------------------------
      # ----------------------------------------------------------------------
    # Build details from data payload for UI (restaurant-safe version)
    # ----------------------------------------------------------------------
    def _build_details_from_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes data payloads into a UI-safe details block.
        Ensures consistent fields required by the React UI.
        """

        if not isinstance(data, dict):
            return {}

        details = {}

        # Totals used by restaurant analysis
        if "total_restaurant_spend" in data:
            details["total_restaurant_spend"] = data["total_restaurant_spend"]

        if "total_visits" in data:
            details["total_visits"] = data["total_visits"]

        # Standard lists used by charts & details UI
        if "top_restaurants" in data:
            details["top_restaurants"] = data["top_restaurants"]

        if "top_cuisines" in data:
            details["top_cuisines"] = data["top_cuisines"]

        if "top_categories" in data:
            details["top_categories"] = data["top_categories"]

        return details

    # ----------------------------------------------------------------------
    # Normalize return payload from handlers
    # ----------------------------------------------------------------------
    def _normalize_result(self, intent_name: str, raw: Any) -> Dict[str, Any]:
        # Handler returned dict
        if isinstance(raw, dict):
            intent = raw.get("intent", intent_name)
            answer = raw.get("answer", "")

            # Choose data field if present, else treat whole dict as data
            data = raw.get("data", raw)
            details = raw.get("details", self._build_details_from_data(data))
            chart = raw.get("chart")

            return {
                "intent": intent,
                "answer": answer,
                "details": details or {},
                "chart": chart,
                "data": data or {},
            }

        # Handler returned JSON string
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return self._normalize_result(intent_name, parsed)
            except Exception:
                return {
                    "intent": intent_name,
                    "answer": raw,
                    "details": {},
                    "chart": None,
                    "data": {},
                }

        # Unknown type
        return {
            "intent": intent_name,
            "answer": str(raw),
            "details": {},
            "chart": None,
            "data": {},
        }

    # ----------------------------------------------------------------------
    # Generic fallback if handler fails or missing
    # ----------------------------------------------------------------------
    def _generic_rag_fallback(self, intent_name: str, question: str) -> Dict[str, Any]:
        try:
            raw = self.retriever.query(question)

            # Accept dict or JSON string
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw": raw}
            else:
                data = raw

            total = data.get("total_spend") or data.get("total") or 0
            matches = data.get("matches", 0)

            answer = (
                f"I hit an internal error while handling '{intent_name}', "
                f"but here's a basic summary: you spent approximately "
                f"${total:,.2f} across {matches} transactions."
            )

            details = self._build_details_from_data(data)

            return {
                "intent": intent_name,
                "answer": answer,
                "details": details,
                "chart": None,
                "data": data,
            }

        except Exception as e2:
            print("[ERROR] RAG fallback also failed:", e2)
            return {
                "intent": intent_name,
                "answer": "Something went wrong while answering this request.",
                "details": {},
                "chart": None,
                "data": {},
            }

    # ----------------------------------------------------------------------
    # Safe universal handler invocation (supports 1, 2, or 4 args)
    # ----------------------------------------------------------------------
    def _invoke_handler(self, handler, question, intent_name):
        sig = inspect.signature(handler)
        param_count = len(sig.parameters)

        # metadata passed to new handlers
        metadata = getattr(self.retriever, "metadata", [])

        if param_count == 4:
            # New standard signature
            return handler(question, intent_name, metadata, self.retriever)

        elif param_count == 2:
            # Old signature: handle(question, retriever)
            return handler(question, self.retriever)

        elif param_count == 1:
            # Very old signature: handle(question)
            return handler(question)

        else:
            raise TypeError(
                f"Unsupported handler signature ({param_count} parameters): {handler}"
            )

    # ----------------------------------------------------------------------
    # Main API entry (called by FastAPI endpoint)
    # ----------------------------------------------------------------------
    def analyze(self, question: str) -> Dict[str, Any]:
        try:
            intent_name = self.router.detect(question)
        except Exception as e:
            print("[ERROR] Intent detection failed:", e)
            return {
                "intent": "error",
                "answer": f"Could not detect intent ({e}).",
                "details": {},
                "chart": None,
                "data": {},
            }

        print(f"[ROUTER] Intent → {intent_name}")

        # Resolve handler for intent
        handler = self.router.handlers.get(intent_name)

        if handler is None:
            print(f"[WARN] No handler found for '{intent_name}'. Using RAG fallback.")
            return self._generic_rag_fallback(intent_name, question)

        # Invoke handler safely
        try:
            raw_result = self._invoke_handler(handler, question, intent_name)
            return self._normalize_result(intent_name, raw_result)

        except Exception as e:
            print(f"[ERROR] Handler '{intent_name}' failed:", e)
            return self._generic_rag_fallback(intent_name, question)
