# app.py — Full Working Version With UI Hosting
# ----------------------------------------------
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from orchestrator.orchestrator import FinanceAgent

# ---------------------------------------------------------
# FastAPI Setup (NO AUTH, NO LOGIN POPUPS)
# ---------------------------------------------------------
app = FastAPI()

# CORS: allows browser JS to call backend without triggering auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Agent initialization
# ---------------------------------------------------------
print("[INIT] Bootstrapping FinanceAgent...")
agent = FinanceAgent()

# ---------------------------------------------------------
# UI: Serve static folder + index.html
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

print(f"[INIT] Static directory resolved to: {STATIC_DIR}")

# Serve /static/* → static/
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve UI at root
@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    print(f"[SERVE] Serving UI → {index_path}")
    return FileResponse(index_path)

# ---------------------------------------------------------
# Request model
# ---------------------------------------------------------
class QueryIn(BaseModel):
    question: str

# ---------------------------------------------------------
# Main endpoint (NO 401 EVER)
# ---------------------------------------------------------
@app.post("/ask")
def ask(query: QueryIn):
    try:
        print(f"[ASK] Question received → {query.question}")

        result = agent.analyze(query.question)

        # Always return 200 OK — avoids browser auth popup
        return JSONResponse(
            status_code=200,
            content=result
        )

    except Exception as e:
        print("[ERROR] /ask failed:", e)

        # Still NO 401 — return 500 JSON only
        return JSONResponse(
            status_code=500,
            content={
                "intent": "error",
                "answer": "Internal error while processing question.",
                "details": {"error": str(e)},
                "chart": None,
                "data": {},
            }
        )


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "ui": "online", "agent": "ready"}
