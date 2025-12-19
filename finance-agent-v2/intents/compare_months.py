import json
INTENT_NAME="compare_months"
KEYWORDS=["compare","vs","difference"]
def handle(question, intent_name, metadata, retriever):
    raw=retriever.query(question)
    data= raw if isinstance(raw,dict) else json.loads(raw)
    answer="Comparison complete."
    return {"intent":INTENT_NAME,"answer":answer,"details":{},"chart":None,"data":data}
