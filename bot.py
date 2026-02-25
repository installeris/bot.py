import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (2026 Stable Edition) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# 2026-ųjų modelių prioritetų sąrašas (nuo naujausio iki seniausio)
MODEL_PRIORITY = [
    "gemini-2.5-flash",       # Pagrindinis 2026-ųjų arkliukas
    "gemini-2.0-flash-001",   # Labai stabilus
    "gemini-1.5-flash",       # Jei dar neuždarytas tavo regione
    "gemini-3-flash-preview"  # Eksperimentinis greitis
]

def get_working_url():
    """Patikrina, kuris modelis veikia tavo paskyroje."""
    for model in MODEL_PRIORITY:
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            test_res = requests.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=5)
            if test_res.status_code == 200:
                print(f"✅ Surastas veikiantis modelis: {model}")
                return url
        except:
            continue
    return None

WORKING_URL = get_working_url()

def run_wealth_bot(politician_name):
    if not WORKING_URL:
        print("🚨 Klaida: Nerastas nei vienas veikiantis Gemini modelis. Patikrink API raktą.")
        return

    print(f"💎 Ruošiamas: {politician_name}")
    
    prompt = (
        f"Generate JSON for {politician_name} net worth 2026. "
        f"Include HTML article, net_worth, job_title, history, and source_of_wealth. "
        f"Return ONLY valid JSON."
    )
    
    try:
        response = requests.post(WORKING_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_data = response.json()
        
        if 'candidates' in res_data:
            ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())
            
            payload = {
                "title": f"{politician_name} Net Worth",
                "content": data["article"],
                "status": "publish",
                "categories": [19],
                "acf": {
                    "job_title": data.get("job_title", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("source_of_wealth", []),
                    "main_assets": data.get("key_assets", ""),
                    "sources": data.get("sources_html", "")
                }
            }
            
            res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            print(f"  ✅ Paskelbta!" if res.status_code == 201 else f"  ❌ WP Klaida: {res.status_code}")
        else:
            print(f"  ❌ API Klaida: {res_data}")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(2) # Kadangi planas mokamas, laukti beveik nereikia
