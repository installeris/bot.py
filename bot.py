import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🛡️ BOTAS: PHOTO-ONLY MODE (2026 Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Naudojame stabiliausią 2026 m. modelį
MODEL_ID = "gemini-1.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n🔍 Tikrinama: {politician_name}")
    
    # 1. ŽINGSNIS: Ieškome nuotraukos
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Nuotrauka nerasta Wikipedia sistemoje.")
        return

    # 2. ŽINGSNIS: Bandome įkelti nuotrauką į WP
    img_id = None
    try:
        img_res = requests.get(wiki_img, timeout=15)
        if img_res.status_code == 200:
            headers = {
                "Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg",
                "Content-Type": "image/jpeg"
            }
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS), timeout=20)
            if res.status_code == 201:
                img_id = res.json()["id"]
                print(f"  📸 Foto įkelta (ID: {img_id})")
            else:
                print(f"  ⏭️ PRALEIDŽIAMA: Nepavyko įkelti foto į WP (Status: {res.status_code})")
                return
        else:
            print(f"  ⏭️ PRALEIDŽIAMA: Wikipedia nuotraukos URL nepasiekiamas.")
            return
    except Exception as e:
        print(f"  ⏭️ PRALEIDŽIAMA: Klaida keliant foto ({e})")
        return

    # 3. ŽINGSNIS: Generuojame straipsnį tik jei turime img_id
    prompt = (
        f"Write an 850-word financial analysis for {politician_name} in 2026. \n"
        f"Include net worth history (2018-2026), H2/H3 tags, and **bold figures**. \n"
        f"SEO: Provide Rank Math Title and Description. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$X.M\", \"job\": \"Role\", \"history\": \"2018:X,2022:Y,2026:Z\", \"urls\": [\"URL1\"], \"wealth\": [], \"assets\": \"Text\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\"}}"
    )

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        if response.status_code != 200:
            print(f"  ❌ API Klaida: {response.text}")
            return

        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        # Šaltinių dizainas
        sources_html = "<strong>Financial Data Sources:</strong><ul>" + "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])]) + "</ul>"

        wp_payload = {
            "title": f"{politician_name} Net Worth 2026",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [19, 1],
            "acf": {
                "job_title": data.get("job", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": data.get("wealth", [])[:2],
                "main_assets": data.get("assets", ""),
                "sources": sources_html
            },
            "rank_math_title": data.get("seo_t", ""),
            "rank_math_description": data.get("seo_d", "")
        }

        final_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS), timeout=30)
        if final_res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
        else:
            print(f"  ❌ WP Klaida: {final_res.text}")

    except Exception as e:
        print(f"  🚨 Klaida apdorojant tekstą: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(15)
