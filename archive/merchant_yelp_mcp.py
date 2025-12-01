import os
import re
import json
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI
from requests.exceptions import SSLError, ConnectionError, ReadTimeout

# ------------------------------------------
# 0) ENVIRONMENT & CLIENTS
# ------------------------------------------
load_dotenv()

DB_CONN = os.getenv("DB_CONN")
YELP_API_KEY = os.getenv("YELP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

YELP_API_URL = "https://api.yelp.com/v3/businesses/search"
YELP_HEADERS = {"Authorization": f"Bearer {YELP_API_KEY}"}

# Optional home geofence
HOME_COORDINATES = os.getenv("HOME_COORDINATES")  # "34.2856,-118.8820"
HOME_RADIUS_METERS = int(os.getenv("HOME_RADIUS_METERS", "25000"))
HOME_ZIPCODES = [z.strip() for z in os.getenv("HOME_ZIPCODES", "93021,93063,93065,91362,91360").split(",")]
HOME_CITIES = [c.strip() for c in os.getenv(
    "HOME_CITIES",
    "Moorpark, CA; Thousand Oaks, CA; Simi Valley, CA; Newbury Park, CA; Agoura Hills, CA; Camarillo, CA; Westlake Village, CA"
).split(";")]

client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------------------
# 1) DATABASE CONNECTION
# ------------------------------------------
def get_db():
    conn = psycopg2.connect(DB_CONN, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

# ------------------------------------------
# 2) SAFE REQUEST WRAPPER (RETRY LOGIC)
# ------------------------------------------
def safe_get(url, headers=None, params=None, retries=3, delay=2):
    """Wrapper to retry transient SSL or connection errors."""
    for attempt in range(1, retries + 1):
        try:
            return requests.get(url, headers=headers, params=params, timeout=15)
        except (SSLError, ConnectionError, ReadTimeout) as e:
            print(f"⚠️ Network/SSL error on attempt {attempt}: {e}")
            if attempt < retries:
                time.sleep(delay * attempt)
                print("🔁 Retrying...")
            else:
                print("❌ Yelp request failed after retries.")
                return None

# ------------------------------------------
# 3) NAME NORMALIZATION
# ------------------------------------------
NOISE_PREFIXES = [
    r"SQ\s*\*", r"POS\s*\*", r"US\s*\*", r"DBA\s*", r"PAYPAL\s*", r"VENMO\s*",
    r"AMZN\s*", r"AMAZON\s*", r"ETSY\s*", r"EBAY\s*", r"SHOPIFY\s*"
]

def normalize_name(name: str) -> str:
    """Aggressive cleanup for better Yelp matching."""
    if not name:
        return ""
    s = name.upper()
    for p in NOISE_PREFIXES:
        s = re.sub(p, "", s)
    s = re.sub(r"\b(CA|TX|AZ|NV|OR|WA|NY|NJ|MA|IL|FL)\b", "", s)
    s = re.sub(r"[^A-Z0-9' ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if re.search(r"\bRESTAUR?", s) and "RESTAURANT" not in s:
        s = re.sub(r"\bRESTAUR[AN]*\b", "RESTAURANT", s)
    return s.title()

def term_variants(base: str) -> list:
    """Generate alternate search terms for truncated merchant names."""
    parts = base.split()
    variants, seen = [], set()

    def add(v):
        v = v.strip()
        if v and v not in seen:
            variants.append(v)
            seen.add(v)

    add(base)
    add(f"{base} Restaurant")
    if len(parts) > 1:
        add(" ".join(parts[:-1]))
    if len(parts) >= 3:
        add(" ".join(parts[:3]))
    if len(parts) >= 2:
        add(" ".join(parts[:2]))
    return variants

# ------------------------------------------
# 4) YELP SEARCH HELPERS
# ------------------------------------------
def yelp_search(term: str, location: str = None, lat: float = None, lon: float = None, radius: int = None):
    """Execute Yelp API search for a single term."""
    params = {
        "term": term,
        "categories": "restaurants",
        "limit": 1,
        "sort_by": "best_match"
    }
    if location:
        params["location"] = location
        params["radius"] = min(HOME_RADIUS_METERS, 40000)
    elif lat and lon:
        params["latitude"] = lat
        params["longitude"] = lon
        params["radius"] = radius or HOME_RADIUS_METERS

    r = safe_get(YELP_API_URL, headers=YELP_HEADERS, params=params)
    if not r:
        return None
    if r.status_code != 200:
        print(f"⚠️ Yelp error {r.status_code} for term='{term}', loc='{location}'")
        return None

    data = r.json()
    if data.get("businesses"):
        b = data["businesses"][0]
        return {
            "match_name": b.get("name"),
            "categories": b.get("categories", []),
            "address": b.get("location", {}).get("display_address", []),
            "rating": b.get("rating"),
            "city": b.get("location", {}).get("city"),
            "state": b.get("location", {}).get("state"),
            "zip": b.get("location", {}).get("zip_code"),
        }
    return None

def query_yelp_multi(merchant_name: str):
    """Multi-pass Yelp search: lat/lon → ZIP → city → California."""
    base = normalize_name(merchant_name)
    variants = term_variants(base)

    lat, lon = (None, None)
    if HOME_COORDINATES:
        try:
            lat, lon = [float(x) for x in HOME_COORDINATES.split(",")]
        except Exception:
            pass

    # Lat/lon pass
    if lat and lon:
        for term in variants:
            print(f"🔎 Yelp try: term='{term}' near ({lat},{lon})")
            hit = yelp_search(term, lat=lat, lon=lon)
            if hit:
                print(f"✅ Yelp(latlon) {merchant_name} → {hit['match_name']} ({hit['city']})")
                return hit, term, f"latlon({lat},{lon})"

    # ZIP pass
    for z in HOME_ZIPCODES:
        for term in variants:
            print(f"🔎 Yelp try: term='{term}' in ZIP {z}")
            hit = yelp_search(term, location=z)
            if hit:
                print(f"✅ Yelp(zip) {merchant_name} → {hit['match_name']} ({hit['city']})")
                return hit, term, z

    # City pass
    for city in HOME_CITIES:
        for term in variants:
            print(f"🔎 Yelp try: term='{term}' in city '{city}'")
            hit = yelp_search(term, location=city)
            if hit:
                print(f"✅ Yelp(city) {merchant_name} → {hit['match_name']} ({hit['city']})")
                return hit, term, city

    # Region pass
    for region in ["California, USA", "United States"]:
        for term in variants:
            print(f"🔎 Yelp try: term='{term}' in region '{region}'")
            hit = yelp_search(term, location=region)
            if hit:
                print(f"✅ Yelp(region) {merchant_name} → {hit['match_name']} ({hit['city']})")
                return hit, term, region

    print(f"🚫 Yelp no match for '{merchant_name}' after {len(variants)} variants.")
    return None, None, None

# ------------------------------------------
# 5) LLM FALLBACK
# ------------------------------------------
def infer_from_llm(merchant_name: str):
    prompt = f"""
    The user's home region is Moorpark, California (ZIP 93021).
    Merchant name: "{merchant_name}"
    Category: Food & Drink.
    Predict the most likely restaurant cuisine (e.g., Italian, Mexican, Indian)
    and a plausible city/state in the US if known.
    Respond as strict JSON with keys "cuisine" and "location".
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        print(f"🤖 LLM inference for {merchant_name}: {content}")
        try:
            return json.loads(content)
        except Exception:
            return {"cuisine": "Unknown", "location": None}
    except Exception as e:
        print(f"❌ LLM inference failed for {merchant_name}: {e}")
        return None

# ------------------------------------------
# 6) HYBRID ENRICHMENT
# ------------------------------------------
def hybrid_enrich(merchant_name: str):
    hit, term_used, loc_used = query_yelp_multi(merchant_name)
    if hit:
        return {
            "merchant_type": json.dumps(hit["categories"]),
            "merchant_address": hit["address"],
            "rating": hit["rating"],
            "enrichment_status": "enriched",
            "confidence": 1.0,
            "last_yelp_query": {"term": term_used, "location": loc_used}
        }

    inferred = infer_from_llm(merchant_name)
    if inferred:
        loc = inferred.get("location")
        cuisine = inferred.get("cuisine", "Unknown")
        if loc:
            base = normalize_name(merchant_name)
            for term in term_variants(base):
                print(f"🔁 Yelp retry with LLM loc: term='{term}' loc='{loc}'")
                hit2 = yelp_search(term, location=loc)
                if hit2:
                    return {
                        "merchant_type": json.dumps(hit2["categories"]),
                        "merchant_address": hit2["address"],
                        "rating": hit2["rating"],
                        "enrichment_status": "enriched",
                        "confidence": 0.8,
                        "last_yelp_query": {"term": term, "location": loc}
                    }
        return {
            "merchant_type": json.dumps([{"alias": cuisine.lower(), "title": cuisine}]),
            "merchant_address": loc,
            "rating": None,
            "enrichment_status": "inferred",
            "confidence": 0.6,
            "last_yelp_query": None
        }

    return {
        "merchant_type": json.dumps([{"alias": "unknown", "title": "Unknown"}]),
        "merchant_address": None,
        "rating": None,
        "enrichment_status": "missing",
        "confidence": 0.2,
        "last_yelp_query": None
    }

# ------------------------------------------
# 7) UPSERT INTO bian.merchants
# ------------------------------------------
def upsert_merchant(conn, merchant_name, data):
    sql = """
        INSERT INTO bian.merchants (
            merchant_name, normalized_name, merchant_type,
            merchant_address, rating, enrichment_status, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (normalized_name)
        DO UPDATE SET
            merchant_type = EXCLUDED.merchant_type,
            merchant_address = EXCLUDED.merchant_address,
            rating = EXCLUDED.rating,
            enrichment_status = EXCLUDED.enrichment_status;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            merchant_name,
            merchant_name.upper(),
            data.get("merchant_type"),
            json.dumps(data.get("merchant_address")) if isinstance(data.get("merchant_address"), list)
                else data.get("merchant_address"),
            data.get("rating"),
            data.get("enrichment_status")
        ))

# ------------------------------------------
# 8) MAIN
# ------------------------------------------
def main():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT description AS merchant_name
            FROM bian.cc_transaction
            WHERE category = 'Food & Drink'
              AND description NOT IN (SELECT merchant_name FROM bian.merchants);
        """)
        rows = cur.fetchall()

    print(f"🍽 Found {len(rows)} new merchants to enrich")

    for row in rows:
        name = row["merchant_name"]
        print(f"\n🔍 Enriching: {name}")
        data = hybrid_enrich(name)
        upsert_merchant(conn, name, data)
        print(f"✅ {name} → {data.get('enrichment_status')} (conf={data.get('confidence')})")

    conn.close()
    print("\n🏁 Enrichment completed.")

if __name__ == "__main__":
    main()
