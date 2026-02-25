import os
import requests
import google.generativeai as genai
import json
import re
import time

# 1. KONFIGŪRACIJA IŠ GITHUB SECRETS
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_URL = "https://politiciannetworth.com/wp-json/wp/v2/posts"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# TAVO KATEGORIJŲ ID ŽEMĖLAPIS
CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "State Governors": 4, "European Parliament": 18, "United States (USA)": 19,
    "United Kingdom (UK)": 20, "Germany": 8, "France": 9, "Italy": 10, "Global": 23
}

def run_wealth_bot(politician_name):
    print(f"🚀 Analizuojame ir rašome apie: {politician_name}...")
    
    prompt = f"""
    You are an expert financial biographer. Research {politician_name}.
    Write a 600-word SEO-optimized article in English about their net worth and finances.
    Include 2-3 interesting personal facts or trivia to make it feel human-written.
    Use H2/H3 headers and bullet points.
    
    Return ONLY JSON:
    {{
    "article": "HTML formatted text (<h2>, <h3>, <p>, <ul>, <li>)",
    "net_worth": "Number only",
    "job_title": "Current position",
    "main_assets": "Most valuable asset",
    "wealth_sources": ["Must choose from: Stock Market Investments, Real Estate Holdings, Venture Capital, Professional Law Practice, Family Inheritance, Book Deals & Royalties, Corporate Board Seats, Consulting Fees, Hedge Fund Interests, Cryptocurrency Assets"],
    "history": "2023:X, 2024:Y, 2025:Z",
    "seo_title": "Catchy SEO Title",
    "seo_desc": "Meta description with a hook",
    "cats": ["Category names like 'Italy', 'US Senate', 'Executive Branch'"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Išvalome JSON
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not json_match: return
        
        data = json.loads(json_match.group())

        target_cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP]
        if not target_cats: target_cats = [23]

        payload = {
            "title": f"{politician_name} Net Worth",
            "content": data["article"],
            "status": "publish",
            "categories": target_cats,
            "acf": {
                "job_title": data["job_title"],
                "net_worth": data["net_worth"],
                "source_of_wealth": data["wealth_sources"],
                "main_assets": data["main_assets"],
                "net_worth_history": data["history"],
                "sources": "https://www.wikipedia.org\nhttps://www.opensecrets.org"
            },
            "rank_math_title": data["seo_title"],
            "rank_math_description": data["seo_desc"],
            "rank_math_focus_keyword": f"{politician_name} Net Worth"
        }

        res = requests.post(WP_URL, json=payload, auth=(WP_USER, WP_PASS))
        if res.status_code == 201:
            print(f"✅ PUBLIKUOTA: {politician_name}")
        else:
            print(f"❌ WP Klaida: {res.status_code}")
            
    except Exception as e:
        print(f"🚨 Klaida su {politician_name}: {e}")

if __name__ == "__main__":
    if os.path.exists("names.txt"):
        with open("names.txt", "r") as f:
            names = [line.strip() for line in f if line.strip()]
        
        total = len(names)
        for index, name in enumerate(names, 1):
            run_wealth_bot(name)
            
            if index < total:
                print(f"⏳ ({index}/{total}) Baigta. Kita užklausa po 5 minučių...")
                time.sleep(300) # 5 minutės (300 sekundžių)
        
        print("🏁 Darbas baigtas!")
