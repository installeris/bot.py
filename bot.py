import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🛠️ BOTAS STARTUOJA (Universal Model Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Išbandome du galimus modelio variantus
MODEL_VARIANTS = ["gemini-1.5-flash", "gemini-1.5-flash-latest"]

def get_gemini_response(prompt):
    for model_id in MODEL_VARIANTS:
        # Svarbu: v1beta endpoint'as kartais reikalauja /models/ prieš pavadinimą
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_KEY}"
        try:
            response = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            })
            res_data = response.json()
            if 'candidates' in res_data:
                print(f"✅ Sėkmingai panaudotas modelis: {model_id}")
                return res_data
            else:
                print(f"⚠️ Modelis {model_id} netiko, bandomas kitas...")
        except:
            continue
    return None

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties", "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "European Parliament": 18, "United States (USA)": 19, "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23}

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    prompt = (
        f"Research {politician_name} net worth for 2026. \n"
        f"1. WEALTH: 2026 estimate (8% growth logic). \n"
        f"2. SOURCES: 2-3 real clickable HTML links. \n"
        f"3. SEO: Title and Description for Rank Math. \n"
        f"Return ONLY valid JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Role\", \"history\": \"2019:X...\", \"sources_html\": \"Links\", \"source_of_wealth\": [], \"key_assets\": \"Assets\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )
    
    resp_json = get_gemini_response(prompt)
    
    if not resp_json:
        print(f"🚨 Klaida: Nepavyko rasti tinkančio modelio arba viršyti limitai.")
        return

    try:
        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())
        
        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS],
                "main_assets": data.get("key_assets", ""),
                "sources": data.get("sources_html", "")
            },
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!" if res.status_code == 201 else f"  ❌ WP Klaida: {res.text}")

    except Exception as e:
        print(f"  🚨 Klaida apdorojant duomenis: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            time.sleep(75)
