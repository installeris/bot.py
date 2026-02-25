import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- ⚡ TIER 1 BOTAS STARTUOJA ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Kategorijos ir Turtas
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

# Naudojame v1beta, kad būtų didžiausias suderinamumas su naujais modeliais
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

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
    print(f"\n🚀 Generuojama: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    prompt = (
        f"Write a high-quality 1000-word financial biography for {politician_name} (2026 update). \n"
        f"Structure: Use H2/H3 tags, use **bold text** for facts. Compare wealth to peers. \n"
        f"Return ONLY a JSON block with these keys: \n"
        f"article (HTML), net_worth (e.g. $15,200,000), job_title, history (e.g. 2020:10M,2026:15M), \n"
        f"raw_sources (array of 2 plain URLs), wealth_sources (array of 2 options from {WEALTH_OPTIONS}), \n"
        f"assets (text), seo_title, seo_desc, cats (array from {list(CAT_MAP.keys())})."
    )

    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = response.json()
        
        # Ištraukiame JSON iš teksto (tiksliausias būdas)
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', full_text, re.DOTALL)
        if not match:
            print("❌ Nepavyko rasti JSON atsakyme")
            return
            
        data = json.loads(match.group())

        # Šaltiniai be tavo svetainės redirectų
        sources_html = "".join([f'<li><a href="{url}" target="_blank" rel="nofollow">{url}</a></li>' for url in data.get("raw_sources", [])])
        
        payload = {
            "title": data.get("seo_title", f"{politician_name} Net Worth 2026"),
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": data.get("wealth_sources", [])[:2],
                "main_assets": data.get("assets", ""),
                "sources": f"<ul>{sources_html}</ul>" if sources_html else ""
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", "")
        }

        wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"✅ SĖKMĖ: {politician_name}")

    except Exception as e:
        print(f"🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(2) # Tier 1 yra labai greitas
