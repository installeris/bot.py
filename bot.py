import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🏁 BOTAS STARTUOJA (Auto-Model Detection) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

if not all([GEMINI_KEY, WP_USER, WP_PASS]):
    print("🚨 KLAIDA: Trūksta GitHub Secrets!")
    sys.exit(1)

def get_working_model():
    """Patikrina, kokį modelį tavo raktas leidžia naudoti."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        # Prioritetas Flash modeliams
        for m in models:
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except: return None

# Surandame tikslų modelio pavadinimą tavo raktui
ACTIVE_MODEL = get_working_model()
if ACTIVE_MODEL:
    print(f"✅ Naudosime modelį: {ACTIVE_MODEL}")
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"
else:
    print("🚨 KLAIDA: Nepavyko rasti jokio veikiančio modelio tavo raktui!")
    sys.exit(1)

# --- STANDARTINĖS FUNKCIJOS ---
def get_wiki_image(name):
    try:
        res = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000").json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    try:
        img_data = requests.get(image_url).content
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_data, 
                            headers={"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"},
                            auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Dirbame su: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    prompt = (f"Research {politician_name}. Write a 600-word SEO article in English about their net worth. "
              f"Return ONLY a valid JSON object: {{\"article\": \"...\", \"net_worth\": \"...\", \"job_title\": \"...\", \"cats\": []}}")
    
    try:
        response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
        if response.status_code != 200:
            print(f"  ❌ API Klaida: {response.status_code}")
            return

        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "acf": {"net_worth": data.get("net_worth", ""), "job_title": data.get("job_title", "")}
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ PUBLIKUOTA!" if res.status_code == 201 else f"  ❌ WP Klaida: {res.text}")
    except Exception as e: print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(10)
