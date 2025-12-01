import os, json, numpy as np, faiss
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L12-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "index", "finance_agent.index")
META_PATH  = os.path.join(os.path.dirname(__file__), "index", "finance_agent_meta.json")

class RAGBuilder:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

    def _format_record(self, txn):
        """
        Combines transaction + merchant info into a single string.
        Expected keys: merchant_name, category, city, amount, date
        """
        return (
            f"Spent ${txn.get('amount')} at {txn.get('merchant_name')} "
            f"({txn.get('category')}) in {txn.get('city')} on {txn.get('date')}."
        )

    def build_index(self, data_file):
        """Create FAISS index from JSON records"""
        with open(data_file, "r") as f:
            records = json.load(f)

        texts = [self._format_record(r) for r in records]
        embeddings = self.model.encode(texts, normalize_embeddings=True)

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(np.array(embeddings, dtype="float32"))

        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        faiss.write_index(index, INDEX_PATH)

        with open(META_PATH, "w") as f:
            json.dump(records, f)

        print(f"✅ FAISS index built: {len(records)} records")

if __name__ == "__main__":
    builder = RAGBuilder()
    builder.build_index("transactions_debug.json")
