import os
import requests
import json
import re
import time
import sys

# Priverčiame logus rodytis realiu laiku
sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (v1.5 Flash + Stability Mode) ---")

# KONFIGŪRACIJA (Iš GitHub Secrets)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame stabilų modelį su dideliais nemokamais limitais
ACTIVE_MODEL = "models/gemini-1.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"

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

def get_wiki_image(name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers=headers).json()
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
    print(f"\n💎 Analizuojamas: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    prompt = (
        f"Research {politician_name} for a net worth article set in 2026. \n"
        f"1. WEALTH: 2026 estimate. If latest data is from 2018-2022, apply 8% annual growth. \n"
        f"2. SOURCES: 2-3 real URLs as clickable HTML links. \n"
        f"3. SEO: Focus-keyword Title and Meta Description for Rank Math. \n"
        f"Return ONLY valid JSON: {{"
        f"\"article\": \"HTML\", \"net_worth\": \"$15.5M\", \"job_title\": \"Role\", "
        f"\"history\": \"2019:8M,2020:9M...\", \"sources_html\": \"HTML links\", "
        f"\"source_of_wealth\": [], \"key_assets\": \"Assets\", "
        f"\"seo_title\": \"Title\", \"seo_desc\": \"Description\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    # RETRY LOGIKA (Bando iki 3 kartų, jei serveris užimtas arba limitas pasiektas)
    for attempt in range(3):
        try:
            response = requests.post(GEMINI_URL, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            })
            
            resp_json = response.json()

            if response.status_code == 429:
                wait_time = 120 * (attempt + 1)
                print(f"  ⚠️ Limitas (429). Bandymas {attempt+1}/3. Laukiame {wait_time}s...")
                time.sleep(wait_time)
                continue

            if 'candidates' not in resp_json:
                print(f"  ❌ API Klaida: {resp_json.get('error', {}).get('message', 'Unknown error')}")
                return

            ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

            # WP duomenų pildymas
            payload = {
                "title": f"{politician_name} Net Worth",
                "content": data["article"],
                "status": "publish",
                "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
                "featured_media": img_id,
                "acf": {
                    "job_title": data.get("job_title", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS],
                    "main_assets": data.get("key_assets", ""),
                    "sources": data.get("sources_html", "")
                },
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }

            res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            if res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} publikuotas!")
                return
            else:
                print(f"  ❌ WP Klaida: {res.text}")
                return

        except Exception as e:
            print(f"  🚨 Kritinė klaida: {e}")
            time.sleep(30)

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        
        print(f"📚 Surasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Saugi pauzė (75 sek.). {i}/{len(names)} pabaigta.")
                time.sleep(75)
