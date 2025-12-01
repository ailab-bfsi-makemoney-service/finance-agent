from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
proj = os.getenv("OPENAI_PROJECT_ID")

print(f"🔑 Key prefix: {key[:8]}...")
print(f"🧭 Project ID: {proj}")

client = OpenAI(api_key=key)
client.project = proj  # <-- important line

try:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
    )
    print("✅ Success! Model reply:", resp.choices[0].message.content)
except Exception as e:
    print("❌ Request failed:", e)
