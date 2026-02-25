import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 PROFESIONALAUS TURINIO BOTAS V4 (Fixing URL & Quality) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Kategorijos ir Turtas
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]

def get_gemini_url():
    # Pirmiausia bandome standartinį mokamą URL (v1 versija dažniausiai stabiliausia Paid Tier)
    standard_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        test = requests.post(standard_url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=5)
        if test.status_code == 200:
            print("✅ Naudojamas stabilus v1 API")
            return standard_url
    except: pass
    
    # Jei standartinis neveikia, bandom v1beta
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

GENERATE_URL = get_gemini_url()

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

    # GRIEŽTAS PROMPTAS KOKYBEI
    prompt = (
        f"Act as a high-end financial journalist. Write a detailed 1000-word SEO article about {politician_name} net worth in 2026. \n"
        f"1. STYLE: Use H2/H3 headings. Use **bold** for emphasis. Tell a compelling story about their financial journey. Compare their wealth to US average or peers. Make it engaging. \n"
        f"2. SEO: Provide a catchy SEO Title and Meta Description. \n"
        f"3. NET WORTH: Exact figure (e.g., $18,200,000). \n"
        f"4. HISTORY: Must be '2018:Value,2020:Value,2023:Value,2026:Value'. \n"
        f"5. SOURCES: Provide 2-3 REAL source URLs (no HTML tags, just raw URLs). \n"
        f"6. CATEGORIES: Choose 2 from {list(CAT_MAP.keys())}. \n"
        f"7. WEALTH: Choose EXACTLY 2 from {WEALTH_OPTIONS}. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Title\", \"history\": \"2020:X,2026:Y\", \"raw_sources\": [\"url1\", \"url2\"], \"wealth_sources\": [\"X\", \"Y\"], \"assets\": \"Detailed list\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"X\", \"Y\"]}}"
    )

    try:
        response = requests.post(GENERATE_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8},
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        })
        
        raw_data = response.json()
        if 'candidates' not in raw_data:
            print(f"  ❌ API Klaida: {raw_data}")
            return

        data = json.loads(raw_data['candidates'][0]['content']['parts'][0]['text'])

        # Šaltinių sutvarkymas be redirectų
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
        print(f"  ✅ SĖKMĖ: {politician_name} įkeltas!")

    except Exception as e:
        print(f"  🚨 Klaida su {politician_name}: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
