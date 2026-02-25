import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (SEO & ACF FIX) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Surandame veikiantį modelį
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

def get_wiki_image(name):
    try:
        # Pridedame User-Agent, kad Wikipedia neblokuotų
        headers = {'User-Agent': 'WealthBot/1.0 (contact@politiciannetworth.com)'}
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000"
        res = requests.get(url, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url)
        headers = {
            "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Dirbame su: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Griežtesnis instruktažas AI
    prompt = (
        f"Research current reliable data for {politician_name}. Write a 600-word SEO article about their net worth. "
        f"Format: Use <h2> and <h3>. \n"
        f"IMPORTANT: Net worth must be a realistic number (e.g., '$15 Million'). \n"
        f"Return ONLY JSON: {{"
        f"\"article\": \"HTML content here\", "
        f"\"net_worth\": \"Short string, e.g. $10 Million\", "
        f"\"job_title\": \"Current role\", "
        f"\"main_assets\": \"List assets\", "
        f"\"seo_title\": \"Focus keyword rich title\", "
        f"\"seo_desc\": \"160 char meta description\", "
        f"\"cats\": [\"United States (USA)\"]}}"
    )
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        # Paruošiame kategorijas
        target_cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP] or [23]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": target_cats,
            "featured_media": img_id,
            # ACF LAUKAI (Patikrink ar tavo WP laukų vardai sutampa!)
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "main_assets": data.get("main_assets", ""),
            },
            # SEO (Yoast SEO laukai)
            "meta": {
                "_yoast_wpseo_title": data.get("seo_title", ""),
                "_yoast_wpseo_metadesc": data.get("seo_desc", "")
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"  ✅ PUBLIKUOTA! (WP ID: {res.json()['id']})")
        else:
            print(f"  ❌ WP Klaida: {res.text}")
    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(20)
