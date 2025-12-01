from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from agent.orchestrator import FinanceAgent

app = FastAPI(title="Finance-Agent v2", version="2.0")

# Initialize the agent
agent = FinanceAgent()

# Request body model
class Query(BaseModel):
    question: str

# Endpoint to query the agent
@app.post("/ask")
async def ask_agent(query: Query):
    result = agent.analyze(query.question)
    return result  # returns structured JSON: summary, chart, recommendation

# Serve the static UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
