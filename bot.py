import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (Original Base + Your Fixes) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame tavo nurodytą modelį
MODEL_ID = "gemini-2.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
# Sutvarkytas kategorijų žemėlapis pagal tavo nurodymus
CAT_MAP = {
    "US Senate": 1, 
    "US House of Representatives": 2, 
    "Executive Branch": 3, 
    "State Governors": 4, 
    "United States (USA)": 19,
    "Politician Wealth": 22, # Tavo kategorija
    "Congress Trades": 21     # Tavo kategorija
}

def get_wiki_image(name):
    try:
        # Pridėtas redirects=1, kad tikrai rastų Tammy Baldwin ir kt.
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
            response = requests.post(GEMINI_URL, json=payload, timeout=60)
            if response.status_code == 200: return response.json()
            time.sleep(10)
        except: time.sleep(10)
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    # GRIEŽTA TAISYKLĖ: Nėra foto - nėra posto
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Nuotrauka nerasta.")
        return

    img_id = None
    try:
        img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        img_id = res.json()["id"] if res.status_code == 201 else None
    except: pass
    
    if not img_id:
        print(f"  ⏭️ PRALEIDŽIAMA: Nepavyko įkelti nuotraukos į WP.")
        return

    # Tavo prašytas PROMPTAS: 700-900 žodžių, tikra info, be AI stiliaus
    prompt = (
        f"Write a 800-word informative financial article about {politician_name} for 2026. \n"
        f"INSTRUCTIONS: Use verified data from OpenSecrets and Ballotpedia. Avoid AI-sounding phrases. \n"
        f"CHART DATA: Provide a realistic net worth progression (e.g., 2019, 2021, 2023, 2025, 2026). \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X.M\", \"job_title\": \"Official Role\", "
        f"\"history\": \"2019:Value,2022:Value,2026:Value\", \"urls\": [\"URL1\", \"URL2\"], "
        f"\"wealth_sources\": [], \"assets\": \"Specific Assets\", \"seo_title\": \"SEO Title\", "
        f"\"seo_desc\": \"SEO Description\", \"cats\": [\"United States (USA)\", \"Politician Wealth\"]}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Gražus šaltinių atvaizdavimas pagal tavo prašymą
            sources_html = "<strong>Financial Data Sources:</strong><ul>"
            for u in data.get("urls", []):
                sources_html += f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>'
            sources_html += "</ul>"

            payload = {
                "title": f"{politician_name} Net Worth 2026: Portfolio & Trades",
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
                    "sources": sources_html # Gražiai suformuotas sąrašas
                },
                # Rank Math laukai dabar užpildyti!
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }
            
            wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            if wp_res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
            else:
                print(f"  ❌ WP Klaida: {wp_res.text}")
        except Exception as e:
            print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(10)
