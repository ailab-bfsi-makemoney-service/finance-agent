from fastapi import FastAPI, Request
import subprocess
import os

app = FastAPI(title="Enrichment MCP", version="1.0.0")

@app.post("/mcp/enrichment")
async def handle_enrichment_intent(req: Request):
    body = await req.json()
    intent = body.get("intent")
    payload = body.get("payload", {})

    print(f"📨 Received intent: {intent}")
    print(f"🔹 Payload: {payload}")

    if intent == "run_enrichment":
        print("🚀 Launching merchant enrichment job...")
        result = subprocess.run(
            ["python3", "merchant_yelp_enrichment.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Enrichment completed successfully.")
            return {"status": "success", "log": result.stdout}
        else:
            print("❌ Enrichment failed.")
            return {"status": "error", "log": result.stderr}

    return {"status": "error", "message": f"Unsupported intent: {intent}"}
