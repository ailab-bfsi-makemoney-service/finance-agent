import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from rag import RAGEngine

# Load environment variables from .env
load_dotenv()

# ------------------------------------------------------------
# LLM Setup
# ------------------------------------------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",   # Use gpt-4o-mini for POC
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)

# ------------------------------------------------------------
# Tool 1: Transactions API
# ------------------------------------------------------------
def fetch_transactions(_: str = ""):
    """Fetch all transactions from the backend API."""
    url = os.getenv(
        "TRANSACTION_API_URL",
        "https://<your-render-subdomain>.onrender.com/transactions"
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.text

transaction_tool = Tool(
    name="fetch_transactions",
    func=fetch_transactions,
    description=(
        "Fetch the user's financial transactions. "
        "Input: none. "
        "Output: JSON array of transactions with fields: "
        "id, transactionDate, postDate, description, category, type, amount."
    ),
)

# ------------------------------------------------------------
# Tool 2: Semantic Search (RAG Layer)
# ------------------------------------------------------------
rag = RAGEngine()

def semantic_search(query: str = ""):
    """Search transactions semantically using embeddings + FAISS index."""
    return rag.query(query)

rag_tool = Tool(
    name="semantic_search",
    func=semantic_search,
    description=(
        "Search past transactions semantically. "
        "Input: a natural language string like 'Italian restaurants in September'. "
        "Output: matching transactions with dates, descriptions, categories, and amounts."
    ),
)

# ------------------------------------------------------------
# Build the Agent
# ------------------------------------------------------------
agent = initialize_agent(
    tools=[transaction_tool, rag_tool],
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

def run_agent(query: str) -> str:
    """Run the finance agent with a user query."""
    return agent.run(query)
