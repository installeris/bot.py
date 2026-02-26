import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 💎 PROFESIONALUS ANALITIKAS (No-Block Version) ---")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {"US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19}

# Naudojame v1beta, nes ji geriausiai priima saugumo nustatymus
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

def get_wiki_image(name):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={name}&prop=pageimages&format=json&pithumbsize=1200"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]: return pages[pg]["thumbnail"]["source"]
    except: return None

def run_wealth_bot(politician_name):
    print(f"\n🕵️ Tiriamas turtas: {politician_name}")
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        try:
            img_res = requests.get(wiki_img)
            headers = {"Content-Disposition": f"attachment; filename=img.jpg", "Content-Type": "image/jpeg"}
            res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
            img_id = res.json()["id"]
        except: pass

    prompt = (
        f"Write a professional 900-word financial biography for {politician_name} in 2026. \n"
        f"FACTS: Use data from OpenSecrets/Ballotpedia. Show net worth growth from 2018 to 2026. \n"
        f"STYLE: Conversational, expert, informative. Use H2/H3 and **bold numbers**. \n"
        f"JSON: {{ \"article\": \"HTML\", \"net_worth\": \"$M\", \"job_title\": \"Title\", \"history\": \"2018:X,2021:Y,2026:Z\", \"urls\": [\"URL1\", \"URL2\"], \"wealth_sources\": [], \"assets\": \"Asset1, Asset2\", \"seo_title\": \"SEO Title\", \"seo_desc\": \"SEO Desc\", \"cats\": [] }}"
    )

    # SVARBU: Išjungiami filtrai, kad nebūtų 'candidates' klaidos
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    try:
        response = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings,
            "generationConfig": {"temperature": 0.7}
        })
        
        res_json = response.json()
        if 'candidates' not in res_json:
            print(f"  ❌ Google blokas: {res_json.get('promptFeedback', 'Saugumo filtrai')}")
            return

        ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.search(r'\{.*\}', ai_text, re.DOTALL).group())

        # Šaltinių dizainas
        sources_list = "".join([f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>' for u in data.get("urls", [])])
        sources_html = f"<p><strong>Financial Data Sources:</strong></p><ul>{sources_list}</ul>"

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
                "sources": sources_html
            },
            # Rank Math laukai
            "rank_math_title": data.get("seo_title", ""),
            "rank_math_description": data.get("seo_desc", ""),
            "rank_math_focus_keyword": f"{politician_name} net worth"
        }

        wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
        print(f"  ✅ SĖKMĖ: {politician_name} paskelbtas!")

    except Exception as e:
        print(f"  🚨 Klaida: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            for name in [n.strip() for n in f if n.strip()]:
                run_wealth_bot(name)
                time.sleep(10)
