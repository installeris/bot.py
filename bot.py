import os
import requests
import json
import re
import time
import sys

# Priverčiame tekstą GitHub lange pasirodyti akimirksniu
sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Galutinė versija: Checkbox & SEO Fix) ---")

# 1. KONFIGŪRACIJA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Tikslus Checkbox sąrašas iš tavo ACF nustatymų
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

# --- API MODELIO PAIEŠKA ---
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
if not ACTIVE_MODEL:
    print("🚨 KLAIDA: Nepavyko rasti Gemini modelio. Patikrink API raktą.")
    sys.exit(1)

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"

# --- PAGALBINĖS FUNKCIJOS ---
def get_wiki_image(name):
    try:
        headers = {'User-Agent': 'WealthBot/1.0 (contact@politiciannetworth.com)'}
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None
    return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, stream=True, timeout=10)
        if img_res.status_code == 200:
            headers = {
                "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
                "Content-Type": "image/jpeg"
            }
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            if res.status_code == 201:
                return res.json()["id"]
    except Exception as e:
        print(f"  ⚠️ Klaida keliant nuotrauką: {e}")
    return None

# --- PAGRINDINĖ BOT LOGIKA ---
def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    # 1. Nuotrauka
    wiki_img = get_wiki_image(politician_name)
    img_id = upload_to_wp(wiki_img, politician_name)
    if img_id: print(f"  📸 Nuotrauka įkelta (ID: {img_id})")

    # 2. AI turinio generavimas
    prompt = (
        f"Research {politician_name}. Write an 800-word professional article in English about their net worth. \n"
        f"1. Net worth: Must be a realistic estimate (e.g. '$15.5 Million'). \n"
        f"2. Source of Wealth: You MUST pick 1-3 items ONLY from this list: {WEALTH_OPTIONS}. \n"
        f"3. Return ONLY JSON: {{"
        f"\"article\": \"HTML content with H2, H3 tags\", "
        f"\"net_worth\": \"Short value\", \"job_title\": \"Current role\", "
        f"\"source_of_wealth\": [], \"key_assets\": \"1-2 main assets\", "
        f"\"seo_title\": \"SEO optimized title\", \"seo_desc\": \"Meta description\", "
        f"\"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        # JSON išvalymas
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if not match:
            print("  ❌ Klaida: AI nepateikė JSON.")
            return
        data = json.loads(match.group())

        # Validuojame Source of Wealth (tik tai, ką WP priima)
        valid_sources = [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS]
        if not valid_sources: valid_sources = ["Stock Market Investments"]

        # Kategorijų ID
        cat_ids = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]
        if not cat_ids: cat_ids = [23]

        # 3. Siuntimas į WordPress
        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": cat_ids,
            "featured_media": img_id,
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
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
            print(f"  ✅ SĖKMĖ: {politician_name} sėkmingai publikuotas!")
        else:
            print(f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Klaida vykdant užduotį: {e}")

# --- PALEIDIMAS ---
if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        
        print(f"📚 Rasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Miegame 30 sek...")
                time.sleep(30)
    else:
        print("🚨 KLAIDA: names.txt failas nerastas!")
