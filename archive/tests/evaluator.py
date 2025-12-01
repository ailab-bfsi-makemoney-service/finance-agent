"""
Finance-Agent Automated Evaluator
---------------------------------
Runs every test question from your FY25 test suite against the local /ask endpoint
and logs predicted intent, answer snippet, and similarity score.

Usage:
    1. Make sure the agent API is running (uvicorn app:app --reload).
    2. Run:  python tests/evaluator.py
    3. Results: tests/results/eval_results_<timestamp>.csv
"""

import csv, json, os, time, requests
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# ============== CONFIGURATION ==============
API_URL = "http://127.0.0.1:8000/ask"        # local endpoint
AUTH = ("betauser", "betapass")              # basic auth credentials
TEST_FILE = Path(__file__).resolve().parents[1] / "FinanceAgent_FY25_TestSuite.csv"
RESULT_DIR = Path(__file__).resolve().parent / "results"
RESULT_DIR.mkdir(exist_ok=True)
# ===========================================

def semantic_score(a: str, b: str) -> float:
    """Rough string similarity between expected and predicted intents."""
    return round(SequenceMatcher(None, a.lower(), b.lower()).ratio(), 3)

def run_tests():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULT_DIR / f"eval_results_{ts}.csv"

    with open(TEST_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tests = list(reader)

    results = []
    print(f"Running {len(tests)} test questions...\n")

    for i, row in enumerate(tests, 1):
        q = row.get("Test Question 1") or ""
        expected_intent = row.get("Intent Category") or "Unknown"

        try:
            r = requests.post(API_URL, auth=AUTH, json={"question": q}, timeout=20)
            data = r.json() if r.ok else {}
            predicted_intent = data.get("intent", "error")
            answer = data.get("answer", "")
            sim = semantic_score(expected_intent, predicted_intent)
        except Exception as e:
            predicted_intent, answer, sim = "exception", str(e), 0.0

        results.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": q,
            "expected_intent": expected_intent,
            "predicted_intent": predicted_intent,
            "semantic_match": sim,
            "answer_snippet": answer[:200].replace("\n", " ")
        })

        print(f"[{i}/{len(tests)}] {expected_intent} → {predicted_intent} (score={sim})")
        time.sleep(0.3)  # polite throttle

    # Write results
    with open(result_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Evaluation complete → {result_file}")
    print("Open in Excel/Sheets and filter by low semantic_match (<0.5) to find weak spots.")

if __name__ == "__main__":
    run_tests()
