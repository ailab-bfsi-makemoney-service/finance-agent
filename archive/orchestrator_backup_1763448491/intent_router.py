# orchestrator/intent_router.py

import os
import importlib
from typing import Dict, List


class IntentRouter:
    """Python-based intent router.

    Loads all files in intents/ folder that define:
        INTENT_NAME = "restaurant_spend"
        KEYWORDS = ["restaurant", "dining", ...]

    And uses simple keyword matching to detect the most likely intent.
    """

    def __init__(self):
        print("[INIT] Loading python-based intents (v2)...")

        self.intent_keywords: Dict[str, List[str]] = {}

        intents_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "intents",
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

            if intent_name and isinstance(keywords, list):
                self.intent_keywords[intent_name] = [k.lower() for k in keywords]
                print(f"  ✓ Loaded intent keywords: {intent_name}")

        if "fallback" not in self.intent_keywords:
            print("⚠ WARNING: No fallback intent defined")

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------
    def detect(self, question: str) -> str:
        q = question.lower()

        # simple scoring: count keyword hits
        best_intent = "fallback"
        best_score = 0

        for intent, kws in self.intent_keywords.items():
            score = sum(1 for kw in kws if kw in q)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent
