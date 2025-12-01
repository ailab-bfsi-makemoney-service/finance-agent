from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

for m in client.models.list().data:
    print(m.id)
