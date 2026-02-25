import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🛠️ BOTAS STARTUOJA (Auto-Fix Mode) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

def get_working_model():
    """Automatiškai randa tikslų modelio pavadinimą tavo paskyrai."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        res = requests.get(url).json()
        if 'models' not in res:
            print(f"🚨 Klaida pasiekiant API: {res}")
            return None
        
        # Ieškome bet kurio 'flash' modelio, kuris palaiko turinio kūrimą
        for m in res['models']:
            if "flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                print(f"✅ Rastas veikiantis modelis: {m['name']}")
                return m['name']
        return None
    except Exception as e:
        print(f"⚠️ Nepavyko gauti modelių sąrašo: {e}")
        return None

# Nustatome veikiantį modelį
MODEL_PATH = get_working_model()

def run_wealth_bot(politician_name):
    if not MODEL_PATH:
        print("🚨 Klaida: Nerastas tinkamas modelis. Patikrink API raktą.")
        return

    print(f"💎 Analizuojamas: {politician_name}")
    
    # URL dabar formuojamas dinamiškai pagal tai, ką grąžino Google
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_PATH}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        f"Research {politician_name} for a net worth article set in 2026. "
        f"Return ONLY a JSON object with keys: article, net_worth, job_title, history, sources_html, source_of_wealth, seo_title, seo_desc."
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
        }
    }
    
    try:
        response = requests.post(gemini_url, json=payload, timeout=60)
        data = response.json()
        
        if 'candidates' in data:
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            content = json.loads(raw_text)
            
            wp_payload = {
                "title": f"{politician_name} Net Worth",
                "content": content.get("article", ""),
                "status": "publish",
                "categories": [19],
                "acf": {
                    "job_title": content.get("job_title", ""),
                    "net_worth": content.get("net_worth", ""),
                    "net_worth_history": content.get("history", ""),
                    "source_of_wealth": content.get("source_of_wealth", []),
                    "sources": content.get("sources_html", "")
                },
                "rank_math_title": content.get("seo_title", ""),
                "rank_math_description": content.get("seo_desc", "")
            }
            
            res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS))
            print(f"  ✅ SĖKMĖ: {politician_name}" if res.status_code == 201 else f"  ❌ WP Klaida: {res.status_code}")
        else:
            print(f"  ❌ API Klaida: {data}")

    except Exception as e:
        print(f"  🚨 Klaida apdorojant {politician_name}: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        for name in names:
            run_wealth_bot(name)
            time.sleep(3)
