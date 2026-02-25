import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (JSON Mode & Stability Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame v1beta, nes ji geriausiai palaiko JSON Mode
MODEL_ID = "gemini-1.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

def run_wealth_bot(politician_name):
    print(f"💎 Analizuojamas: {politician_name}")
    
    # Griežtas nurodymas dėl struktūros
    prompt = (
        f"Research {politician_name} for a net worth article set in 2026. "
        f"Return a JSON object with these EXACT keys: "
        f"'article' (full HTML content), 'net_worth' (string), 'job_title' (string), "
        f"'history' (string format 2019:X,2020:Y), 'sources_html' (HTML links), "
        f"'source_of_wealth' (array of strings), 'seo_title' (string), 'seo_desc' (string)."
    )
    
    # Konfigūracija, kuri priverčia Gemini grąžinti TIK JSON
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
        }
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        res_data = response.json()
        
        if 'candidates' in res_data:
            # Ištraukiame tekstą, kuris dabar garantuotai yra JSON formatu
            raw_output = res_data['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(raw_output)
            
            # Patikriname, ar visi raktai egzistuoja, kad išvengtume KeyError
            article_content = data.get("article", "No content generated")
            
            wp_payload = {
                "title": f"{politician_name} Net Worth",
                "content": article_content,
                "status": "publish",
                "categories": [19], # United States (USA)
                "acf": {
                    "job_title": data.get("job_title", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("source_of_wealth", []),
                    "sources": data.get("sources_html", "")
                },
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", "")
            }
            
            res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS))
            
            if res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
            else:
                print(f"  ❌ WP Klaida: {res.text}")
        else:
            print(f"  ❌ API Klaida: {res_data}")

    except Exception as e:
        print(f"  🚨 Kritinė klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
        
        for name in names:
            run_wealth_bot(name)
            time.sleep(3) # Maža pauzė dėl WP stabilumo
