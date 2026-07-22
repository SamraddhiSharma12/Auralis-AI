"""
Batch evaluation script for Auralis AI /chat/text endpoint.

Usage:
    1. Make sure your FastAPI server is running (uvicorn src.api.server:app --reload)
    2. In a SEPARATE terminal, run: python run_eval.py
    3. Results print to console AND save to eval_results.csv

Requires: pip install requests  (only if not already installed)
"""

import requests
import time
import csv
import re

BASE_URL = "http://localhost:8000/chat/text"

# ---- Add/edit your test queries here ----
# category is just a label for your own organization (returns, shipping, escalation, etc.)
time.sleep(15) 
TEST_QUERIES = [
    {"category": "Returns",     "text": "What is your refund policy?"},
    {"category": "Shipping",    "text": "How do I track my order?"},
    {"category": "Product FAQ", "text": "Do you ship internationally?"},
    {"category": "Escalation",  "text": "I was charged twice for the same order, can I speak to a manager?"},
    {"category": "Out-of-scope","text": "What is the capital of France?"},
    # Add more here, e.g.:
    # {"category": "Billing",   "text": "Why was I charged an extra fee?"},
]

def extract_top_distance(response_text: str):
    """Pulls the first 'relevance distance: X.XXX' value found in the response, if any."""
    match = re.search(r"relevance distance:\s*([\d.]+)", response_text)
    return float(match.group(1)) if match else None

def run_eval():
    results = []

    for i, item in enumerate(TEST_QUERIES, start=1):
        print(f"[{i}/{len(TEST_QUERIES)}] Sending: {item['text']}")
        try:
            start = time.time()
            resp = requests.post(BASE_URL, json={"text": item["text"]}, timeout=30)
            elapsed = round((time.time() - start) * 1000, 1)  # ms, client-side timing

            if resp.status_code != 200:
                print(f"    ERROR: status {resp.status_code} - {resp.text[:200]}")
                results.append({
                    "category": item["category"],
                    "query": item["text"],
                    "status": resp.status_code,
                    "server_processing_time_ms": None,
                    "client_roundtrip_ms": elapsed,
                    "top_relevance_distance": None,
                    "response_snippet": resp.text[:200],
                })
                continue

            data = resp.json()
            response_text = data.get("response_text", "")
            server_time = data.get("processing_time_ms")
            top_distance = extract_top_distance(response_text)

            results.append({
                "category": item["category"],
                "query": item["text"],
                "status": 200,
                "server_processing_time_ms": server_time,
                "client_roundtrip_ms": elapsed,
                "top_relevance_distance": top_distance,
                "response_snippet": response_text[:150].replace("\n", " ") + "...",
            })
            print(f"    OK - server: {server_time}ms, top distance: {top_distance}")

        except requests.exceptions.RequestException as e:
            print(f"    FAILED to reach server: {e}")
            results.append({
                "category": item["category"],
                "query": item["text"],
                "status": "connection_error",
                "server_processing_time_ms": None,
                "client_roundtrip_ms": None,
                "top_relevance_distance": None,
                "response_snippet": str(e),
            })

    # ---- Save to CSV ----
    with open("eval_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # ---- Print summary ----
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r["status"] == 200]
    if successful:
        avg_server_time = sum(r["server_processing_time_ms"] for r in successful) / len(successful)
        distances = [r["top_relevance_distance"] for r in successful if r["top_relevance_distance"] is not None]
        avg_distance = sum(distances) / len(distances) if distances else None

        print(f"Total queries tested: {len(results)}")
        print(f"Successful responses: {len(successful)}")
        print(f"Average server processing time: {avg_server_time:.1f}ms")
        if avg_distance:
            print(f"Average top relevance distance: {avg_distance:.3f}")
    else:
        print("No successful responses — check server is running.")

    print(f"\nFull results saved to: eval_results.csv")
    print("Open this file and manually mark each response as Correct/Partial/Hallucinated")
    print("to get your grounding accuracy percentage (e.g. '18/22 = 82% correctly grounded').")


if __name__ == "__main__":
    run_eval()
