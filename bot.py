import os
import requests
import json
import re
import time
import sys

# Priverčiame logus rodytis GitHub Actions realiu laiku
sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Stabilizuota versija: 70s pauzė) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Tikslus Checkbox sąrašas tavo svetainei
WEALTH_OPTIONS = [
    "Stock Market Investments", "Real Estate Holdings", "Venture Capital", 
    "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties", 
    "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets"
]

# Kategorijų žemėlapis (ID iš tavo svetainės)
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
        f"1. WEALTH LOGIC: Use recent disclosures. If data is old (e.g. 2018), apply a ~7-10% annual growth rate to estimate the 2026 value. Ensure the value is realistic for 2026. \n"
        f"2. SOURCES: Find 2-3 real external URLs (OpenSecrets, Forbes, Official Disclosures) and return them as clickable HTML links. \n"
        f"3. SEO: Create a focus-keyword rich Title and Meta Description for Rank Math. \n"
        f"4. CATEGORIES: You must select 'United States (USA)' and the appropriate subcategory (e.g. 'US Senate'). \n"
        f"Return ONLY valid JSON: {{"
        f"\"article\": \"HTML\", \"net_worth\": \"$15,500,000\", \"job_title\": \"Role\", "
        f"\"history\": \"2019:8000000,2020:8800000...\", \"sources_html\": \"HTML links\", "
        f"\"source_of_wealth\": [], \"key_assets\": \"1-2 main assets\", "
        f"\"seo_title\": \"Title\", \"seo_desc\": \"Description\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        # Saugos nustatymai, kad API neblokuotų užklausų apie turtą
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings
        })
        
        resp_json = response.json()
        
        if 'candidates' not in resp_json:
            print(f"  ❌ API Klaida: {resp_json.get('error', {}).get('message', 'Blocked or Quota Exceeded')}")
            return

        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
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
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": valid_sources,
                "main_assets": data.get("key_assets", ""),
                "sources": data.get("sources_html", "")
            },
            # Rank Math API Manager palaikymas
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} publikuotas!")
        else:
            print(f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Klaida vykdant užduotį: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        
        print(f"📚 Iš viso rasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Laukiama 70 sek. (Saugome Gemini kvotą {i}/{len(names)})...")
                time.sleep(70)
    else:
        print("🚨 Klaida: names.txt nerastas!")
