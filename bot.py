import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🛠️ BOTAS STARTUOJA (Universal Model Detection) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Kategorijų žemėlapis
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

def get_best_model_url():
    """Automatiškai randa veikiantį Gemini modelio URL."""
    # Bandome v1beta ir v1 versijas
    versions = ["v1beta", "v1"]
    # Modeliai, kurių ieškome (prioriteto tvarka)
    targets = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash-exp"]
    
    for ver in versions:
        list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={GEMINI_KEY}"
        try:
            res = requests.get(list_url).json()
            if 'models' in res:
                available = [m['name'] for m in res['models'] if 'generateContent' in m.get('supportedGenerationMethods', [])]
                for target in targets:
                    for full_name in available:
                        if target in full_name:
                            print(f"✅ RASTAS MODELIS: {full_name} ({ver})")
                            return f"https://generativelanguage.googleapis.com/{ver}/{full_name}:generateContent?key={GEMINI_KEY}"
        except:
            continue
    return None

GENERATE_URL = get_best_model_url()

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000"
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
    if not GENERATE_URL:
        print("🚨 KLAIDA: Nepavyko rasti jokio veikiančio Gemini modelio tavo paskyroje!")
        return

    print(f"\n🚀 Ruošiamas pilnas straipsnis: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Maksimalios kokybės promptas
    prompt = (
        f"Write a 1000-word financial analysis of {politician_name} for 2026. \n"
        f"Use HTML (H2, H3 tags). Be detailed about career and specific assets. \n"
        f"Net worth must be a precise full number (e.g. $12,500,000). \n"
        f"Include 2-3 REAL source links using <a href='...'> tags. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Title\", \"history\": \"2020:X,2026:Y\", \"sources_html\": \"Sources\", \"source_of_wealth\": [], \"key_assets\": \"Assets\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"United States (USA)\"]}}"
    )

    try:
        response = requests.post(GENERATE_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8},
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        })
        
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS],
                "main_assets": data.get("key_assets", ""),
                "sources": data.get("sources_html", "")
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", "")
        }

        wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!" if wp_res.status_code == 201 else f"  ❌ WP Klaida: {wp_res.text}")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
