Finance Agent - Phase 1 Modular Setup
=====================================

This bundle contains two services:

1. rag-agent-ui
   - FastAPI-based Finance Agent
   - JSON-config intent router (15 intents ready to extend)
   - RAGRetriever stub (wire to your FAISS + metadata)
   - Basic Auth (FINAGENT_USER / FINAGENT_PASS)
   - Simple HTML UI with charts.

2. enrichment-mcp-service
   - FastAPI MCP-style stub for merchant enrichment.
   - Replace placeholder logic with your existing Yelp / merchant classifiers.

Quick Start (rag-agent-ui)
--------------------------

cd rag-agent-ui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FINAGENT_USER=betauser
export FINAGENT_PASS=betapass
uvicorn app:app --reload

Then open http://127.0.0.1:8000 and authenticate.

Render Deployment (rag-agent-ui)
--------------------------------
Build command:
  pip install -r requirements.txt

Start command:
  uvicorn app:app --host 0.0.0.0 --port 10000

Set environment variables:
  FINAGENT_USER
  FINAGENT_PASS

Next Steps
----------
- Copy your existing FAISS index + metadata.json into rag-agent-ui/rag/index.
- Replace RAGRetriever.query() with your production retrieval logic.
- Wire transactional computations to your deployed Transaction API if desired.
- Extend intents/ with additional handlers while keeping orchestrator thin.