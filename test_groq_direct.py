from dotenv import load_dotenv
import os

load_dotenv(override=True)

from groq import Groq

key = os.getenv("GROQ_API_KEY")
print("Using key of length:", len(key) if key else "None")

client = Groq(api_key=key)

try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say hello"}],
        model="llama-3.1-8b-instant"
    )
    print("SUCCESS:", response.choices[0].message.content)
except Exception as e:
    print("FAILED:", e)