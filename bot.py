import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 💎 KOKYBIŠKO TURINIO BOTAS (Paid Tier) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Nustatymai
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

def get_wiki_image(name):
    """Randa aukštos kokybės nuotrauką iš Wikipedia."""
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    """Įkelia nuotrauką į WP Media Library."""
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n🚀 Ruošiamas pilnas straipsnis: {politician_name}")
    
    # 1. Nuotrauka
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # 2. Kokybiškas Promptas
    prompt = (
        f"Write a detailed, 800-word SEO-optimized financial biography for {politician_name} in 2026. \n"
        f"1. ARTICLE: Use H2/H3 tags. Discuss career, wealth sources, and recent 2024-2025 financial trends. \n"
        f"2. NET WORTH: Be precise (e.g., $15,400,000, not 15.4). If old data, apply 8% annual growth. \n"
        f"3. CHART: Create 'net_worth_history' string (e.g., '2020:10000000,2021:11000000,2026:15400000'). \n"
        f"4. CATEGORIES: Pick from: {list(CAT_MAP.keys())}. \n"
        f"Return ONLY JSON: {{"
        f"\"article\": \"HTML content\", \"net_worth\": \"$XX,XXX,XXX\", \"job_title\": \"Title\", "
        f"\"history\": \"2020:X,2026:Y\", \"sources_html\": \"<a href='...'>Source</a>\", "
        f"\"source_of_wealth\": [\"Real Estate Holdings\"], \"key_assets\": \"Specific assets\", "
        f"\"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS],
                "main_assets": data.get("key_assets", ""),
                "sources": data.get("sources_html", "")
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", "")
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} (ID: {res.json().get('id')})")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
