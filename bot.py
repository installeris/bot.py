import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (Gemini 2.0 Flash versija) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame naujausią 2.0 Flash modelį
MODEL_NAME = "gemini-2.0-flash-exp"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_KEY}"

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
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
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
    print(f"\n💎 Ruošiamas: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Griežtas promptas naujam modeliui
    prompt = (
        f"Act as a financial journalist. Research {politician_name} net worth for 2026. \n"
        f"1. WEALTH: Provide a realistic 2026 estimate. Use latest disclosures and add 8% annual growth if data is older than 2024. \n"
        f"2. SOURCES: Provide 2-3 REAL external URLs as clickable HTML links (e.g., OpenSecrets, Forbes). \n"
        f"3. SEO: Write a high-quality Meta Title and Meta Description for Rank Math. \n"
        f"4. DATA: Ensure 'net_worth_history' (chart) is in '2019:XXXX,2020:XXXX' format. \n"
        f"Return ONLY a clean JSON object: {{"
        f"\"article\": \"HTML content\", \"net_worth\": \"$10,500,000\", \"job_title\": \"Official Title\", "
        f"\"history\": \"2019:8000000,2020:8600000...\", \"sources_html\": \"Links\", "
        f"\"source_of_wealth\": [], \"key_assets\": \"1-2 key assets\", "
        f"\"seo_title\": \"SEO Title\", \"seo_desc\": \"Description\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    try:
        # Gemini 2.0 palaiko BLOCK_NONE saugumo nustatymus
        safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in [
            "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
            "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
        ]]
        
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings
        })
        
        resp_json = response.json()
        
        if 'candidates' in resp_json:
            ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
            # Išvalome JSON, jei AI pridėjo ```json žymes
            clean_json = re.search(r'\{.*\}', ai_text, re.DOTALL).group()
            data = json.loads(clean_json)
            
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
                print(f"  ✅ SĖKMĖ: {politician_name} publikuotas naudojant Gemini 2.0!")
            else:
                print(f"  ❌ WP Klaida: {res.text}")
        else:
            print(f"  ❌ API Klaida: {resp_json}")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Pauzė 75 sek. (Ruošiamas {i+1}/{len(names)})")
                time.sleep(75)
