import os
import requests
from google import genai
import json
import re
import time
import sys

# KONFIGŪRACIJA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

print("--- 🏁 STARTAS ---")
print(f"Patikra: Gemini raktas yra: {'✅ YRA' if GEMINI_KEY else '❌ TRŪKSTA'}")
print(f"Patikra: WP User yra: {'✅ YRA' if WP_USER else '❌ TRŪKSTA'}")

try:
    client = genai.Client(api_key=GEMINI_KEY)
    print("✅ Gemini klientas sukurtas sėkmingai.")
except Exception as e:
    print(f"❌ Klaida kuriant Gemini klientą: {e}")
    sys.exit(1)

def run_wealth_bot(politician_name):
    print(f"\n💎 Dirbame su: {politician_name}")
    prompt = f"Write a short 300-word article about {politician_name} net worth. Return ONLY JSON: {{'article': '...', 'net_worth': '...', 'job_title': '...', 'main_assets': '...', 'wealth_sources': [], 'history': '...', 'seo_title': '...', 'seo_desc': '...', 'cats': []}}"
    
    try:
        print("  🧠 Generuojame turinį per AI...")
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        print("  ✅ AI atsakymas gautas.")
        
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            print("  ❌ AI nesugeneravo JSON.")
            return

        data = json.loads(match.group())
        
        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": [23],
            "acf": {
                "job_title": data["job_title"],
                "net_worth": data["net_worth"]
            }
        }

        print("  ✉️ Siunčiame į WordPress...")
        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        
        if res.status_code == 201:
            print(f"  ✨ SĖKMĖ: {politician_name} paskelbtas!")
        else:
            print(f"  ❌ WP Klaida {res.status_code}: {res.text}")
            
    except Exception as e:
        print(f"  🚨 Klaida procese: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [l.strip() for l in f if l.strip()]
        
        print(f"📚 Rasta vardų: {len(names)}")
        for i, name in enumerate(names, 1):
            run_wealth_bot(name)
            if i < len(names):
                print(f"⏳ Miegame 5 min... ({i}/{len(names)})")
                time.sleep(300)
    else:
        print("🚨 Klaida: names.txt failas nerastas!")
