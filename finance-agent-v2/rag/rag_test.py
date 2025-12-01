import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer

print("🧠 Loading model and FAISS index ...")
model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("rag/index/faiss.index")

with open("rag/index/metadata.json") as f:
    data = json.load(f)
print(f"✅ Loaded {len(data)} records.")

while True:
    query = input("\n🔍 Enter your query (or type 'exit' to quit): ").strip()
    if query.lower() == "exit":
        print("👋 Goodbye!")
        break

    query_vec = model.encode([query])
    D, I = index.search(np.array(query_vec, dtype=np.float32), k=10)

    total_spend = 0
    count = 0
    print("\n📊 Top results:")
    for rank, idx in enumerate(I[0]):
        record = data[idx]
        amount = float(record.get("amount", 0))
        total_spend += abs(amount)
        count += 1
        print(f"\nResult {rank + 1}:")
        print(f"  Description: {record.get('description', '')}")
        print(f"  Merchant: {record.get('merchantName', '')}")
        print(f"  Restaurant Type: {record.get('restaurantType', '')}")
        print(f"  Amount: {amount}")
        print(f"  Date: {record.get('transactionDate', '')}")
        print("-" * 50)

    if count > 0:
        avg = total_spend / count
        print(f"\n💰 Total spend (top {count} matches): ${total_spend:.2f}")
        print(f"💵 Average transaction: ${avg:.2f}")
    else:
        print("⚠️ No matching records found.")

