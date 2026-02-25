import os
import requests
import google.generativeai as genai
import json
import re
import time

# 1. KONFIGŪRACIJA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
# Tavo svetainės pagrindinis adresas be galinio brūkšnio
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

def get_wiki_image(name):
    """Suranda oficialią Wikipedia nuotraukos nuorodą pagal vardą."""
    try:
        params = {
            "action": "query",
            "titles": name,
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": 1000  # Aukštos kokybės nuotrauka
        }
        res = requests.get("https://en.wikipedia.org/w/api.php", params=params).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                return pages[pg]["thumbnail"]["source"]
    except:
        return None
    return None

def upload_to_wp(image_url, politician_name):
    """Atsisiunčia nuotrauką iš Wiki ir įkelia į WordPress."""
    try:
        img_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/media",
            data=img_data,
            headers=headers,
            auth=(WP_USER, WP_PASS)
        )
        if res.status_code == 201:
            return res.json()["id"] # Grąžina nuotraukos ID
    except Exception as e:
        print(f"🖼️ Nuotraukos klaida: {e}")
    return None

def run_wealth_bot(politician_name):
    print(f"🚀 Procesas: {politician_name}...")
    
    # 1. Surandame nuotrauką
    image_url = get_wiki_image(politician_name)
    featured_image_id = None
    if image_url:
        print(f"📸 Rasta nuotrauka: {image_url}")
        featured_image_id = upload_to_wp(image_url, politician_name)

    # 2. Generuojame straipsnį
    prompt = f"Research {politician_name}. Write 600-word SEO article in English (H2, H3, HTML). Return JSON with keys: article, net_worth, job_title, main_assets, wealth_sources, history, seo_title, seo_desc, cats."
    
    try:
        response = model.generate_content(prompt)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not json_match: return
        data = json.loads(json_match.group())

        target_cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]
        if not target_cats: target_cats = [23]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": target_cats,
            "featured_media": featured_image_id, # Čia susiejame nuotrauką!
            "acf": {
                "job_title": data["job_title"],
                "net_worth": data["net_worth"],
                "source_of_wealth": data["wealth_sources"],
                "main_assets": data["main_assets"],
                "net_worth_history": data["history"],
                "sources": "https://en.wikipedia.org"
            },
            "rank_math_title": data["seo_title"],
            "rank_math_description": data["seo_desc"]
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"✅ PUBLIKUOTA: {politician_name}")
        else:
            print(f"❌ WP Klaida: {res.status_code}")
            
    except Exception as e:
        print(f"🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [line.strip() for line in f if line.strip()]
        
        for index, name in enumerate(names, 1):
            run_wealth_bot(name)
            if index < len(names):
                print(f"⏳ ({index}/{len(names)}) Laukiame 5 min...")
                time.sleep(300)
