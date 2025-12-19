import json
INTENT_NAME="recurring_merchants"
KEYWORDS=["recurring","repeat","subscription"]
def handle(question, intent_name, metadata, retriever):
    raw=retriever.query(question)
    data= raw if isinstance(raw,dict) else json.loads(raw)
    answer="Recurring merchants detected."
    return {"intent":INTENT_NAME,"answer":answer,"details":{},"chart":None,"data":data}
