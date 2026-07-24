from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("GROQ_API_KEY")

if key is None:
    print("No key found in .env")
else:
    print("Full length:", len(key))
    print("First 8 chars:", key[:8])
    print("Last 6 chars:", key[-6:])
    print("Repr (shows hidden chars like \\r \\n if any):", repr(key))