import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS: DEBUG MODE ON (Tammy & John Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "[https://politiciannetworth.com/wp-json](https://politiciannetworth.com/wp-json)"

MODEL_ID = "gemini-1.5-flash" 
GEMINI_URL = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19, "Politician Wealth": 22, "Congress Trades": 21}

def get_wiki_image(name):
    try:
        url = f"[https://en.wikipedia.org/w/api.php?action=query&titles=](https://en.wikipedia.org/w/api.php?action=query&titles=){name}&prop=pageimages&format=json&pithumbsize=1200&redirects=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except Exception as e:
        print(f"  ⚠️ Wiki klaida: {e}")
        return None

def call_gemini_with_retry(prompt, retries=3):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    for i in range(retries):
        try:
            print(f"  🧠 AI bando generuoti (bandymas {i+1})...")
            response = requests.post(GEMINI_URL, json=payload, timeout=60)
            if response.status_code == 200: return response.json()
            print(f"  ⚠️ AI Status: {response.status_code}")
            time.sleep(5)
        except Exception as e:
            print(f"  ⚠️ AI Request klaida: {e}")
            time.sleep(5)
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Pradedame: {politician_name}")
    
    # 1. Foto paieška
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Foto nerasta Wikipedia.")
        return

    # 2. Foto kėlimas
    img_id = None
    try:
        print("  📸 Siunčiame foto į WordPress...")
        img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        headers = {"Content-Disposition": f"attachment; filename=img.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS), timeout=20)
        if res.status_code == 201:
            img_id = res.json()["id"]
            print(f"  📸 Foto OK (ID: {img_id})")
        else:
            print(f"  ⏭️ STOP: WP nepriėmė foto (Status: {res.status_code})")
            return
    except Exception as e:
        print(f"  ⏭️ STOP: Media kėlimo lūžis: {e}")
        return

    # 3. AI Generavimas
    prompt = (
        f"Detailed 850-word financial profile for {politician_name} (2026). \n"
        f"TITLE: {politician_name} Net Worth 2026. \n"
        f"FORMAT: If Net Worth >= $1M use '$X.X Million', if < $1M use '$850,000'. \n"
        f"HISTORY: Annual net worth from 2018 to 2026. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$8.4 Million\", \"job\": \"U.S. Senator\", "
        f"\"history\": \"2018:$2M,2019:$2.5M,2020:$3M,2021:$4M,2022:$5M,2023:$6M,2024:$7M,2025:$7.8M,2026:$8.4M\", "
        f"\"urls\": [{{ \"n\": \"OpenSecrets\", \"u\": \"https://...\" }}], "
        f"\"wealth_src\": [\"Stock Market Investments\"], \"assets\": \"Top 2 Assets\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\"}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            # Išvalome AI šiukšles (```json ... ```)
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            sources_html = "<strong>Financial Data Sources:</strong><ul>"
            for link in data.get("urls", []):
                sources_html += f'<li><a href="{link.get("u")}" target="_blank">{link.get("n")}</a></li>'
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
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("wealth_src", [])[:2],
                    "main_assets": data.get("assets", ""),
                    "sources": sources_html
                },
                "rank_math_title": data.get("seo_t", ""),
                "rank_math_description": data.get("seo_d", "")
            }
            
            final_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS), timeout=30)
            if final_res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
            else:
                print(f"  ❌ WP Klaida: {final_res.text}")
        except Exception as e:
            print(f"  🚨 JSON/WP Klaida: {e}")
    else:
        print("  ❌ Nepavyko gauti atsakymo iš AI.")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(10)
