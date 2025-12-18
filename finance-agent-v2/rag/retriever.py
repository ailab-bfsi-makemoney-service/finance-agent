import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from collections import defaultdict


class RAGRetriever:
    """
    Loads FAISS index + metadata and provides semantic query capability
    with aggregation logic (spend totals, categories, merchants, etc.).
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.index_path = os.path.join(base_dir, "faiss.index")
        self.meta_path = os.path.join(base_dir, "metadata.json")
        # Render/Git layout: metadata lives under rag/index/
        from pathlib import Path
        _mp = Path(self.meta_path)
        if not _mp.exists():
            _alt = _mp.parent / 'index' / _mp.name
            if _alt.exists():
                self.meta_path = str(_alt)

        # --- Load metadata ---
        if not os.path.exists(self.meta_path):
            raise FileNotFoundError(f"Missing metadata file: {self.meta_path}")
        with open(self.meta_path, "r") as f:
            self.metadata = json.load(f)

        # --- Load FAISS index and embedding model ---
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"Missing FAISS index file: {self.index_path}")
        self.index = faiss.read_index(self.index_path)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # --- Canonical categories ---
        self.category_map = {
            "professional": "Professional Services",
            "shopping": "Shopping",
            "fee": "Fees & Adjustments",
            "education": "Education",
            "personal": "Personal",
            "food": "Food & Drink",
            "drink": "Food & Drink",
            "restaurant": "Food & Drink",
            "automotive": "Automotive",
            "car": "Automotive",
            "entertainment": "Entertainment",
            "movie": "Entertainment",
            "travel": "Travel",
            "flight": "Travel",
            "hotel": "Travel",
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
            "wellness": "Health & Wellness"
        }

    # ------------------------------------------------------------------

    def detect_category(self, query: str):
        q = query.lower()
        for k, v in self.category_map.items():
            if k in q:
                return v
        return None

    # ------------------------------------------------------------------

    def query(self, question: str, top_k: int = 10):
        """
        Perform semantic similarity search across FAISS index and aggregate results.
        """
        detected_category = self.detect_category(question)

        # Encode query and search FAISS
        q_emb = self.model.encode([question])
        q_emb = np.array(q_emb).astype("float32")
        D, I = self.index.search(q_emb, top_k)

        results = [self.metadata[i] for i in I[0] if i < len(self.metadata)]
        if not results:
            return json.dumps({"summary": "No matching transactions found."}, indent=2)

        # Filter results by detected category if applicable
        if detected_category:
            results = [
                r for r in results
                if detected_category.lower() in (r.get("category") or "").lower()
            ]

        # --- Aggregate spending ---
        total_spend = 0.0
        count = 0
        by_merchant = defaultdict(float)
        categories = defaultdict(float)

        for r in results:
            amt = float(r.get("amount", 0) or 0)
            if amt < 0:  # spending only
                total_spend += -amt
                count += 1
                merchant = r.get("merchantName") or r.get("description")
                cat = r.get("category") or "Uncategorized"
                by_merchant[merchant] += -amt
                categories[cat] += -amt

        summary = {
            "query": question,
            "detected_category": detected_category or "None",
            "matches": count,
            "total_spend": round(total_spend, 2),
            "top_merchants": sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_categories": sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3],
        }

        return json.dumps(summary, indent=2)

