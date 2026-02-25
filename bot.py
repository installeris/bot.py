import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Chart, Image & NetWorth Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

WEALTH_OPTIONS = [
    "Stock Market Investments", "Real Estate Holdings", "Venture Capital", 
    "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties", 
    "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets"
]

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

def get_working_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        for m in models:
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except: return None

ACTIVE_MODEL = get_working_model()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"

def get_wiki_image(name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Ieškome per Wikipedia paiešką, kad gautume tiksliausią puslapį
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages|images&titles={name}&pithumbsize=1000"
        res = requests.get(search_url, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                return pages[pg]["thumbnail"]["source"]
    except: return None
    return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if img_res.status_code == 200:
            headers = {
                "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
                "Content-Type": "image/jpeg"
            }
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            if res.status_code == 201:
                return res.json()["id"]
    except: return None
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    wiki_img = get_wiki_image(politician_name)
    img_id = upload_to_wp(wiki_img, politician_name)
    if img_id: print(f"  📸 Nuotrauka įkelta (ID: {img_id})")
    else: print("  ⚠️ Nuotraukos rasti nepavyko.")

    prompt = (
        f"Research {politician_name}. Write an 800-word SEO article in English about their net worth. \n"
        f"1. Net worth: Give a clear estimate, e.g., '$14,500,000'. Do not use short versions like $2.3. \n"
        f"2. Chart data: Generate wealth history from 2019 to 2026. Format EXACTLY like this: 2019:1000000,2020:1200000,2021:1500000... \n"
        f"3. Source of Wealth: Pick from: {WEALTH_OPTIONS}. \n"
        f"4. Return ONLY JSON: {{"
        f"\"article\": \"HTML content\", \"net_worth\": \"$15,000,000\", \"job_title\": \"Official Role\", "
        f"\"chart\": \"2019:164000000,2020:175000000...\", \"source_of_wealth\": [], \"key_assets\": \"Specific assets\", "
        f"\"seo_title\": \"SEO Title\", \"seo_desc\": \"Meta Description\", \"cats\": [\"United States (USA)\"]}}"
    )
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        valid_sources = [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS]
        cat_ids = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": cat_ids,
            "featured_media": img_id,
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "wealth_chart": data.get("chart", ""), # Pataisyk 'wealth_chart' į savo tikrą ACF ID
                "source_of_wealth": valid_sources,
                "main_assets": data.get("key_assets", ""),
            },
            "meta": {
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} publikuotas!")
        else:
            print(f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(30)
