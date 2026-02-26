import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (2026 Model Migration Fix) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# --- SVARBU: Nauji 2026 m. modelių pavadinimai ---
# gemini-1.5-flash nebeegzistuoja. Naudojame 2.5 arba 3.0.
MODEL_ID = "gemini-2.5-flash" 
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def call_gemini_with_retry(prompt, retries=5):
    delay = 10
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    
    for i in range(retries):
        response = requests.post(GEMINI_URL, json=payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            print(f"  ⚠️ Serveris užimtas (503). Bandymas {i+1}. Laukiame {delay}s...")
            time.sleep(delay)
            delay *= 2
        elif response.status_code == 404:
            print(f"  🚨 Modelis {MODEL_ID} nerastas (404). Tikrink modelio pavadinimą!")
            break
        else:
            print(f"  ❌ API Klaida {response.status_code}: {response.text}")
            break
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    
    if wiki_img:
        try:
            img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
            headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            img_id = res.json()["id"] if res.status_code == 201 else None
        except: pass

    prompt = (
        f"Write a 1000-word financial case study on {politician_name} for 2026. \n"
        f"Use H2/H3 tags and **bold** key facts. Focus on net worth growth. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$10M\", \"job_title\": \"Senator\", "
        f"\"history\": \"2019:8M,2026:10M\", \"urls\": [\"https://ballotpedia.org/example\"], "
        f"\"wealth_sources\": [\"Real Estate\"], \"assets\": \"Text\", \"seo_title\": \"Title\", "
        f"\"seo_desc\": \"Desc\", \"cats\": [\"US Senate\"]}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            # Ištraukiame tik JSON dalį
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            sources_html = "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])])

            payload = {
                "title": f"{politician_name} Net Worth 2026: Financial Portfolio & Assets",
                "content": data["article"],
                "status": "publish",
                "featured_media": img_id,
                "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2],
                "acf": {
                    "job_title": data.get("job_title", ""),
                    "net_worth": data.get("net_worth", ""),
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2],
                    "main_assets": data.get("assets", ""),
                    "sources": f"<ul>{sources_html}</ul>"
                },
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", "")
            }
            wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            if wp_res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")
            else:
                print(f"  ❌ WP Klaida: {wp_res.text}")
        except Exception as e:
            print(f"  🚨 Klaida apdorojant AI atsakymą: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
