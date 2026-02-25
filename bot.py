import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Tier 1 High-Quality Edition) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Tikslus WEALTH pasirinkimų sąrašas
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

# Tier 1 stabilus URL (v1beta palaiko geresnį JSON formatavimą)
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

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

    # Griežtas promptas kokybei ir SEO
    prompt = (
        f"Write a professional, 1000-word financial biography for {politician_name} in 2026. \n"
        f"STYLE: Use H2/H3 tags, use **bolding** for key financial figures and milestones. "
        f"Compare their wealth to US average citizens. Tell an interesting story of their financial rise. \n"
        f"DATA: For net worth, use $XX,XXX,XXX format. History: '2019:X,2022:Y,2026:Z'. \n"
        f"SOURCES: Provide 2-3 REAL raw URLs (plain text). \n"
        f"LIMITS: Pick EXACTLY 2 categories from {list(CAT_MAP.keys())} and EXACTLY 2 wealth sources from {WEALTH_OPTIONS}. \n"
        f"Return ONLY valid JSON: {{"
        f"\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Role\", "
        f"\"history\": \"2019:X,2026:Y\", \"raw_urls\": [\"url1\", \"url2\"], "
        f"\"wealth_sources\": [], \"assets\": \"Specific assets\", "
        f"\"seo_title\": \"Title\", \"seo_desc\": \"Description\", \"cats\": []}}"
    )
    
    safety_settings = [
        {"category": cat, "threshold": "BLOCK_NONE"} 
        for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
    ]

    try:
        response = requests.post(GENERATE_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings,
            "generationConfig": {"temperature": 0.8} # Didesnis kūrybiškumas straipsniui
        })
        
        resp_json = response.json()
        if 'candidates' not in resp_json:
            print(f"  ❌ API Klaida: {resp_json}")
            return

        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        # Šaltinių sutvarkymas be redirectų į tavo puslapį
        sources_list = "".join([f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{url}</a></li>' for url in data.get("raw_urls", [])])
        clean_sources_html = f"<ul>{sources_list}</ul>" if sources_list else ""

        payload = {
            "title": data.get("seo_title", f"{politician_name} Net Worth 2026"),
            "content": data["article"],
            "status": "publish",
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
            "featured_media": img_id,
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
                # Tier 1 leidžia greičiau, bet 10s užtikrina stabilumą dėl WordPress limitų
                time.sleep(10)
