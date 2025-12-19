# orchestrator/intent_router.py

import os
import importlib
from typing import Dict, List, Callable, Any


class IntentRouter:
    """
    Loads all intent modules from intents/*.py

    Each intent module must define:
        INTENT_NAME = "restaurant_spend"
        KEYWORDS = ["restaurant", "dining"]
        def handle(question, ...) -> dict

    Router exposes two dicts:
        self.handlers[intent_name]  → handler function
        self.intent_keywords[intent_name] → list[str]
    """

    def __init__(self):
        print("[INIT] Loading python-based intents (v3)...")

        self.handlers: Dict[str, Callable] = {}
        self.intent_keywords: Dict[str, List[str]] = {}

        intents_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "intents"
        )
        intents_dir = os.path.abspath(intents_dir)

        for fname in os.listdir(intents_dir):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue

            module_name = fname[:-3]
            module_path = f"intents.{module_name}"

            module = importlib.import_module(module_path)

            intent_name = getattr(module, "INTENT_NAME", None)
            keywords = getattr(module, "KEYWORDS", [])
            handler = getattr(module, "handle", None)

            # Only load valid modules
            if not intent_name:
                print(f"⚠ Skipping {module_name}: missing INTENT_NAME")
                continue

            if not callable(handler):
                print(f"⚠ Skipping {module_name}: missing handle()")
                continue

            # Register handler + keywords
            self.handlers[intent_name] = handler
            self.intent_keywords[intent_name] = [k.lower() for k in keywords]

            print(f"  ✓ Loaded intent: {intent_name}")

        if "fallback" not in self.handlers:
            print("⚠ WARNING: No fallback handler loaded!")

    # ------------------------------------------------------------
    # Intent detection using keyword scoring
    # ------------------------------------------------------------
    def detect(self, question: str) -> str:
        q = question.lower()
        best_intent = "fallback"
        best_score = 0

        for intent, kw_list in self.intent_keywords.items():
            score = sum(1 for kw in kw_list if kw in q)
            if score > best_score:
                best_intent = intent
                best_score = score

        return best_intent

    # Optional convenience
    def get_handler(self, intent_name: str):
        return self.handlers.get(intent_name, self.handlers.get("fallback"))
