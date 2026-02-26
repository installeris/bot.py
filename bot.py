import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS: SMART NUMBERS & YEARLY HISTORY ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

MODEL_ID = "gemini-1.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19, "Politician Wealth": 22, "Congress Trades": 21}

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200&redirects=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def call_gemini_with_retry(prompt, retries=5):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    for i in range(retries):
        try:
            response = requests.post(GEMINI_URL, json=payload, timeout=90)
            if response.status_code == 200: return response.json()
            time.sleep(15)
        except: time.sleep(15)
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Analizuojame: {politician_name}")
    
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Nėra foto.")
        return

    img_id = None
    try:
        img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename=img.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        img_id = res.json()["id"] if res.status_code == 201 else None
    except: pass
    
    if not img_id:
        print(f"  ⏭️ PRALEIDŽIAMA: Media klaida.")
        return

    prompt = (
        f"Research and write an 850-word financial profile for {politician_name} for 2026. \n"
        f"1. TITLE: Use exactly '{politician_name} Net Worth 2026'. \n"
        f"2. JOB TITLE: Find their specific current office (e.g., U.S. Senator from State). \n"
        f"3. NET WORTH FORMAT: If >= $1M use '$X.X Million'. If < $1M use full number '$850,000'. \n"
        f"4. HISTORY: Provide ANNUAL net worth for 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, and 2026. \n"
        f"5. SOURCES: Use 3-4 real sources (OpenSecrets, FEC, Ballotpedia). \n"
        f"6. STYLE: SEO optimized, conversational but expert, include interesting investment facts. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$8.4 Million\", \"job\": \"U.S. Senator from Wisconsin\", "
        f"\"history\": \"2018:$2.1M,2019:$2.4M,2020:$3M,2021:$4.1M,2022:$5M,2023:$6.2M,2024:$7M,2025:$7.8M,2026:$8.4M\", "
        f"\"urls\": [{{ \"n\": \"OpenSecrets Profile\", \"u\": \"https://...\" }}], "
        f"\"wealth_src\": [\"Stock Market Investments\"], \"assets\": \"Top 2 major assets\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\"}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Šaltinių blokas su pavadinimais
            sources_html = "<strong>Financial Data Sources & Verification:</strong><ul>"
            for link in data.get("urls", []):
                name = link.get("n", "Source")
                url = link.get("u", "#")
                sources_html += f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{name}</a></li>'
            sources_html += "</ul>"

            wp_payload = {
                "title": f"{politician_name} Net Worth 2026",
                "content": data["article"] + sources_html,
                "status": "publish",
                "featured_media": img_id,
                "categories": [19, 22],
                "acf": {
                    "job_title": data.get("job", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""), # Pilna metinė istorija
                    "source_of_wealth": data.get("wealth_src", [])[:2], # Varnelės
                    "main_assets": data.get("assets", ""),
                    "sources": sources_html
                },
                "rank_math_title": data.get("seo_t", ""),
                "rank_math_description": data.get("seo_d", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }
            
            requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS))
            print(f"  ✅ SĖKMĖ: {politician_name} ({data.get('net_worth')})")
        except Exception as e:
            print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(15)
