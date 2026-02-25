import os
import requests
from google import genai
import json
import re
import time

# 1. KONFIGŪRACIJA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naujas klientas pagal naują biblioteką
client = genai.Client(api_key=GEMINI_KEY)

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

def get_wiki_image(name):
    print(f"  🖼️ Ieškoma nuotrauka Wikipedia: {name}")
    try:
        params = {
            "action": "query", "titles": name, "prop": "pageimages",
            "format": "json", "pithumbsize": 1000
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
    try:
        img_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            return res.json()["id"]
    except Exception as e:
        print(f"  ⚠️ Nepavyko įkelti nuotraukos: {e}")
    return None

def run_wealth_bot(politician_name):
    print(f"\n--- Pradedamas darbas su: {politician_name} ---")
    
    img_url = get_wiki_image(politician_name)
    img_id = upload_to_wp(img_url, politician_name) if img_url else None
    if img_id: print(f"  ✅ Nuotrauka paruošta (ID: {img_id})")

    prompt = f"""Research {politician_name}. Write 600-word SEO article in English (H2, H3, HTML). 
    Focus on net worth. Return ONLY JSON with keys: article, net_worth, job_title, main_assets, 
    wealth_sources, history, seo_title, seo_desc, cats."""
    
    try:
        # Naujas iškvietimo būdas
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        text = response.text
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            print("  ❌ AI nesugeneravo JSON")
            return
            
        data = json.loads(json_match.group())
        target_cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP] or [23]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": target_cats,
            "featured_media": img_id,
            "acf": {
                "job_title": data["job_title"],
                "net_worth": data["net_worth"],
                "source_of_wealth": data["wealth_sources"],
                "main_assets": data["main_assets"],
                "net_worth_history": data["history"],
                "sources": "https://en.wikipedia.org"
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"  ✨ SĖKMĖ: {politician_name} publikuotas!")
        else:
            print(f"  ❌ WP klaida: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"  🚨 Klaida generuojant turinį: {e}")

if __name__ == "__main__":
    print("🤖 Botas aktyvuotas...")
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [l.strip() for l in f if l.strip()]
        
        print(f"📚 Rasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"💤 Miegame 5 min. iki kito politiko ({i}/{len(names)})...")
                time.sleep(300)
    else:
        print("❌ Failas names.txt nerastas!")
