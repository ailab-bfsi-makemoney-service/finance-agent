import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------
# Fiscal year configuration
# ---------------------------------------------------------------------
FY25_YEAR = 2025
FY25_MONTH_START = 1
FY25_MONTH_END = 10

# ---------------------------------------------------------------------
# Canonical categories and cuisine tokens
# ---------------------------------------------------------------------
CUISINE_KEYWORDS = [
    "mexican", "italian", "indian", "japanese", "chinese", "thai",
    "sushi", "korean", "mediterranean", "greek", "vietnamese",
    "american", "pizza", "burger", "coffee", "bakery"
]

CATEGORY_MAP = {
    "professional": "Professional Services",
    "shopping": "Shopping",
    "fee": "Fees & Adjustments",
    "education": "Education",
    "personal": "Personal",
    "food": "Food & Drink",
    "restaurant": "Food & Drink",
    "dining": "Food & Drink",
    "automotive": "Automotive",
    "entertainment": "Entertainment",
    "travel": "Travel",
    "donation": "Gifts & Donations",
    "gift": "Gifts & Donations",
    "grocery": "Groceries",
    "supermarket": "Groceries",
    "gas": "Gas",
    "fuel": "Gas",
    "home": "Home",
    "bill": "Bills & Utilities",
    "utility": "Bills & Utilities",
    "electric": "Bills & Utilities",
    "water": "Bills & Utilities",
    "health": "Health & Wellness",
    "pharmacy": "Health & Wellness",
    "wellness": "Health & Wellness",
    "gym": "Health & Wellness",
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12
}


class RAGRetriever:
    """
    Final production retriever_v2.

    Uses the existing FAISS index + metadata.json that already
    include merchant enrichment (restaurantType, merchantName, etc.).
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Support both flat and nested index layouts
        flat_index = os.path.join(base_dir, "faiss.index")
        flat_meta = os.path.join(base_dir, "metadata.json")
        nested_index = os.path.join(base_dir, "index", "faiss.index")
        nested_meta = os.path.join(base_dir, "index", "metadata.json")

        self.index_path = flat_index if os.path.exists(flat_index) else nested_index
        self.meta_path = flat_meta if os.path.exists(flat_meta) else nested_meta

        if not os.path.exists(self.index_path) or not os.path.exists(self.meta_path):
            raise FileNotFoundError(
                f"Missing FAISS index or metadata file.\n"
                f"Index: {self.index_path}\nMeta: {self.meta_path}"
            )

        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.metadata: List[Dict[str, Any]] = json.load(f)

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.read_index(self.index_path)

    # -----------------------------------------------------------------
    # Parsing helpers
    # -----------------------------------------------------------------
    def _parse_month_year(self, text: str):
        q = text.lower()
        month = next((v for k, v in MONTHS.items() if k in q), None)

        year = None
        for tok in re.findall(r"\b\d{4}\b", q):
            try:
                year = int(tok)
                break
            except Exception:
                pass

        return month, year

    def _is_ytd(self, text: str) -> bool:
        q = text.lower()
        return any(x in q for x in ["ytd", "year to date", "to date"])

    def _requested_cuisines(self, text: str) -> List[str]:
        q = text.lower()
        return [c for c in CUISINE_KEYWORDS if c in q]

    def _requested_categories(self, text: str) -> List[str]:
        q = text.lower()
        words = set(re.findall(r"\b\w+\b", q))
        cats = set()

        for k, v in CATEGORY_MAP.items():
            if k in words or f"{k}s" in words:
                cats.add(v)

        return list(cats)

    # -----------------------------------------------------------------
    # Restaurant detection
    # -----------------------------------------------------------------
    def _is_restaurant(self, record: Dict[str, Any]) -> bool:
        desc = (record.get("description") or "").lower()
        cat = (record.get("category") or "").lower()

        # Category-based
        if "food" in cat or "drink" in cat:
            return True

        # Enriched merchantType (from merchant table)
        rt = record.get("restaurantType")
        if isinstance(rt, list) and rt:
            return True
        if isinstance(rt, str) and rt.strip():
            return True

        # Fallback keyword sniffing on description
        restaurant_terms = [
            "restaurant", "cafe", "bar", "grill", "taco", "pizza",
            "pizzeria", "kitchen", "eatery", "burger", "bbq",
            "brunch", "bistro", "brew", "donut", "doughnut"
        ]
        return any(t in desc for t in restaurant_terms)

    # -----------------------------------------------------------------
    # Cuisine check
    # -----------------------------------------------------------------
    def _matches_cuisine(self, record: Dict[str, Any], cuisines: List[str]) -> bool:
        if not cuisines:
            return True

        desc = (record.get("description") or "").lower()
        rt = record.get("restaurantType")

        if any(c in desc for c in cuisines):
            return True

        if isinstance(rt, str):
            rts = [rt.lower()]
        elif isinstance(rt, list):
            rts = [str(x).lower() for x in rt]
        else:
            rts = []

        for c in cuisines:
            if any(c in t for t in rts):
                return True

        return False

    # -----------------------------------------------------------------
    # Core filtering iterator
    # -----------------------------------------------------------------
    def _iter_filtered_records(
        self,
        question: str,
        top_k: int = 300,
        restaurant_only: bool = False,
    ):
        """
        Core iterator that applies:
          - FY25 window (Jan–Oct 2025)
          - optional month/year filter from question
          - optional YTD logic
          - restaurant-only filter for restaurant queries
          - category/cuisine filters for non-restaurant queries

        IMPORTANT:
          • For restaurant_only=True we DO NOT use FAISS to prefilter.
            We scan all metadata so counts match your SQL exactly.
        """

        q_lower = question.lower()
        month, year = self._parse_month_year(q_lower)
        ytd = self._is_ytd(q_lower)
        cuisines = self._requested_cuisines(q_lower)
        cats = self._requested_categories(q_lower)

        # If only month mentioned, assume FY25
        if month and not year:
            year = FY25_YEAR

        # -------------------------------------------------------------
        # Candidate set
        # -------------------------------------------------------------
        if restaurant_only:
            # Hard accuracy requirement → scan everything
            candidate_indices = range(len(self.metadata))
        else:
            # Use FAISS for general spend/category queries
            q_emb = self.model.encode([question])
            q_emb = np.array(q_emb).astype("float32")
            top_k = min(top_k, len(self.metadata))
            _, I = self.index.search(q_emb, top_k)
            candidate_indices = I[0]

        # -------------------------------------------------------------
        # Apply filters
        # -------------------------------------------------------------
        for i in candidate_indices:
            if not (0 <= i < len(self.metadata)):
                continue

            r = self.metadata[i]

            date_raw = r.get("transactionDate")
            if not date_raw:
                continue

            try:
                d = datetime.strptime(date_raw.split("T")[0], "%Y-%m-%d")
            except Exception:
                continue

            # FY25 window
            if not (
                d.year == FY25_YEAR
                and FY25_MONTH_START <= d.month <= FY25_MONTH_END
            ):
                continue

            # Month-specific vs YTD
            if month and not ytd and d.month != month:
                continue

            if year and d.year != year:
                continue

            # Restaurant-only filter
            if restaurant_only and not self._is_restaurant(r):
                continue

            # Category filter for non-restaurant queries
            if not restaurant_only and cats:
                rec_cat = (r.get("category") or "").lower()
                if not any(c.lower() in rec_cat for c in cats):
                    continue

            # Cuisine filter
            if cuisines and not self._matches_cuisine(r, cuisines):
                continue

            yield r

    # -----------------------------------------------------------------
    # Restaurant spend (public)
    # -----------------------------------------------------------------
    def get_restaurant_spend(self, question: str) -> Dict[str, Any]:
        total = 0.0
        count = 0
        by_restaurant = defaultdict(float)
        by_category = defaultdict(float)
        by_cuisine = defaultdict(float)

        # Iterate through all records with restaurant_only=True
        for r in self._iter_filtered_records(question, restaurant_only=True):
            amt_raw = r.get("amount", 0)
            try:
                amt = float(amt_raw)
            except Exception:
                continue

            # Negative amounts represent spending
            if amt >= 0:
                continue
            amt = -amt

            total += amt
            count += 1

            name = r.get("merchantName") or r.get("description") or "Unknown"
            by_restaurant[name] += amt

            category = r.get("category") or "Uncategorized"
            by_category[category] += amt

            rt = r.get("restaurantType")
            if isinstance(rt, list):
                for t in rt:
                    by_cuisine[str(t)] += amt
            elif isinstance(rt, str) and rt.strip():
                by_cuisine[rt] += amt

        # Convert tuples → dicts
        top_restaurants = [
            {"merchant": name, "total_spend": round(amt, 2)}
            for name, amt in sorted(
                by_restaurant.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        top_categories = [
            {"category": name, "total_spend": round(amt, 2)}
            for name, amt in sorted(
                by_category.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        top_cuisines = [
            {"cuisine": name, "total_spend": round(amt, 2)}
            for name, amt in sorted(
                by_cuisine.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        # Final normalized return object
        return {
            "query": question,

            # legacy fields
            "matches": count,
            "total": round(total, 2),

            # new normalized fields for UI
            "total_restaurant_spend": round(total, 2),
            "total_visits": count,

            "top_restaurants": top_restaurants,
            "top_categories": top_categories,
            "top_cuisines": top_cuisines,
        }

    # -----------------------------------------------------------------
    # Generic query (debug / non-restaurant)
    # -----------------------------------------------------------------
    def query(self, question: str, top_k: int = 300) -> Dict[str, Any]:
        total = 0.0
        count = 0
        by_merchant = defaultdict(float)
        by_category = defaultdict(float)
        by_cuisine = defaultdict(float)

        for r in self._iter_filtered_records(
            question, top_k=top_k, restaurant_only=False
        ):
            amt_raw = r.get("amount", 0)
            try:
                amt = float(amt_raw)
            except Exception:
                continue

            if amt >= 0:
                continue
            amt = -amt

            total += amt
            count += 1

            merchant = r.get("merchantName") or r.get("description") or "Unknown"
            by_merchant[merchant] += amt

            category = r.get("category") or "Uncategorized"
            by_category[category] += amt

            rt = r.get("restaurantType")
            if isinstance(rt, list):
                for t in rt:
                    by_cuisine[str(t)] += amt
            elif isinstance(rt, str) and rt.strip():
                by_cuisine[rt] += amt

        return {
            "query": question,
            "matches": count,
            "total_spend": round(total, 2),
            "top_merchants": sorted(
                by_merchant.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_categories": sorted(
                by_category.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_cuisines": sorted(
                by_cuisine.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }


# =====================================================================
#  BACKWARDS COMPATIBILITY ALIAS
# =====================================================================

# So anything importing RetrieverV2 still works.
RetrieverV2 = RAGRetriever
