import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (February 2026 Edition) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Tavo nustatytos kategorijos ir šaltiniai
WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

# Stabiliausias 2026 m. kelias
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

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

def call_gemini_with_retry(prompt, retries=5):
    """Bando gauti atsakymą, jei serveris 503 (perkrautas)."""
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
            print(f"  ⚠️ Serveris perkrautas (503). Bandymas {i+1}/{retries}. Laukiame {delay}s...")
            time.sleep(delay)
            delay *= 2
        else:
            print(f"  ❌ API Klaida {response.status_code}: {response.text}")
            break
    return None

def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    img_id = upload_to_wp(get_wiki_image(politician_name), politician_name)

    prompt = (
        f"Write a 1000-word financial bio for {politician_name} (2026 update). \n"
        f"Use H2/H3 tags and **bold** key facts. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$10M\", \"job_title\": \"Senator\", "
        f"\"history\": \"2019:8M,2026:10M\", \"urls\": [\"https://ballotpedia.org/URL1\"], "
        f"\"wealth_sources\": [\"Real Estate\"], \"assets\": \"Text\", \"seo_title\": \"Title\", "
        f"\"seo_desc\": \"Desc\", \"cats\": [\"US Senate\"]}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.search(r'\{.*\}', full_text, re.DOTALL).group())
            
            # Nuorodos be vidinių redirectų
            sources_html = "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])])

            payload = {
                "title": f"{politician_name} Net Worth 2026",
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
                }
            }
            requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            print(f"  ✅ SĖKMĖ: {politician_name} įkeltas!")
        except Exception as e:
            print(f"  🚨 Klaida apdorojant: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(5)
