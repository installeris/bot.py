import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (2026 Auto-Model Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# --- AUTOMATINIS MODELIO PARINKIMAS ---
def find_best_model():
    # Tikriname per v1beta, kad matytume naujausius Flash modelius
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
        # Prioritetas: Gemini 3 Flash -> Gemini 2.5 Flash -> Gemini 2.0 Flash -> Gemini 1.5 Flash
        for version in ["gemini-3-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            for m in models:
                if version in m:
                    print(f"  🎯 Rastas veikiantis modelis: {m}")
                    return m
        return models[0] if models else "models/gemini-1.5-flash"
    except Exception as e:
        print(f"  ⚠️ Nepavyko gauti sąrašo, bandomas standartinis: {e}")
        return "models/gemini-1.5-flash"

ACTIVE_MODEL = find_best_model()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"

# --- FUNKCIJOS ---
def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def upload_to_wp(image_url, politician_name):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        return res.json()["id"] if res.status_code == 201 else None
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Analizuojamas: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    prompt = (
        f"Generate a 1000-word financial analysis for {politician_name} in 2026. \n"
        f"Use HTML structure (H2, H3, **bold** facts). \n"
        f"Return JSON: {{\"article\": \"HTML\", \"net_worth\": \"$10M\", \"job_title\": \"Senator\", \"history\": \"2019:8M,2026:10M\", \"raw_urls\": [\"url1\", \"url2\"], \"wealth_sources\": [\"Real Estate Holdings\"], \"assets\": \"Homes\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"US Senate\"]}}"
    )

    try:
        # Priverstinis saugumo filtrų išjungimas politiniam turiniui
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        })
        
        if response.status_code != 200:
            print(f"  ❌ API Klaida: {response.text}")
            return

        ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        sources_html = "".join([f'<li><a href="{url}" target="_blank" rel="nofollow">{url}</a></li>' for url in data.get("raw_urls", [])])

        payload = {
            "title": data.get("seo_title", f"{politician_name} Net Worth 2026"),
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "acf": {
                "job_title": data.get("job_title", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": data.get("wealth_sources", [])[:2],
                "main_assets": data.get("assets", ""),
                "sources": f"<ul>{sources_html}</ul>"
            }
        }

        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name}")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
