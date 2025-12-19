import os
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from orchestrator.orchestrator import FinanceAgent

app = FastAPI(title="Finance-Agent Unified", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[INIT] Bootstrapping FinanceAgent...")
agent = FinanceAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

class AskIn(BaseModel):
    question: Optional[str] = None
    input: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None

@app.post("/ask")
def ask(payload: AskIn):
    try:
        q = payload.question or payload.input or payload.message or payload.text
        if not q:
            return JSONResponse(
                status_code=400,
                content={"intent":"error","answer":"Missing question. Send {question: \"...\"}.","chart":None,"data":{}},
            )

        result = agent.analyze(q)

        if isinstance(result, dict):
            return JSONResponse(status_code=200, content=result)
        return JSONResponse(status_code=200, content={"intent":"answer","answer":str(result),"chart":None,"data":{}})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"intent":"error","answer":"Internal error while processing question.","details":{"error":str(e)},"chart":None,"data":{}},
        )

@app.get("/health")
def health():
    return {"status":"ok", "ui":"online", "agent":"ready"}
