from fastapi import FastAPI
from pydantic import BaseModel
from agent import run_agent
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask_agent(query: Query):
    response = run_agent(query.question)
    return {"answer": response}



# Serve the chat UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")