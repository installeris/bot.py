import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🛡️ BOTAS STARTUOJA: FULL AUTOMATION V8 ---")

# Konfigūracija iš tavo aplinkos kintamųjų
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Modelio nustatymai (Tier 1 stabilumas)
MODEL_ID = "gemini-1.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

# Tavo nustatytos kategorijos ir šaltiniai
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {
    "US Senate": 1, 
    "US House of Representatives": 2, 
    "Executive Branch": 3, 
    "State Governors": 4, 
    "United States (USA)": 19,
    "Congress Trades": 21 # Pridėjau tavo minėtą kategoriją
}

def get_wiki_image(name):
    """Garantuota Wikipedia nuotraukos paieška su paieškos funkcija."""
    headers = {'User-Agent': 'PoliticianNetWorthBot/1.0 (contact@politiciannetworth.com)'}
    try:
        # 1. Bandymas: Tiesmuka paieška su Redirects
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1000&redirects=1"
        res = requests.get(url, headers=headers, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                return pages[pg]["thumbnail"]["source"]
        
        # 2. Bandymas: Jei nerado, ieškome per Wikipedia paieškos variklį
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={name}&format=json"
        search_res = requests.get(search_url, headers=headers, timeout=10).json()
        results = search_res.get("query", {}).get("search", [])
        if results:
            best_title = results[0]['title']
            # Kartojame su tiksliu surastu pavadinimu
            return get_wiki_image(best_title)
    except:
        return None
    return None

def run_wealth_bot(name):
    print(f"\n🔍 Tikrinamas asmuo: {name}")
    
    # 1. FOTO PATIKRA (Jei nėra - stop)
    wiki_img_url = get_wiki_image(name)
    if not wiki_img_url:
        print(f"  ⏭️ PRALEIDŽIAMA: Nuotrauka Wikipedia sistemoje nerasta.")
        return

    # 2. FOTO ĮKĖLIMAS Į WP
    img_id = None
    try:
        img_data = requests.get(wiki_img_url, timeout=15).content
        files = {
            "file": (f"{name.replace(' ', '_')}.jpg", img_data, "image/jpeg"),
            "title": name
        }
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", files=files, auth=(WP_USER, WP_PASS), timeout=20)
        if res.status_code == 201:
            img_id = res.json()["id"]
            print(f"  📸 Foto įkelta sėkmingai (ID: {img_id})")
        else:
            print(f"  ⏭️ PRALEIDŽIAMA: WP nepriėmė nuotraukos ({res.status_code})")
            return
    except:
        print(f"  ⏭️ PRALEIDŽIAMA: Klaida keliant nuotrauką.")
        return

    # 3. TURINIO GENERAVIMAS (AI)
    print(f"  🧠 Generuojamas straipsnis...")
    prompt = (
        f"Write a comprehensive 900-word financial case study on {name} for 2026. \n"
        f"STRUCTURE: Use H2/H3 tags, **bold** important numbers. Make it readable and human-like. \n"
        f"DATA: Realistically estimate net worth growth from 2018 to 2026 (based on public data). \n"
        f"SEO: Create a Rank Math Title and Description. \n"
        f"SOURCES: Include 2-3 links to OpenSecrets, Ballotpedia or FEC. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$10M\", \"job\": \"Official\", "
        f"\"history\": \"2018:5M,2022:8M,2026:10M\", \"urls\": [\"URL1\"], "
        f"\"wealth_src\": [\"Real Estate\"], \"assets\": \"Asset1, Asset2\", \"seo_t\": \"Title\", \"seo_d\": \"Desc\", \"cats\": [\"United States (USA)\"]}}"
    )

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])

        # Šaltinių HTML formavimas
        sources_list = "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])])
        sources_html = f"<strong>Financial Data Sources:</strong><ul>{sources_list}</ul>"

        # 4. POSTINIMAS Į WP
        wp_payload = {
            "title": f"{name} Net Worth 2026: Portfolio & Assets",
            "content": data["article"],
            "status": "publish",
            "featured_media": img_id,
            "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2],
            "acf": {
                "job_title": data.get("job", ""),
                "net_worth": data.get("net_worth", ""),
                "net_worth_history": data.get("history", ""),
                "source_of_wealth": [s for s in data.get("wealth_src", []) if s in WEALTH_OPTIONS][:2],
                "main_assets": data.get("assets", ""),
                "sources": sources_html
            },
            "rank_math_title": data.get("seo_t", ""),
            "rank_math_description": data.get("seo_d", ""),
            "rank_math_focus_keyword": f"{name} net worth"
        }

        final_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=wp_payload, auth=(WP_USER, WP_PASS), timeout=30)
        if final_res.status_code == 201:
            print(f"  ✅ SĖKMĖ: {name} straipsnis paskelbtas!")
        else:
            print(f"  ❌ WP KLAIDA: {final_res.text}")

    except Exception as e:
        print(f"  🚨 API/JSON KLAIDA: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [n.strip() for n in f if n.strip()]
            for name in names:
                run_wealth_bot(name)
                time.sleep(15) # Saugus intervalas Tier 1 limitams
