import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 💎 PROFESIONALUS FINANSŲ ANALITIKAS V5 (RankMath & Accuracy Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Nustatymai
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United Kingdom (UK)": 20, "United States (USA)": 19}

# Modelis (Tier 1 stabilumas)
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n🕵️ Tiriamas turtas: {politician_name}")
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        try:
            img_res = requests.get(wiki_img)
            headers = {"Content-Disposition": f"attachment; filename=img.jpg", "Content-Type": "image/jpeg"}
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            img_id = res.json()["id"]
        except: pass

    # GRIEŽTAS ANALITIKO PROMPTAS
    prompt = (
        f"Act as a professional financial investigator for 'Politician Net Worth'. \n"
        f"TOPIC: {politician_name} Net Worth 2026. \n\n"
        f"STRICT REQUIREMENTS: \n"
        f"1. RESEARCH: Look for data from OpenSecrets and official disclosures. Provide a realistic net worth based on their salary ($174k/year) and assets. \n"
        f"2. HISTORY: Provide 4-5 data points for the chart (e.g., '2018:Value, 2020:Value, 2022:Value, 2024:Value, 2026:Value'). Use real progression. \n"
        f"3. STYLE: Write 800 words. Be conversational but expert. Use 'Did you know?' facts. Avoid AI clichés. Use H2/H3 and **bold numbers**. \n"
        f"4. CATEGORIES: Choose EXACTLY 2 from {list(CAT_MAP.keys())}. \n"
        f"5. WEALTH: Choose EXACTLY 2 from {WEALTH_OPTIONS}. \n"
        f"6. ASSETS: Provide a short comma-separated list of 3 specific assets. \n"
        f"7. SEO: Create a click-worthy Rank Math Title and Description. \n\n"
        f"RETURN ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X.M\", \"job_title\": \"Official Title\", \"history\": \"2018:X,2026:Y\", \"sources_urls\": [\"URL1\", \"URL2\"], \"wealth_sources\": [], \"assets\": \"Asset1, Asset2\", \"seo_title\": \"RankMathTitle\", \"seo_desc\": \"RankMathDesc\", \"cats\": []}}"
    )

    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        # Šaltinių atvaizdavimas (Gražus sąrašas)
        sources_list = "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("sources_urls", [])])
        sources_html = f"<strong>Financial Data Sources:</strong><ul>{sources_list}</ul>"

        # WordPress Payload su Rank Math laukais
        payload = {
            "title": f"{politician_name} Net Worth 2026",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2],
                "main_assets": data.get("assets", ""),
                "sources": sources_html
            },
            # Rank Math integracija per API
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
                time.sleep(15) # Saugus tarpas Tier 1
