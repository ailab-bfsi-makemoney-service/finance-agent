import os
import requests
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

class RAGEngine:
    def __init__(self):
        # Use local Hugging Face embeddings instead of OpenAI
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self._build_index()

    def _build_index(self):
        url = os.getenv("TRANSACTION_API_URL", "https://<your-render-subdomain>.onrender.com/transactions")
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        docs = []
        for tx in data:
            text = (
                f"Date: {tx['transactionDate']}, "
                f"Desc: {tx['description']}, "
                f"Category: {tx['category']}, "
                f"Amount: {tx['amount']}"
            )
            docs.append(Document(page_content=text))

        self.vectorstore = FAISS.from_documents(docs, self.embeddings)

    def query(self, q: str) -> str:
        if not self.vectorstore:
            return "No index available"
        docs = self.vectorstore.similarity_search(q, k=5)
        return "\n".join([d.page_content for d in docs])
