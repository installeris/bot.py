import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (70s pauzė + Retry logika) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties", "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "European Parliament": 18, "United States (USA)": 19, "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23}

def get_working_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        for m in models:
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except: return None

ACTIVE_MODEL = get_working_model()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"

def run_wealth_bot(politician_name):
    print(f"\n💎 Analizuojamas: {politician_name}")
    
    prompt = (
        f"Research {politician_name} for a net worth article set in 2026. \n"
        f"1. WEALTH: 2026 estimate (8% growth if data is old). \n"
        f"2. SOURCES: 2-3 HTML links. \n"
        f"3. SEO: Title/Desc for Rank Math. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X\", \"job_title\": \"Role\", \"history\": \"2019:X...\", \"sources_html\": \"Links\", \"source_of_wealth\": [], \"key_assets\": \"Assets\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"United States (USA)\", \"US Senate\"]}}"
    )

    # RETRY LOGIKA (Bando iki 3 kartų, jei serveris perkrautas)
    for attempt in range(3):
        try:
            response = requests.post(GEMINI_URL, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            })
            
            resp_json = response.json()

            if 'candidates' in resp_json:
                ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())
                
                # ... (čia lieka tavo WP siuntimo kodas iš praeito žingsnio) ...
                
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
                requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
                print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
                return # Išeiname iš funkcijos, nes pavyko

            elif "high demand" in str(resp_json).lower() or "503" in str(resp_json):
                wait_time = (attempt + 1) * 60
                print(f"  ⚠️ Serveris užimtas. Bandymas {attempt+1}/3. Laukiame {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ Klaida: {resp_json}")
                break

        except Exception as e:
            print(f"  🚨 Klaida: {e}")
            time.sleep(30)

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            time.sleep(70)
