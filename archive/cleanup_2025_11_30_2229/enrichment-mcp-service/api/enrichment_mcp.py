from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Finance Agent Enrichment MCP", version="1.0")

class MerchantRequest(BaseModel):
    name: str
    city: str | None = None

@app.post("/mcp/enrich-merchant")
def enrich_merchant(req: MerchantRequest):
    # Placeholder: replace with your Yelp/Places enrichment logic.
    return {
        "name": req.name,
        "city": req.city,
        "category": "Restaurant",
        "confidence": 0.8
    }