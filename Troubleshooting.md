# Troubleshooting Guide

Real issues encountered while building and deploying Auralis AI, and how they were diagnosed and fixed. Written so the next person (including future me) doesn't have to re-debug from scratch.

---

## 1. `ImportError` / build failures on Python 3.13

**Symptom:** Fresh installs on Python 3.13 fail during `pip install`, with `numpy` unable to build or import correctly.

**Cause:** At the time of development, `numpy` (and several of its downstream dependents in the LangChain ecosystem) didn't yet ship stable wheels for Python 3.13. The failure isn't in your code — it's an environment compatibility gap.

**Fix:** Pin the project to Python 3.11.

```bash
python3.11 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**How to confirm this is your issue:** Run `python --version`. If you're on 3.13 and seeing build errors specifically from `numpy` or C-extension packages, this is almost certainly it.

---

## 2. App crashes / OOM on Render (512MB instance)

**Symptom:** The backend deploys successfully, responds to a few requests, then the Render instance restarts with an out-of-memory error — no clear stack trace pointing to the cause.

**Cause:** `sentence-transformers` (via `torch`) was loaded at startup for embedding generation. Both libraries are memory-heavy, and on a 512MB instance, loading the model alone was enough to exhaust available memory before any real traffic hit the app.

**Fix:** Removed the `torch`/`sentence-transformers` dependency entirely and switched to a lighter embedding path compatible with the memory ceiling. If you need local embeddings on a constrained instance, consider a smaller ONNX-based model or an API-based embedding call instead of loading a full torch model in-process.

**How to confirm this is your issue:** Check Render's memory graph for the instance right before a restart — a spike close to the 512MB ceiling right at startup (not under load) points to a model being loaded into memory, not a traffic problem.

---

## 3. Environment variables silently using stale/wrong values

**Symptom:** Updating a value in `.env` (like an API key or config flag) doesn't seem to take effect — the app keeps behaving like the old value is still set, with no error thrown.

**Cause:** `load_dotenv()` by default does **not** override variables that are already set in the environment (e.g., from a previous shell session, a system-level env var, or a prior `.env` load). It silently no-ops instead of warning you.

**Fix:**

```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

**How to confirm this is your issue:** Print the value of the relevant env var right after `load_dotenv()` and compare it to what's actually in your `.env` file. If they differ, this is the cause.

---

## 4. Accidentally committed a real API key

**Symptom:** A real (not placeholder) API key ends up in a tracked file — commonly `.env.example`, meant to be a template.

**Cause:** Copy-pasting an actual `.env` into `.env.example` for convenience during setup, then committing before swapping in a placeholder.

**Fix:**
1. Rotate/revoke the exposed key immediately at the provider (don't skip this even if you're about to clean the repo — assume it's compromised the moment it's pushed).
2. Remove it from git history, not just the latest commit — a simple new commit deleting the key still leaves it recoverable in history:
```bash
git filter-repo --path .env.example --invert-paths
# or, for smaller repos: BFG Repo-Cleaner
```
3. Force-push the cleaned history and have any collaborators re-clone.

**How to confirm this is your issue:** Search your git history, not just your working directory: `git log -p -- .env.example` will show you if a real key was ever committed, even if it's since been "removed."

---

## 5. Tool calls hanging or failing intermittently under async routes

**Symptom:** Some requests to endpoints that trigger LangChain tool calls hang indefinitely or throw inconsistent errors, while others complete fine.

**Cause:** Mixing sync-only tool implementations with an async FastAPI route — the sync call blocks the event loop instead of yielding control, so behavior depends on what else is queued at that moment.

**Fix:** Ensure tool functions called from async routes are either genuinely async (`async def`) or explicitly run in a thread pool executor (`run_in_executor`) so they don't block the event loop.

**How to confirm this is your issue:** If failures are inconsistent and correlate with concurrent requests rather than a specific input, suspect blocking calls in an async context before anything else.

---

## General debugging approach

Across these issues, the pattern that helped most: reproduce with the smallest possible input first, and check environment/infrastructure (Python version, memory limits, env loading order) before assuming the bug is in application logic. Most of the above weren't logic bugs — they were mismatches between the code's assumptions and the environment it ran in.