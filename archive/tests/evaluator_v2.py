"""
Finance-Agent Automated Evaluator (v2)
--------------------------------------
Runs all test questions from FinanceAgent_FY25_TestSuite.csv against the local /ask endpoint,
and writes a rich evaluation report with:

- Expected vs predicted intent
- Semantic similarity score for intents
- Answer snippet for quick inspection
- Optional numeric accuracy (if Expected Value column is present)

Usage:
  1. Start the API:
        uvicorn app:app --reload
  2. Run:
        python -m tests.evaluator_v2
     or:
        python tests/evaluator_v2.py
  3. Open the generated CSV under tests/results/ in Excel/Sheets.

Notes:
  - AUTH assumes basic auth is enabled on /ask; update if needed.
  - If no Expected Value column exists, numeric_error fields remain blank.
"""

import csv
import json
import os
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import requests

# ===================== CONFIG =====================

# Where your FastAPI agent is running
API_URL = os.environ.get("FINANCE_AGENT_API_URL", "http://127.0.0.1:8000/ask")

# Basic auth for your beta environment (update to match your app.py security)
AUTH_USER = os.environ.get("FINANCE_AGENT_USER", "betauser")
AUTH_PASS = os.environ.get("FINANCE_AGENT_PASS", "betapass")
AUTH = (AUTH_USER, AUTH_PASS) if AUTH_USER and AUTH_PASS else None

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_SUITE_PATH = BASE_DIR / "FinanceAgent_FY25_TestSuite.csv"

RESULTS_DIR = (BASE_DIR / "tests" / "results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 20      # seconds
REQUEST_DELAY = 0.25      # seconds between calls

# ==================================================


def semantic_score(a: str, b: str) -> float:
    """Rough similarity between two short strings (e.g., intents/categories)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a.lower(), b.lower()).ratio(), 3)


def extract_first_number(text: str):
    """
    Extract the first numeric value from a text.
    Supports things like: "$1,234.56", "1234.56", "1234".
    Returns float or None.
    """
    if not text:
        return None
    # Look for money-like or numeric patterns
    match = re.search(r"\$?\s*([0-9][0-9,]*\.?[0-9]*)", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def load_tests(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Test suite CSV not found at: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def call_agent(question: str):
    """POST to /ask and return parsed JSON or error payload."""
    try:
        resp = requests.post(
            API_URL,
            json={"question": question},
            auth=AUTH,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        return {
            "intent": "request_error",
            "answer": f"[client-side error: {e}]",
        }

    if not resp.ok:
        # Non-2xx from API
        try:
            body = resp.text[:300]
        except Exception:
            body = "<unreadable>"
        return {
            "intent": f"http_{resp.status_code}",
            "answer": f"[server error] {body}",
        }

    try:
        return resp.json()
    except json.JSONDecodeError:
        return {
            "intent": "invalid_json",
            "answer": resp.text[:300],
        }


def run_evaluation():
    tests = load_tests(TEST_SUITE_PATH)
    if not tests:
        raise ValueError("Test suite CSV is empty.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"eval_results_{ts}.csv"

    results = []

    print(f"\n🚀 Running {len(tests)} tests against {API_URL}\n")

    for i, row in enumerate(tests, start=1):
        intent_expected = (row.get("Intent Category") or "").strip()

        # Prefer Test Question 1; fall back to 2 if empty
        q1 = (row.get("Test Question 1") or "").strip()
        q2 = (row.get("Test Question 2") or "").strip()
        question = q1 or q2
        if not question:
            continue

        # Optional: Expected numeric value (if you add this column later)
        # e.g., "Expected Value" = 1234.56
        expected_value_raw = (row.get("Expected Value") or "").strip()
        try:
            expected_value = float(expected_value_raw) if expected_value_raw else None
        except ValueError:
            expected_value = None

        payload = call_agent(question)
        intent_pred = (payload.get("intent") or "").strip()
        answer = (payload.get("answer") or json.dumps(payload)) or ""

        # Intent similarity
        intent_sim = semantic_score(intent_expected, intent_pred)

        # Numeric extraction & error
        predicted_value = extract_first_number(answer)
        numeric_error = None
        numeric_error_pct = None

        if expected_value is not None and predicted_value is not None:
            numeric_error = round(predicted_value - expected_value, 4)
            if expected_value != 0:
                numeric_error_pct = round((numeric_error / expected_value) * 100, 2)

        results.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "question": question,
                "expected_intent": intent_expected,
                "predicted_intent": intent_pred,
                "intent_semantic_match": intent_sim,
                "expected_value": expected_value if expected_value is not None else "",
                "predicted_value": predicted_value if predicted_value is not None else "",
                "numeric_error": numeric_error if numeric_error is not None else "",
                "numeric_error_pct": numeric_error_pct if numeric_error_pct is not None else "",
                "answer_snippet": answer[:280].replace("\n", " "),
            }
        )

        print(
            f"[{i}/{len(tests)}] "
            f"Intent: '{intent_expected}' → '{intent_pred}' "
            f"(sim={intent_sim})"
            + (
                f" | val: {predicted_value} vs {expected_value} (Δ={numeric_error_pct}%)"
                if numeric_error_pct is not None
                else ""
            )
        )

        time.sleep(REQUEST_DELAY)

    # Write CSV
    if results:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)

        print(f"\n✅ Evaluation complete → {out_path}")
        print("   Filter rows where:")
        print("   - intent_semantic_match < 0.6  (routing issues)")
        print("   - numeric_error_pct not blank and abs(numeric_error_pct) > 10 (bad math/data)")
    else:
        print("⚠️ No results written. Check that your test CSV has questions.")


if __name__ == "__main__":
    run_evaluation()
