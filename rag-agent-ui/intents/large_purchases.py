import json
INTENT_NAME="large_purchases"
KEYWORDS=["large","big","expensive","high value"]
def handle(question, intent_name, metadata, retriever):
    raw=retriever.query(question)
    data= raw if isinstance(raw,dict) else json.loads(raw)
    answer="Large purchases identified."
    return {"intent":INTENT_NAME,"answer":answer,"details":{},"chart":None,"data":data}
