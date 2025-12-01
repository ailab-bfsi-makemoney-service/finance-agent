from fastapi import FastAPI, Request
import requests
import os

app = FastAPI(title="Transaction MCP", version="1.0.0")

TRANSACTION_API = os.getenv("TRANSACTION_API_BASE_URL", "https://get-transaction-wmco.onrender.com")

@app.post("/mcp/transactions")
async def handle_transaction_intent(req: Request):
    body = await req.json()
    intent = body.get("intent")
    payload = body.get("payload", {})

    print(f"📨 Received intent: {intent}")
    print(f"🔹 Payload: {payload}")

    if intent == "get_transactions":
        category = payload.get("filters", {}).get("category", "")
        resp = requests.get(f"{TRANSACTION_API}/transactions")
        txns = resp.json()

        if category:
            txns = [t for t in txns if t.get("category") == category]

        return {"status": "success", "count": len(txns), "transactions": txns}

    return {"status": "error", "message": f"Unsupported intent: {intent}"}
