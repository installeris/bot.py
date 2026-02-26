import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (Vardų ir RankMath Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame stabilų 2026 m. Tier 1 kelią
MODEL_ID = "gemini-1.5-flash" # Arba gemini-2.5-flash, jei tavo regione jau aktyvus
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def call_gemini_with_retry(prompt, retries=5):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"} 
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]
    }
    for i in range(retries):
        response = requests.post(GEMINI_URL, json=payload)
        if response.status_code == 200: return response.json()
        time.sleep(10)
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        try:
            img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
            headers = {"Content-Disposition": f"attachment; filename=img.jpg", "Content-Type": "image/jpeg"}
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            img_id = res.json()["id"] if res.status_code == 201 else None
        except: pass

    # Patobulintas tavo promptas (kad Rank Math nebūtų tuščias)
    prompt = (
        f"Write a professional 850-word financial article on {politician_name} net worth in 2026. \n"
        f"FACTS: Use realistic net worth history (e.g. 2018: $1M, 2022: $1.1M, 2026: $1.2M). \n"
        f"SOURCES: Provide 3 real URLs from OpenSecrets, Ballotpedia, or FEC. \n"
        f"STYLE: Engaging, expert tone. Use H2/H3 and **bold numbers**. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$1.2M\", \"job_title\": \"Senator\", "
        f"\"history\": \"2018:1M,2022:1.1M,2026:1.2M\", \"urls\": [\"URL1\", \"URL2\"], "
        f"\"wealth_sources\": [\"Stock Market Investments\"], \"assets\": \"Real estate, Mutual funds\", "
        f"\"seo_title\": \"{politician_name} Net Worth 2026: Financial Portfolio\", "
        f"\"seo_desc\": \"Explore the detailed financial portfolio and net worth growth of {politician_name} in 2026.\"}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Tavo prašytas "GRIŽTAS" šaltinių atvaizdavimas
            sources_html = "<strong>Financial Data Sources:</strong><ul>" + "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])]) + "</ul>"

            payload = {
                "title": f"{politician_name} Net Worth 2026",
                "content": data["article"],
                "status": "publish",
                "featured_media": img_id,
                "categories": [19, 1], # United States + Senate (pavyzdys)
                "acf": {
                    "job_title": data.get("job_title", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("wealth_sources", [])[:2],
                    "main_assets": data.get("assets", ""),
                    "sources": sources_html
                },
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", "")
            }
            requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            print(f"  ✅ SĖKMĖ: {politician_name}")
        except Exception as e:
            print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    with open("names.txt", "r") as f:
        for name in [n.strip() for n in f if n.strip()]:
            run_wealth_bot(name)
            time.sleep(10)
