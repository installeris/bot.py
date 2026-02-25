import os
import requests
import json
import re
import time
import sys

# Priverčiame tekstą pasirodyti GitHub lange iškart
sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Direct API v1) ---")

# 1. KONFIGŪRACIJA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Gemini API adresas (naudojame STABILIĄ v1 versiją)
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

if not all([GEMINI_KEY, WP_USER, WP_PASS]):
    print("🚨 KLAIDA: Trūksta GitHub Secrets!")
    sys.exit(1)

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

def get_wiki_image(name):
    try:
        params = {"action": "query", "titles": name, "prop": "pageimages", "format": "json", "pithumbsize": 1000}
        res = requests.get("https://en.wikipedia.org/w/api.php", params=params).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None
    return None

def upload_to_wp(image_url, politician_name):
    try:
        img_data = requests.get(image_url).content
        headers = {
            "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, WP_PASS))
        if res.status_code == 201: return res.json()["id"]
    except: return None
    return None

def ask_gemini(prompt):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(GEMINI_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        raise Exception(f"Gemini API klaida: {response.status_code} - {response.text}")

def run_wealth_bot(politician_name):
    print(f"\n💎 Dirbame su: {politician_name}")
    
    img_url = get_wiki_image(politician_name)
    img_id = upload_to_wp(img_url, politician_name) if img_url else None

    prompt = (
        f"Research {politician_name}. Write a 600-word SEO article in English about their net worth. "
        f"Return ONLY a valid JSON object: "
        f"{{\"article\": \"...\", \"net_worth\": \"...\", \"job_title\": \"...\", \"main_assets\": \"...\", \"wealth_sources\": [], \"history\": \"...\", \"seo_title\": \"...\", \"seo_desc\": \"...\", \"cats\": []}}"
    )
    
    try:
        print("  🧠 AI generuoja tekstą (Direct v1)...")
        ai_response = ask_gemini(prompt)
        
        clean_text = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if not clean_text:
            print("  ❌ Klaida: AI nepateikė JSON.")
            return
            
        data = json.loads(clean_text.group())
        target_cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP] or [23]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": target_cats,
            "featured_media": img_id,
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "source_of_wealth": str(data.get("wealth_sources", "")),
                "main_assets": data.get("main_assets", ""),
                "net_worth_history": data.get("history", "")
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
        else:
            print(f"  ❌ WP Klaida {res.status_code}: {res.text}")
            
    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [l.strip() for l in f if l.strip()]
        
        print(f"📚 Rasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Miegame 30 sek. (testas)... ")
                time.sleep(30) # Sutrumpinau testui
    else:
        print("🚨 KLAIDA: names.txt nerastas!")
