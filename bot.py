import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Stability & RankMath Fix) ---")

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
        f"Research {politician_name} for a net worth article. \n"
        f"1. WEALTH: Use financial disclosures. If data is old, calculate 2026 value with 8% annual growth. Be realistic. \n"
        f"2. SOURCES: Return 2-3 real URLs as HTML links. \n"
        f"3. SEO: Title and Meta Description for Rank Math. \n"
        f"Return ONLY valid JSON: {{"
        f"\"article\": \"HTML content\", \"net_worth\": \"$15M\", \"job_title\": \"Role\", "
        f"\"history\": \"2019:8M,2020:9M...\", \"sources_html\": \"HTML links\", "
        f"\"source_of_wealth\": [], \"key_assets\": \"Asset names\", "
        f"\"seo_title\": \"Title\", \"seo_desc\": \"Description\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        # Pridėti saugos nustatymai, kad API neblokuotų užklausos
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
        
        # Patikra ar 'candidates' egzistuoja
        if 'candidates' not in resp_json:
            print(f"  ❌ API Klaida (Nėra kandidatų): {resp_json.get('error', {}).get('message', 'Blokuota saugos filtrų')}")
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
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
        else:
            print(f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Kritinė klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(30)
