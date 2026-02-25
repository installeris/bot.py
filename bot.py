import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 💎 KOKYBIŠKO TURINIO BOTAS (Final URL Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Kategorijų ID
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

# 2026 m. stabiliausias URL formatas mokamam planui
# Atkreipk dėmesį: v1beta/models/ID:generateContent
MODEL_ID = "gemini-1.5-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n🚀 Ruošiamas pilnas straipsnis: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Griežtas promptas kokybei užtikrinti
    prompt = (
        f"Write a comprehensive 800-word financial biography for {politician_name} for 2026. \n"
        f"1. STRUCTURE: Use H2 and H3 HTML tags. Detailed career, asset breakdown, and investment strategy. \n"
        f"2. NET WORTH: Use full figures (e.g., $15,400,000). \n"
        f"3. CHART: Return 'net_worth_history' as '2020:10000000,2022:12500000,2026:15400000'. \n"
        f"4. SOURCES: Include 2-3 REAL links using <a href='...'>Source Name</a> tags. \n"
        f"5. CATEGORIES: Select multiple from {list(CAT_MAP.keys())}. \n"
        f"Return ONLY valid JSON."
    )

    safety_settings = [
        {"category": c, "threshold": "BLOCK_NONE"} 
        for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
    ]

    try:
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.7},
            "safetySettings": safety_settings
        })
        
        resp_json = response.json()
        
        # Jei vis dar meta 404, išspausdiname visą atsakymą derinimui
        if 'candidates' not in resp_json:
            print(f"  ❌ API Klaida: {resp_json}")
            return

        raw_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(raw_text)

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data.get("article", ""),
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
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
        else:
            print(f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Klaida apdorojant {politician_name}: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5) # Greitas kėlimas mokamam planui
