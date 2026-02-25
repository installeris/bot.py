import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (Tier 1 Verified) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Kategorijos ir Turtas
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

# TIER 1 STABILUS URL (v1 versija)
# Svarbu: models/gemini-1.5-flash
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

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
    print(f"\n💎 Ruošiamas straipsnis: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    # Maksimalios kokybės promptas
    prompt = (
        f"Write a 1000-word financial biography for {politician_name} for 2026. \n"
        f"1. CONTENT: Use H2/H3 tags. Use **bolding** for important facts. Tell an interesting story about their rise to wealth, compare their money to average citizens. Use engaging, professional language. \n"
        f"2. NET WORTH: Precise full figure (e.g. $14,200,000). \n"
        f"3. HISTORY: Format: '2018:Value,2020:Value,2023:Value,2026:Value'. \n"
        f"4. SOURCES: 2-3 REAL raw URLs (no HTML). \n"
        f"5. JSON: article (HTML), net_worth (string), job_title, history, raw_sources (array), wealth_sources (array), assets, seo_title, seo_desc, cats (array)."
    )

    try:
        # Priverstinis JSON formatas
        response = requests.post(GENERATE_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8}
        })
        
        raw_res = response.json()
        if 'candidates' not in raw_res:
            print(f"  ❌ API Klaida: {raw_res}")
            return

        data = json.loads(raw_res['candidates'][0]['content']['parts'][0]['text'])

        # Šaltinių sutvarkymas be tavo puslapio redirectų
        sources_list = "".join([f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{url}</a></li>' for url in data.get("raw_sources", [])])
        clean_sources_html = f"<ul>{sources_list}</ul>" if sources_list else ""

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
                "source_of_wealth": [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2],
                "main_assets": data.get("assets", ""),
                "sources": clean_sources_html
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                # Tier 1 leidžia greitai - užtenka 3 sekundžių
                time.sleep(3)
