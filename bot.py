import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 💎 GALUTINIS FINANSINIS ANALITIKAS (V6 - RankMath Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

def run_wealth_bot(name):
    print(f"\n🕵️ Ruošiamas straipsnis: {name}")
    
    # GRIEŽTA INSTRUKCIJA: Emuliuojame finansinį žurnalistą, kad apeitume filtrus
    prompt = (
        f"Write a 800-word financial analysis for a database entry about {name} in 2026. \n"
        f"1. STRUCTURE: Use H2/H3 tags, **bold** key figures. Use a friendly, professional tone for common readers. \n"
        f"2. DATA: Include a net worth growth chart (2018, 2020, 2022, 2024, 2026) using realistic market growth data. \n"
        f"3. SEO: Provide Rank Math Title and Description. \n"
        f"4. SOURCES: List 2-3 real educational URLs like ballotpedia.org or opensecrets.org. \n"
        f"5. LIMITS: Exactly 2 categories from {list(CAT_MAP.keys())} and exactly 2 sources from {WEALTH_OPTIONS}. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X.M\", \"job\": \"Role\", \"history\": \"2018:X,2022:Y,2026:Z\", \"urls\": [\"URL1\", \"URL2\"], \"wealth_src\": [], \"assets\": \"Asset1, Asset2\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\", \"cats\": []}}"
    )

    # IŠJUNGIAME FILTRUS (BŪTINA TIER 1)
    safety_settings = [
        {"category": c, "threshold": "BLOCK_NONE"} 
        for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
    ]

    try:
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings,
            "generationConfig": {"response_mime_type": "application/json"} # Priverstinis JSON režimas
        })
        
        res_json = response.json()
        if 'candidates' not in res_json:
            print(f"  ❌ API vis dar blokuoja {name}. Priežastis: {res_json.get('promptFeedback', 'Saugumas')}")
            return

        ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(ai_text)

        # Gražus šaltinių atvaizdavimas
        sources_html = "<strong>Financial Data Sources:</strong><ul>" + "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])]) + "</ul>"

        payload = {
            "title": f"{name} Net Worth 2026: Career & Financial Profile",
            "content": data["article"],
            "status": "publish",
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2],
            "acf": {
                "job_title": data.get("job", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("wealth_src", []) if s in WEALTH_OPTIONS][:2],
                "main_assets": data.get("assets", ""),
                "sources": sources_html
            },
            # Rank Math užpildymas
            "rank_math_title": data.get("seo_t", ""),
            "rank_math_description": data.get("seo_d", ""),
            "rank_math_focus_keyword": f"{name} net worth"
        }

        wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        if wp_res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {name} paskelbtas su Rank Math duomenimis!")
        else:
            print(f"  ❌ WP Klaida: {wp_res.text}")

    except Exception as e:
        print(f"  🚨 Kritinė klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(10)
