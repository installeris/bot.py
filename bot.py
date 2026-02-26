import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA: STABILUS IR SEO OPTIMIZUOTAS ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame tavo patikrintą modelį
MODEL_ID = "gemini-2.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {
    "US Senate": 1, 
    "US House of Representatives": 2, 
    "Executive Branch": 3, 
    "State Governors": 4, 
    "United States (USA)": 19,
    "Politician Wealth": 22,
    "Congress Trades": 21
}

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
            response = requests.post(GEMINI_URL, json=payload, timeout=60)
            if response.status_code == 200: return response.json()
            time.sleep(10)
        except: time.sleep(10)
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Analizuojamas: {politician_name}")
    
    # 1. Foto patikra (Nėra foto - nėra posto)
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Foto nerasta.")
        return

    img_id = None
    try:
        img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        img_id = res.json()["id"] if res.status_code == 201 else None
    except: pass
    
    if not img_id:
        print(f"  ⏭️ PRALEIDŽIAMA: Media klaida.")
        return

    # 2. PROMPTAS (Milijonai, Varnelės, Įdomūs Faktai)
    prompt = (
        f"Create an 850-word financial dossier for {politician_name} (2026 update). \n"
        f"STYLE: Engaging, journalistic, and easy to scan. Use H2/H3 and **bold figures**. \n"
        f"SECTIONS: Include a 'Financial Milestones' section with rare facts and a precise net worth history (2018-2026). \n"
        f"NET WORTH: Must be in Millions (e.g., $12.5M). NEVER use values below $100,000 for politicians. \n"
        f"ASSETS: Identify max 2 specific major asset classes. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$8.4M\", \"job\": \"Official\", "
        f"\"history\": \"2018:$3M,2022:$6M,2026:$8.4M\", \"urls\": [\"URL1\"], "
        f"\"wealth_src\": [\"Stock Market Investments\", \"Real Estate Holdings\"], "
        f"\"assets\": \"Stock Portfolio, Residential Real Estate\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\", \"cats\": [\"United States (USA)\", \"Politician Wealth\"]}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Šaltinių dizainas
            sources_html = "<strong>Financial Data Sources:</strong><ul>"
            for u in data.get("urls", []):
                sources_html += f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>'
            sources_html += "</ul>"

            # 3. WordPress Payload
            payload = {
                "title": f"{politician_name} Net Worth 2026: Analysis & Assets",
                "content": data["article"] + sources_html,
                "status": "publish",
                "featured_media": img_id,
                "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
                "acf": {
                    "job_title": data.get("job", ""),
                    "net_worth": data.get("net_worth", ""), # Dabar tikrai rodys Milijonus
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("wealth_src", [])[:2], # Čia užsipildo Checkboxai
                    "main_assets": data.get("assets", ""), # Tik 1-2 pagrindiniai
                    "sources": sources_html
                },
                "rank_math_title": data.get("seo_t", ""),
                "rank_math_description": data.get("seo_d", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }
            
            wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            if wp_res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} (Net Worth: {data.get('net_worth')})")
            else:
                print(f"  ❌ WP KLAIDA: {wp_res.text}")
        except Exception as e:
            print(f"  🚨 KLAIDA: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(15)
