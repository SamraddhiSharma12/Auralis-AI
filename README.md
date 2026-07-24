# Auralis AI

**A voice-and-text customer support agent that actually knows when it doesn't know something.**

Auralis AI combines retrieval-augmented generation (RAG) with a ReAct reasoning agent to answer customer support questions grounded in a real knowledge base — and, just as importantly, to recognize when a question is out of scope or when a human should take over.

**Live Demo:** [https://auralis-ai.streamlit.app/](#) 
**API Docs:** [QUICKSTART.md](./QUICKSTART.md)

---

## Try it yourself

The live demo runs in text-only mode (see [Limitations](#limitations) below). Here are a few questions to get a feel for what it can do:

**Things it handles well:**
- "What is your refund policy?"
- "How do I track my order?"
- "Do you ship internationally?"
- "What payment methods do you accept?"

**Escalation handling** — try this and notice it routes to a human instead of guessing:
- "I was charged twice for the same order, can I speak to a manager?"

**Out-of-scope detection** — try this and notice it says so, instead of making something up:
- "What is the capital of India?"
- "Write me a poem about the ocean"

---

## Limitations

Being upfront about these matters more to me than pretending they don't exist:

- **Text-only on the hosted demo.** Voice input/output is fully built and works locally (Whisper STT + Edge-TTS) — see [Local Setup](#local-setup-with-full-audio) below to try it. It's disabled on the hosted version because free-tier hosting (both Render and Streamlit Cloud) doesn't have enough memory/system libraries to run STT/TTS reliably alongside the LLM and knowledge base.
- **Cold start delay.** The backend (Render free tier) spins down after inactivity. The first request after idle time can take 20-90 seconds while it wakes up. If your first message seems to hang or times out, just try sending it again.
- **Occasional CPU throttling.** Streamlit Community Cloud's free tier may temporarily throttle CPU during heavy usage. The app still works, just a bit slower until the throttle clears.
- **Health status may show "unhealthy" on first load.** The backend uses lazy-loading for STT/TTS — they only initialize on first actual use, not at startup. Until that happens, the health check reports them as "not ready," which is expected and not an error. The LLM and knowledge base are ready immediately.
- **Escalation detection is keyword-based**, not full intent recognition — it catches common phrasings ("speak to a manager," "human agent") but won't catch every possible way someone might ask for a human.
- **Out-of-scope detection uses a fixed relevance-distance threshold**, tuned against a small internal test set. It's a heuristic, not a perfect classifier.
- **LLM inference runs on Groq's free tier**, which enforces a token-per-minute rate limit. Heavy, rapid testing may occasionally trigger a rate-limit delay.

---

## Local Setup (with full audio)

To run the complete voice + text experience locally:

```bash
git clone https://github.com/SamraddhiSharma12/Auralis-AI.git
cd Auralis-AI
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your own Groq API key (free at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

Start the backend:
```bash
uvicorn src.api.server:app --reload
```

In a separate terminal, start the frontend:
```bash
streamlit run streamlit_app.py
```

Full voice recording and playback work out of the box locally, since your machine has the system audio libraries (PortAudio) that cloud hosting doesn't provide by default.

---

## Documentation

For full API reference — request/response schemas, error handling, and endpoint details — see the [Quickstart Guide](./QUICKSTART.md), written in the style of Stripe's developer documentation.

---

## Tech Stack

`Python` `FastAPI` `LangChain` `ChromaDB` `Groq (Llama 3.1)` `Streamlit` `Whisper` `Edge-TTS` `Render` `Streamlit Community Cloud`