import sys
import os
import json
import requests
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
import warnings

# --------------------------------------------------------------------
# ✅ Fix Import Path (so we can import sibling package /rag)
# --------------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.retriever import RAGRetriever

# --------------------------------------------------------------------
# ⚙️ Optional: suppress LangChain deprecation warnings
# --------------------------------------------------------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --------------------------------------------------------------------
# ✅ Environment Setup
# --------------------------------------------------------------------
load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT_ID")

# --------------------------------------------------------------------
# ✅ Model Setup (OpenAI)
# --------------------------------------------------------------------
if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    print("✅ Using classic OpenAI (sk-) key")
else:
    print("⚠️  No valid OpenAI key found, reasoning disabled")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=OPENAI_KEY,
)

# --------------------------------------------------------------------
# ✅ Load Metadata (used for deterministic analytics)
# --------------------------------------------------------------------
metadata_path = os.path.join(os.path.dirname(__file__), "..", "rag", "index", "metadata.json")
with open(metadata_path, "r") as f:
    metadata = json.load(f)

rag = RAGRetriever()

# --------------------------------------------------------------------
# 🧩 Helper - Parse month/year from query
# --------------------------------------------------------------------
def parse_month_year(query: str):
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    query_l = query.lower()
    month = next((v for k, v in months.items() if k in query_l), None)

    year = None
    for token in query_l.split():
        if token.isdigit() and len(token) == 4:
            year = int(token)
            break
    return month, year

# --------------------------------------------------------------------
# 🍽️ Restaurant Analytics
# --------------------------------------------------------------------
def restaurant_analytics(query: str) -> str:
    query_l = query.lower()
    month, year = parse_month_year(query)

    total_spend = 0.0
    count = 0
    by_restaurant = defaultdict(float)

    for r in metadata:
        cat = (r.get("category") or "").lower()
        desc = (r.get("description") or "").lower()
        types = json.dumps(r.get("restaurantType", [])) if r.get("restaurantType") else ""
        date = r.get("transactionDate") or r.get("transaction_date")

        if not date:
            continue
        try:
            d = datetime.strptime(date.split("T")[0], "%Y-%m-%d")
        except ValueError:
            continue

        # Filter by date
        if year and d.year != year:
            continue
        if month and d.month != month:
            continue

        # Must be food/restaurant
        if "restaurant" not in cat and "food" not in cat and "drink" not in cat:
            continue

        # Apply cuisine-specific filter
        if any(k in query_l for k in ["italian", "mexican", "indian", "thai", "chinese"]):
            cuisine = next((k for k in ["italian", "mexican", "indian", "thai", "chinese"] if k in query_l), None)
            if cuisine and cuisine not in types.lower() and cuisine not in desc:
                continue

        amt = float(r.get("amount", 0) or 0)
        if amt < 0:
            total_spend += -amt
            count += 1
            rest = r.get("merchantName") or r.get("description")
            by_restaurant[rest] += -amt

    result = {
        "category": "restaurants",
        "month": month,
        "year": year,
        "transactions": count,
        "total_spend": round(total_spend, 2),
        "top_restaurants": sorted(by_restaurant.items(), key=lambda x: x[1], reverse=True)[:5]
    }
    return json.dumps(result, indent=2)

# --------------------------------------------------------------------
# 🛍️ Deterministic Analytics for Other Categories
# --------------------------------------------------------------------
def category_analytics(query: str) -> str:
    query_l = query.lower()
    month, year = parse_month_year(query)

    # detect category keyword
    keywords = ["travel", "grocer", "shopping", "uber", "lyft", "gas", "entertainment", "utilities"]
    detected = None
    for kw in keywords:
        if kw in query_l:
            detected = kw
            break

    total_spend = 0.0
    count = 0
    merchants = defaultdict(float)

    for r in metadata:
        cat = (r.get("category") or "").lower()
        desc = (r.get("description") or "").lower()
        date = r.get("transactionDate") or r.get("transaction_date")

        if not date:
            continue
        try:
            d = datetime.strptime(date.split("T")[0], "%Y-%m-%d")
        except ValueError:
            continue

        # Filter by year/month if provided
        if year and d.year != year:
            continue
        if month and d.month != month:
            continue

        # Filter by detected category keyword
        if detected:
            if detected not in cat and detected not in desc:
                continue

        amt = float(r.get("amount", 0) or 0)
        if amt < 0:
            total_spend += -amt
            count += 1
            merchant = r.get("merchantName") or r.get("description")
            merchants[merchant] += -amt

    result = {
        "category": detected or "general",
        "month": month,
        "year": year,
        "transactions": count,
        "total_spend": round(total_spend, 2),
        "top_merchants": sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:5]
    }

    return json.dumps(result, indent=2)

# --------------------------------------------------------------------
# 🤖 RAG Search Tool
# --------------------------------------------------------------------
def semantic_search(query: str):
    return rag.query(query)

rag_tool = Tool(
    name="semantic_search",
    func=semantic_search,
    description="Search transactions semantically based on natural queries."
)

# --------------------------------------------------------------------
# 🧠 Agent Construction
# --------------------------------------------------------------------
agent = initialize_agent(
    tools=[rag_tool],
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True,
    handle_parsing_errors=True
)

# --------------------------------------------------------------------
# 🔍 Run Agent Logic
# --------------------------------------------------------------------
def run_agent(query: str) -> str:
    query_l = query.lower()
    try:
        if any(k in query_l for k in ["restaurant", "eat", "dine", "food", "drink"]):
            print("🍽️ Routing to restaurant_analytics()")
            return restaurant_analytics(query)
        elif any(k in query_l for k in ["travel", "uber", "lyft", "grocery", "shopping", "entertainment", "gas", "utilities"]):
            print("🛍️ Routing to category_analytics()")
            return category_analytics(query)
        else:
            print("🧠 Routing to RAG semantic search for reasoning")
            return rag.query(query)
    except Exception as e:
        print(f"⚠️ Agent error: {e}")
        return json.dumps({"error": str(e)}, indent=2)

# --------------------------------------------------------------------
# 🧪 Local CLI Testing
# --------------------------------------------------------------------
if __name__ == "__main__":
    print("\n💬 Finance Agent (CLI Mode)")
    print("Type your question (or 'exit' to quit):\n")
    while True:
        q = input("You: ")
        if q.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        response = run_agent(q)
        print(f"\n🤖 Agent:\n{response}\n")

# --- Backwards-compatible export for Render / app.py imports ---
# app.py expects: from agent.orchestrator import FinanceAgent
# If the implementation was renamed/refactored, provide a stable alias.
import inspect as _inspect
import sys as _sys

_mod = _sys.modules[__name__]

if not hasattr(_mod, "FinanceAgent"):
    # Prefer common class names if they exist
    for _name in ("FinanceAgent", "Orchestrator", "FinanceOrchestrator", "AgentOrchestrator"):
        _obj = getattr(_mod, _name, None)
        if _inspect.isclass(_obj):
            setattr(_mod, "FinanceAgent", _obj)
            break

if not hasattr(_mod, "FinanceAgent"):
    # Otherwise, pick a single obvious candidate class (last resort)
    _candidates = [
        (_n, _o) for _n, _o in vars(_mod).items()
        if _inspect.isclass(_o) and _o.__module__ == __name__
    ]
    # If there's exactly one local class, alias it
    if len(_candidates) == 1:
        setattr(_mod, "FinanceAgent", _candidates[0][1])
    else:
        # Try "agent" in the class name
        _agentish = [(_n, _o) for _n, _o in _candidates if "agent" in _n.lower()]
        if len(_agentish) == 1:
            setattr(_mod, "FinanceAgent", _agentish[0][1])

# --- Render/app.py compatibility ---
# app.py imports: from agent.orchestrator import FinanceAgent
# This repo currently uses top-level functions (no classes). Provide a stable wrapper.

class FinanceAgent:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, query: str, **kwargs):
        fn = globals().get('parse_month_year')
        if callable(fn):
            try:
                return fn(query, **kwargs)
            except TypeError:
                # function may not accept kwargs
                return fn(query)
        raise RuntimeError("No suitable orchestrator function found in agent/orchestrator.py")

    def __call__(self, query: str, **kwargs):
        return self.run(query, **kwargs)

