import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 PROFESIONALAUS TURINIO BOTAS V3 ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
# Tavo leidžiami variantai
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

def get_best_model_url():
    versions = ["v1beta", "v1"]
    targets = ["gemini-1.5-flash", "gemini-1.5-flash-latest"]
    for ver in versions:
        url = f"https://generativelanguage.googleapis.com/{ver}/models?key={GEMINI_KEY}"
        try:
            res = requests.get(url).json()
            if 'models' in res:
                available = [m['name'] for m in res['models'] if 'generateContent' in m.get('supportedGenerationMethods', [])]
                for target in targets:
                    for full_name in available:
                        if target in full_name:
                            return f"https://generativelanguage.googleapis.com/{ver}/{full_name}:generateContent?key={GEMINI_KEY}"
        except: continue
    return None

GENERATE_URL = get_best_model_url()

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

    prompt = (
        f"Act as a professional financial journalist. Write a captivating 1000-word SEO article about {politician_name} net worth in 2026. \n"
        f"1. CONTENT: Use H2/H3 tags. Include bold text for key facts. Tell an interesting story about their rise to wealth, compare their wealth to average citizens or peers. Use engaging language. \n"
        f"2. NET WORTH: Precise figure (e.g., $12,450,000). \n"
        f"3. HISTORY: Essential for charts! Return string: '2018:Value,2020:Value,2022:Value,2026:Value'. \n"
        f"4. SOURCES: Provide 2-3 REAL external URLs (plain text). \n"
        f"5. LIMITS: Pick EXACTLY 2 categories from {list(CAT_MAP.keys())} and EXACTLY 2 wealth sources from {WEALTH_OPTIONS}. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Title\", \"history\": \"2018:X,2026:Y\", \"source_urls\": [\"url1\", \"url2\"], \"wealth_sources\": [], \"assets\": \"Text\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\"}}"
    )

    try:
        response = requests.post(GENERATE_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.85},
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        })
        
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        # Sutvarkome šaltinių HTML, kad nebūtų redirectų
        sources_list = "".join([f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{url}</a></li>' for url in data.get("source_urls", [])])
        sources_html = f"<ul>{sources_list}</ul>" if sources_list else ""

        payload = {
            "title": f"{politician_name} Net Worth 2026: Career & Wealth Analysis",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP] if "cats" in data else [19],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2],
                "main_assets": data.get("assets", ""),
                "sources": sources_html
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
