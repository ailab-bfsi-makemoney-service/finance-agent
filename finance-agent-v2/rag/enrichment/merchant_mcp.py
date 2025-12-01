"""
merchant_google_enrichment.py
-------------------------------------
1. Fetches transactions (Food & Drink) from Transaction API
2. Calls Google Places API using merchant name + ZIP code
3. Identifies restaurants and infers cuisine type
4. Updates Neon merchants table
5. Skips merchants outside the beta region (ZIP filter)
"""

import os
import re
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlencode
from dotenv import load_dotenv
from pathlib import Path
from dotenv import load_dotenv
import os
# ---------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------
# ---------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES (explicit .env path)
# ---------------------------------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)
print(f"🔹 Loaded .env from {env_path.resolve()}")

# --- Read environment variables ---
DB_CONN = os.getenv("DB_CONN")
TRANSACTION_API_BASE = os.getenv("TRANSACTION_API_BASE", "").rstrip("/")
TRANSACTION_API_KEY = os.getenv("TRANSACTION_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ZIP_CODE = os.getenv("ZIP_CODE", "93021")
ENRICH_CATEGORIES = os.getenv("ENRICH_CATEGORIES", "Food & Drink").split(",")
HOME_ZIPCODES = [z.strip() for z in os.getenv("HOME_ZIPCODES", "93021").split(",")]
TXN_SINCE_DAYS = int(os.getenv("TXN_SINCE_DAYS", "7"))

# --- Validate required vars ---
REQUIRED = ["DB_CONN", "TRANSACTION_API_BASE", "GOOGLE_API_KEY"]
for var in REQUIRED:
    if not os.getenv(var):
        raise ValueError(f"❌ Missing required environment variable: {var}")

print("✅ Environment loaded successfully.")
print("TRANSACTION_API_BASE_URL =", TRANSACTION_API_BASE)


# Always load .env from the same folder as this script
env_path = Path(__file__).parent / ".env"
print(f"🔹 Loading env file from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Verify one key
print("TRANSACTION_API_BASE_URL =", os.getenv("TRANSACTION_API_BASE_URL"))


# ---------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------
def normalize_name(name: str) -> str:
    """Normalize merchant name for deduplication."""
    return re.sub(r"[^A-Za-z0-9 ]+", "", name or "").strip().upper()

def db():
    """Connect to Postgres (Neon) with autocommit enabled."""
    conn = psycopg2.connect(DB_CONN, cursor_factory=RealDictCursor)
    conn.autocommit = True  # ✅ ensures all inserts/updates are immediately saved
    return conn

def fetch_transactions():
    """Fetch all transactions (or by category if API supports it)."""
    global TRANSACTION_API_BASE, TRANSACTION_API_KEY, ENRICH_CATEGORIES

    category = ENRICH_CATEGORIES[0].strip()
    # Default endpoint (no category filter)
    url = f"{TRANSACTION_API_BASE.rstrip('/')}/transactions"
    headers = {"Accept": "application/json"}
    if TRANSACTION_API_KEY:
        headers["Authorization"] = f"Bearer {TRANSACTION_API_KEY}"

    print(f"\n📡 Fetching transactions from: {url}")

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        txns = r.json()

        if not isinstance(txns, list):
            print("⚠️ Unexpected response:", r.text)
            return []

        print(f"✅ Retrieved {len(txns)} total transactions from API.")

        # 🔍 Optional local filter (since API doesn’t support ?category=)
        filtered = [t for t in txns if t.get("category") in ENRICH_CATEGORIES]
        print(f"✅ Filtered {len(filtered)} transactions matching categories: {ENRICH_CATEGORIES}")

        # Show up to 10 transactions for inspection
        print("\n🔍 [DEBUG] First few transactions:")
        for i, t in enumerate(filtered[:10]):
            merchant = (
                t.get("merchant_name")
                or t.get("description")
                or t.get("vendor")
                or "UNKNOWN"
            )
            date = t.get("transaction_date") or t.get("date") or "N/A"
            print(f"{i+1:03d}. {merchant} | {t.get('category')} | ${t.get('amount')} | {date}")

        if len(filtered) > 10:
            print(f"... ({len(filtered) - 10} more not shown)\n")

        return filtered

    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling Transaction API: {e}")
        print("Response text:", getattr(e.response, 'text', 'No response text'))
        return []

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

    data = r.json()
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    return data

def get_known_merchants(conn):
    """Return set of normalized merchant names already in DB."""
    with conn.cursor() as cur:
        cur.execute("SELECT normalized_name FROM bian.merchants;")
        rows = cur.fetchall()
    if rows:
        dbname, dbuser = rows[0], rows[1]
        print(f"📦 Connected to Neon DB: {dbname} as user {dbuser}")
    else:
        print("⚠️ Could not fetch current database/user info.")
    return set([r["normalized_name"] for r in rows])

def is_in_beta_region(address: str) -> bool:
    """Check if merchant address belongs to beta ZIP region."""
    if not address:
        return True
    for z in HOME_ZIPCODES:
        if z in address:
            return True
    return False

# ---------------------------------------------
# 3. GOOGLE PLACES LOOKUP
# ---------------------------------------------
def find_place(merchant_name, zip_code):
    """Find merchant info using Google Places API."""
    query = f"{merchant_name} {zip_code}"
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "name,formatted_address,types,rating,place_id",
        "key": GOOGLE_API_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return None
    c = candidates[0]
    types = c.get("types", [])
    merchant_type, cuisine = derive_restaurant_type(types, merchant_name)
    return {
        "merchant_name": c.get("name", merchant_name),
        "normalized_name": normalize_name(c.get("name", merchant_name)),
        "merchant_address": c.get("formatted_address"),
        "google_types": json.dumps(types),
        "rating": c.get("rating"),
        "merchant_type": merchant_type,
        "cuisine": cuisine,
        "enrichment_status": "enriched"
    }

def derive_restaurant_type(types, name):
    """Infer restaurant type/cuisine from name and Google 'types'."""
    restaurant_keywords = ["restaurant", "food", "meal_takeaway", "cafe", "bar"]
    merchant_type = "Restaurant" if any(t for t in types if "restaurant" in t) else "Other"

    # Simple heuristic for cuisine
    n = name.lower()
    cuisine = None
    for word, label in [
        ("italian", "Italian"), ("indian", "Indian"), ("mexican", "Mexican"),
        ("thai", "Thai"), ("sushi", "Japanese"), ("japanese", "Japanese"),
        ("chinese", "Chinese"), ("pizza", "Pizza"), ("burger", "Burgers"),
        ("bbq", "BBQ"), ("coffee", "Cafe"), ("cafe", "Cafe")
    ]:
        if word in n:
            cuisine = label
            break

    if not cuisine:
        for t in types:
            if t.endswith("_restaurant") and t != "restaurant":
                cuisine = t.split("_")[0].title()
                break
    return merchant_type, cuisine

# ---------------------------------------------
# 4. UPSERT INTO DATABASE
# ---------------------------------------------
def upsert_merchant(conn, rec):
    sql = """
    INSERT INTO bian.merchants (
        merchant_name,
        normalized_name,
        merchant_type,
        merchant_address,
        google_types,
        rating,
        enrichment_status,
        created_at
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
    ON CONFLICT (normalized_name)
    DO UPDATE SET
        merchant_name = EXCLUDED.merchant_name,
        merchant_type = EXCLUDED.merchant_type,
        merchant_address = EXCLUDED.merchant_address,
        google_types = EXCLUDED.google_types,
        rating = EXCLUDED.rating,
        enrichment_status = EXCLUDED.enrichment_status;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    rec.get("merchant_name"),
                    rec.get("normalized_name"),
                    rec.get("merchant_type"),
                    rec.get("merchant_address"),
                    json.dumps(rec.get("google_types")),
                    rec.get("rating"),
                    rec.get("enrichment_status", "enriched"),
                ),
            )
        conn.commit()
        print(f"✅ DB commit confirmed for merchant: {rec.get('merchant_name')}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error processing {rec.get('merchant_name')}: {e}")
        print("🧾 Record content:", json.dumps(rec, indent=2, default=str))

# ---------------------------------------------
# 5. MAIN ENRICHMENT LOGIC
# ---------------------------------------------
def main():
    print("🚀 Starting Merchant Enrichment (Beta Mode)")
    print(f"🔹 Home ZIPs: {HOME_ZIPCODES}")
    print(f"🔹 Category: {ENRICH_CATEGORIES}")
    txns = fetch_transactions()

    with db() as conn:
        known = get_known_merchants(conn)
        added = 0
        print(f"💾 {len(known)} merchants already in DB.")

        for txn in txns:
            name = txn.get("description")
            if not name:
                continue
            norm = normalize_name(name)
            if norm in known:
                continue

            print(f"🔍 Searching Google for {name} ({ZIP_CODE})")
            try:
                rec = find_place(name, ZIP_CODE)
                if not rec:
                    print(f"⚠️  No Google match for {name}")
                    continue

                # Beta region filter
                if not is_in_beta_region(rec.get("merchant_address", "")):
                    print(f"🌐 Skipping {name} — outside beta ZIP region.")
                    continue

                if rec["merchant_type"] == "Restaurant":
                    upsert_merchant(conn, rec)
                    added += 1
                    print(f"✅ Added {rec['merchant_name']} ({rec.get('cuisine') or 'Unknown'})")
                else:
                    print(f"⚠️  {name} not identified as restaurant.")
            except Exception as e:
                print(f"❌ Error processing {name}: {e}")

        print(f"\n✅ Completed enrichment — {added} merchants added/updated.")

# ---------------------------------------------
# 6. RUN SCRIPT
# ---------------------------------------------
if __name__ == "__main__":
    main()
