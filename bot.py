import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (DEBUG versija) ---")

GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

MODEL_ID    = "gemini-2.5-flash"
GEMINI_URL  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

# ── Timeouts ───────────────────────────────────────────────────────────────────
WP_TIMEOUT     = 30
IMG_TIMEOUT    = 20
GEMINI_TIMEOUT = 120   # Gemini 2.5 gali būti lėtas – 2 min max

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital",
                  "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2,
    "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19
}

stats = {"ok": 0, "fail": 0, "skip": 0}


def get_wiki_image(name):
    print(f"    [1/4] 🌐 Ieškome Wikipedia nuotraukos...")
    try:
        url = (f"https://en.wikipedia.org/w/api.php?action=query&titles={name}"
               f"&prop=pageimages&format=json&pithumbsize=1200")
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                src = pages[pg]["thumbnail"]["source"]
                print(f"    [1/4] ✅ Nuotrauka rasta")
                return src
        print(f"    [1/4] ⚠️ Nuotrauka nerasta")
    except Exception as e:
        print(f"    [1/4] ⚠️ Wiki klaida: {e}")
    return None


def upload_image_to_wp(name, img_url):
    print(f"    [2/4] 📤 Keliame nuotrauką į WP...")
    try:
        img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=IMG_TIMEOUT)
        img_res.raise_for_status()
        headers = {
            "Content-Disposition": f"attachment; filename={name.replace(' ', '_')}.jpg",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/media",
            data=img_res.content,
            headers=headers,
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT
        )
        if res.status_code == 201:
            media_id = res.json()["id"]
            print(f"    [2/4] ✅ Nuotrauka įkelta (ID: {media_id})")
            return media_id
        else:
            print(f"    [2/4] ❌ Media klaida {res.status_code}: {res.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"    [2/4] ⏱️ Nuotraukos įkėlimas TIMEOUT – tęsiame be jos")
    except Exception as e:
        print(f"    [2/4] ⚠️ Media išimtis: {e}")
    return None


def call_gemini_with_retry(prompt, retries=5):
    print(f"    [3/4] 🤖 Siunčiame užklausą Gemini...")
    delay = 10
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                      "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]
    }
    for i in range(retries):
        try:
            print(f"    [3/4] ⏳ Bandymas {i+1}/{retries} (timeout={GEMINI_TIMEOUT}s)...")
            response = requests.post(GEMINI_URL, json=payload, timeout=GEMINI_TIMEOUT)
            print(f"    [3/4] 📡 Gemini atsakė: {response.status_code}")
            if response.status_code == 200:
                print(f"    [3/4] ✅ Gemini atsakymas gautas")
                return response.json()
            elif response.status_code in (429, 503):
                print(f"    [3/4] ⚠️ Rate limit / serveris užimtas. Laukiam {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)
            elif response.status_code == 404:
                print(f"    [3/4] 🚨 Modelis '{MODEL_ID}' nerastas!")
                break
            else:
                print(f"    [3/4] ❌ Gemini klaida {response.status_code}: {response.text[:300]}")
                break
        except requests.exceptions.Timeout:
            print(f"    [3/4] ⏱️ Gemini TIMEOUT po {GEMINI_TIMEOUT}s! Bandymas {i+1}/{retries}")
            time.sleep(delay)
            delay = min(delay * 2, 120)
        except Exception as e:
            print(f"    [3/4] ❌ Gemini išimtis: {e}")
            break
    print(f"    [3/4] 🚨 Visi Gemini bandymai nepavyko")
    return None


def parse_json_from_gemini(text):
    # 1. ```json ... ``` blokas
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        return json.loads(md.group(1))
    # 2. { ... } regex
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return json.loads(brace.group())
    # 3. Tiesiogiai
    return json.loads(text)


def post_to_wp(name, data, img_id):
    print(f"    [4/4] 📝 Keliame straipsnį į WordPress...")
    sources_html = "".join([
        f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>'
        for u in data.get("urls", [])
    ])
    payload = {
        "title": f"{name} Net Worth 2026: Financial Portfolio & Assets",
        "content": data["article"],
        "status": "publish",
        "featured_media": img_id,
        "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2],
        "acf": {
            "job_title":         data.get("job_title", ""),
            "net_worth":         data.get("net_worth", ""),
            "net_worth_history": data.get("history", ""),
            "source_of_wealth":  [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2],
            "main_assets":       data.get("assets", ""),
            "sources":           f"<ul>{sources_html}</ul>"
        },
        "rank_math_title":       data.get("seo_title", ""),
        "rank_math_description": data.get("seo_desc", "")
    }

    for attempt in range(3):
        try:
            print(f"    [4/4] ⏳ WP POST bandymas {attempt+1}/3...")
            wp_res = requests.post(
                f"{WP_BASE_URL}/wp/v2/posts",
                json=payload,
                auth=(WP_USER, WP_PASS),
                timeout=WP_TIMEOUT
            )
            print(f"    [4/4] 📡 WP atsakė: {wp_res.status_code}")
            if wp_res.status_code == 201:
                print(f"    [4/4] ✅ Straipsnis įkeltas!")
                return True
            elif wp_res.status_code in (500, 502, 503, 504):
                print(f"    [4/4] ⚠️ WP serverio klaida {wp_res.status_code}. Laukiam {10*(attempt+1)}s...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"    [4/4] ❌ WP klaida {wp_res.status_code}: {wp_res.text[:300]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] ⏱️ WP TIMEOUT po {WP_TIMEOUT}s! Bandymas {attempt+1}/3")
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] ❌ WP išimtis: {e}")
            return False
    print(f"    [4/4] 🚨 Visi WP bandymai nepavyko")
    return False


def run_wealth_bot(politician_name):
    num = stats['ok'] + stats['fail'] + stats['skip'] + 1
    print(f"\n{'='*55}")
    print(f"💎 [{num}] PRADEDAME: {politician_name}")
    print(f"{'='*55}")

    # 1. Nuotrauka
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        img_id = upload_image_to_wp(politician_name, wiki_img)

    # 2. Gemini
    prompt = (
        f"Write a 1000-word financial case study on {politician_name} for 2026.\n"
        f"Use H2/H3 tags and **bold** key facts. Focus on net worth growth.\n"
        f"Return ONLY valid JSON (no markdown, no extra text):\n"
        f'{{"article":"HTML","net_worth":"$10M","job_title":"Senator",'
        f'"history":"2019:8M,2026:10M","urls":["https://ballotpedia.org/example"],'
        f'"wealth_sources":["Real Estate"],"assets":"Text","seo_title":"Title",'
        f'"seo_desc":"Desc","cats":["US Senate"]}}'
    )

    res = call_gemini_with_retry(prompt)
    if not res or "candidates" not in res:
        print(f"  🚨 PRALEISTA (Gemini nepavyko): {politician_name}")
        stats["skip"] += 1
        return

    # 3. JSON
    try:
        full_text = res["candidates"][0]["content"]["parts"][0]["text"]
        print(f"    [3/4] 🔍 JSON ilgis: {len(full_text)} simbolių")
        data = parse_json_from_gemini(full_text)
    except Exception as e:
        print(f"  🚨 JSON klaida: {e}")
        print(f"  📄 Pirmieji 500 simbolių: {full_text[:500]}")
        stats["fail"] += 1
        return

    # 4. WP
    ok = post_to_wp(politician_name, data, img_id)
    if ok:
        stats["ok"] += 1
        print(f"  🎉 SĖKMĖ: {politician_name}")
    else:
        stats["fail"] += 1
        print(f"  💀 NEPAVYKO: {politician_name}")


if __name__ == "__main__":
    if not os.path.exists("names.txt"):
        print("❌ names.txt nerastas!")
        sys.exit(1)

    with open("names.txt", "r") as f:
        names = [n.strip() for n in f if n.strip()]

    print(f"📋 Iš viso vardų: {len(names)}")

    for i, name in enumerate(names):
        run_wealth_bot(name)

        # Pauzė tarp straipsnių (didesnė kas 10)
        if i < len(names) - 1:
            pause = 15 if (i + 1) % 10 == 0 else 7
            print(f"\n⏸️  Laukiam {pause}s... (ok={stats['ok']}, fail={stats['fail']}, skip={stats['skip']})")
            time.sleep(pause)

    print(f"\n{'='*55}")
    print(f"📊 GALUTINĖ STATISTIKA:")
    print(f"   ✅ Sėkminga: {stats['ok']}")
    print(f"   ❌ Nepavyko: {stats['fail']}")
    print(f"   ⏭️  Praleista: {stats['skip']}")
    print(f"{'='*55}")
