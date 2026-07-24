from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("GROQ_API_KEY")

if key is None:
    print("GROQ_API_KEY is not set at all (None).")
else:
    print("Length:", len(key))
    print("Starts with gsk_:", key.startswith("gsk_"))
    print("Has double-quote char:", '"' in key)
    print("Has single-quote char:", "'" in key)
    print("Has leading/trailing whitespace:", key != key.strip())