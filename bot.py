import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (ACF CHART & SEO FIX) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# --- API KONFIGŪRACIJA ---
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

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

# --- FUNKCIJOS ---
def get_wiki_image(name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000"
        res = requests.get(url, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, stream=True)
        headers = {
            "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Griežtas SEO ir ACF Chart promptas
    prompt = (
        f"Research {politician_name}. Write an 800-word SEO article. \n"
        f"1. Generate data for a wealth chart (2019-2025). Format: years and values separated by commas. \n"
        f"2. Return ONLY JSON: {{"
        f"\"article\": \"HTML content\", "
        f"\"net_worth\": \"e.g. $5 Million\", "
        f"\"job_title\": \"Official role\", "
        f"\"chart_data\": \"2019,2020,2021,2022,2023,2024,2025|1M,1.2M,1.5M,2M,3M,4M,5M\", "
        f"\"seo_title\": \"Keyword rich title\", "
        f"\"seo_desc\": \"Meta description\", "
        f"\"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        cat_ids = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]

        # WordPress POST paketas
        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": cat_ids,
            "featured_media": img_id,
            # ACF LAUKAI (Pataisyk 'wealth_chart' pagal savo tikrąjį ACF slug!)
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "wealth_chart": data.get("chart_data", ""), # <--- TAVO CHARTO LAUKAS
                "main_assets": "Investments, Real Estate, Salary"
            },
            "meta": {
                "_yoast_wpseo_title": data.get("seo_title", ""),
                "_yoast_wpseo_metadesc": data.get("seo_desc", ""),
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", "")
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} publikuotas! (Image ID: {img_id})")
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
