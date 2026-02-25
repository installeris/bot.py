import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- ⚡ BOTAS STARTUOJA (Mokamas planas: Didelis greitis) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame stabilią v1 versiją. Ji pigiausia ir greičiausia Paid Tier'e.
MODEL_ID = "gemini-1.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties", "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets"]

def run_wealth_bot(politician_name):
    print(f"🚀 Generuojama: {politician_name}...")
    
    prompt = (
        f"Generate a professional financial report for {politician_name} for 2026. \n"
        f"Return ONLY a valid JSON object: {{\"article\": \"HTML content with H2/H3 tags\", \"net_worth\": \"$X,XXX,XXX\", \"job_title\": \"Official Role\", \"history\": \"2019:X,2020:Y...\", \"sources_html\": \"Links\", \"source_of_wealth\": [], \"key_assets\": \"Assets\", \"seo_title\": \"SEO Title\", \"seo_desc\": \"Meta Desc\", \"cats\": [\"United States (USA)\"]}}"
    )
    
    # Retry logika: bando iki 3 kartų, jei gauna klaidą
    for attempt in range(3):
        try:
            response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            res_data = response.json()
            
            if 'candidates' in res_data:
                ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())
                
                payload = {
                    "title": f"{politician_name} Net Worth",
                    "content": data["article"],
                    "status": "publish",
                    "categories": [19], # United States (USA)
                    "acf": {
                        "job_title": data.get("job_title", ""),
                        "net_worth": data.get("net_worth", ""),
                        "net_worth_history": data.get("history", ""),
                        "source_of_wealth": [s for s in data.get("source_of_wealth", []) if s in WEALTH_OPTIONS],
                        "main_assets": data.get("key_assets", ""),
                        "sources": data.get("sources_html", "")
                    },
                    "rank_math_title": data.get("seo_title", ""),
                    "rank_math_description": data.get("seo_desc", "")
                }
                
                wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
                if wp_res.status_code == 201:
                    print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas.")
                    return # Išeiname iš funkcijos po sėkmės
                else:
                    print(f"  ❌ WP Klaida: {wp_res.text}")
                    break
            
            elif "429" in str(res_data):
                wait_time = (attempt + 1) * 5
                print(f"  ⚠️ Limitai viršyti. Laukiame {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ Bandymas {attempt+1} nepavyko: {res_data}")
                time.sleep(2)

        except Exception as e:
            print(f"  🚨 Klaida su {politician_name}: {e}")
            time.sleep(2)

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        
        for name in names:
            run_wealth_bot(name)
            # Dabar užtenka 3-5 sekundžių tarpų, kad WordPress spėtų suvirškinti nuotraukas/duomenis
            time.sleep(3) 

print("\n--- 🏁 VISI VARDAI APDOROTI ---")
