import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Image, RankMath & Checkbox Fix) ---")

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
        # Naudojame oficialų Wikipedia API su User-Agent
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except Exception as e:
        print(f"  ⚠️ Nepavyko gauti nuotraukos iš Wiki: {e}")
    return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        # Atsisiunčiame nuotrauką į atmintį
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
        if img_res.status_code == 200:
            headers = {
                "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
                "Content-Type": "image/jpeg"
            }
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            if res.status_code == 201:
                return res.json()["id"]
    except Exception as e:
        print(f"  ⚠️ Klaida keliant nuotrauką į WP: {e}")
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    wiki_img = get_wiki_image(politician_name)
    img_id = upload_to_wp(wiki_img, politician_name)
    if img_id: print(f"  📸 Featured Image įkeltas (ID: {img_id})")

    prompt = (
        f"Research current financial data for {politician_name}. Write an 800-word SEO article. \n"
        f"1. Net worth: Must be a specific string like '$12 Million'. \n"
        f"2. Source of Wealth: List 1-3 categories (e.g., 'Politics', 'Real Estate', 'Investments'). \n"
        f"3. Key Assets: List 1-2 main assets. \n"
        f"4. Rank Math SEO: Provide a meta title and meta description. \n"
        f"Return ONLY JSON: {{"
        f"\"article\": \"HTML content\", \"net_worth\": \"$10 Million\", \"job_title\": \"Official Role\", "
        f"\"source_of_wealth\": [\"Politics\", \"Investments\"], \"key_assets\": \"Real Estate in DC\", "
        f"\"seo_title\": \"SEO Title\", \"seo_desc\": \"Meta Description\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        cat_ids = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]

        # WordPress užklausa
        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": cat_ids,
            "featured_media": img_id,
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "source_of_wealth": data.get("source_of_wealth", []), # Masyvas checkbox'ui
                "main_assets": data.get("key_assets", ""),
            },
            "meta": {
                # Rank Math laukai
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth",
                # Yoast (atsargai)
                "_yoast_wpseo_title": data.get("seo_title", ""),
                "_yoast_wpseo_metadesc": data.get("seo_desc", "")
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
