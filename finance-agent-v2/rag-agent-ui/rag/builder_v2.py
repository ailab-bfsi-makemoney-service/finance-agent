import os
import json
import requests
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
TRANSACTION_API_URL = os.getenv("TRANSACTION_MCP_URL", "http://127.0.0.1:8080/transactions")
INDEX_DIR = "rag/index"
os.makedirs(INDEX_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# Embedding Model (small and free for local testing)
# ---------------------------------------------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------------------------------------------------------------
# Helper: Format each transaction into a text block for embedding
# ---------------------------------------------------------------------
def format_transaction(t):
    parts = [
        f"Description: {t.get('description', '')}",
        f"Category: {t.get('category', '')}",
        f"Merchant: {t.get('merchantName', '')}",
        f"Restaurant Type: {t.get('restaurantType', '')}",
        f"Amount: {t.get('amount', '')}",
        f"Date: {t.get('transactionDate', '')}",
    ]
    return " | ".join(parts)

# ---------------------------------------------------------------------
# Main Builder Class
# ---------------------------------------------------------------------
class RAGBuilder:
    def __init__(self):
        self.records = []
        self.embeddings = []

    def fetch_transactions(self):
        print(f"📡 Fetching transactions from {TRANSACTION_API_URL} ...")
        resp = requests.get(TRANSACTION_API_URL)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Retrieved {len(data)} transactions.")
        return data

    def build_index(self):
        data = self.fetch_transactions()

        print("🧠 Generating text representations ...")
        texts = [format_transaction(t) for t in data]

        print("🔢 Encoding embeddings ...")
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

        print("💾 Building FAISS index ...")
        dimension = vectors.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(vectors, dtype=np.float32))

        faiss.write_index(index, f"{INDEX_DIR}/faiss.index")

        # Save metadata (so we can look up transaction info later)
        with open(f"{INDEX_DIR}/metadata.json", "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ FAISS index created with {len(data)} records.")
        print(f"📂 Saved to {INDEX_DIR}/faiss.index and metadata.json")

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    builder = RAGBuilder()
    builder.build_index()
