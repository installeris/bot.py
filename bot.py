import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- 🚀 BOTAS STARTUOJA (Gemini 2.0 Flash Fix) ---")

GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# ── Greitesnis ir stabilesnis modelis ─────────────────────────────────────────
MODEL_ID    = "gemini-2.0-flash"
GEMINI_URL  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_KEY}"

WP_TIMEOUT     = 30
IMG_TIMEOUT    = 20
GEMINI_TIMEOUT = 60   # 2.0-flash turi atsakyti per 60s

WEALTH_OPTIONS = ["Stock Market Investments", "Real Estate Holdings", "Venture Capital",
                  "Professional Law Practice", "Family Inheritance"]
CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2,
    "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19
}

stats = {"ok": 0, "fail": 0, "skip": 0}


def get_wiki_image(name):
    print(f"    [1/4] 🌐 Wikipedia nuotrauka...")
    try:
        url = (f"https://en.wikipedia.org/w/api.php?action=query&titles={name}"
               f"&prop=pageimages&format=json&pithumbsize=1200")
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                print(f"    [1/4] ✅ Rasta")
                return pages[pg]["thumbnail"]["source"]
        print(f"    [1/4] ⚠️ Nerasta")
    except Exception as e:
        print(f"    [1/4] ⚠️ Klaida: {e}")
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
            data=img_res.content, headers=headers,
            auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT
        )
        if res.status_code == 201:
            media_id = res.json()["id"]
            print(f"    [2/4] ✅ Įkelta (ID: {media_id})")
            return media_id
        print(f"    [2/4] ❌ {res.status_code}: {res.text[:150]}")
    except requests.exceptions.Timeout:
        print(f"    [2/4] ⏱️ Timeout – tęsiame be nuotraukos")
    except Exception as e:
        print(f"    [2/4] ⚠️ {e}")
    return None


def call_gemini_with_retry(prompt, retries=4):
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048   # Ribojame outputą – greičiau atsako
        },
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                      "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]
    }
    for i in range(retries):
        try:
            print(f"    [3/4] ⏳ Gemini bandymas {i+1}/{retries}...")
            t0 = time.time()
            response = requests.post(GEMINI_URL, json=payload, timeout=GEMINI_TIMEOUT)
            elapsed = round(time.time() - t0, 1)
            print(f"    [3/4] 📡 Atsakė per {elapsed}s – statusas: {response.status_code}")

            if response.status_code == 200:
                print(f"    [3/4] ✅ Gemini OK")
                return response.json()
            elif response.status_code in (429, 503):
                print(f"    [3/4] ⚠️ Rate limit. Laukiam {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)
            elif response.status_code == 404:
                print(f"    [3/4] 🚨 Modelis '{MODEL_ID}' nerastas!")
                break
            else:
                print(f"    [3/4] ❌ Klaida {response.status_code}: {response.text[:200]}")
                break

        except requests.exceptions.Timeout:
            elapsed = round(time.time() - t0, 1)
            print(f"    [3/4] ⏱️ TIMEOUT po {elapsed}s! Bandymas {i+1}/{retries}. Laukiam {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, 120)
        except Exception as e:
            print(f"    [3/4] ❌ Išimtis: {e}")
            break

    print(f"    [3/4] 🚨 Visi Gemini bandymai nepavyko")
    return None


def parse_json_from_gemini(text):
    # 1. ```json ... ``` blokas
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        return json.loads(md.group(1))
    # 2. Pirmasis { ... } blokas
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return json.loads(brace.group())
    return json.loads(text)


def post_to_wp(name, data, img_id):
    print(f"    [4/4] 📝 Keliame į WordPress...")
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
                json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT
            )
            print(f"    [4/4] 📡 WP atsakė: {wp_res.status_code}")
            if wp_res.status_code == 201:
                print(f"    [4/4] ✅ Straipsnis įkeltas!")
                return True
            elif wp_res.status_code in (500, 502, 503, 504):
                print(f"    [4/4] ⚠️ WP serverio klaida. Laukiam {10*(attempt+1)}s...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"    [4/4] ❌ WP klaida {wp_res.status_code}: {wp_res.text[:300]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] ⏱️ WP TIMEOUT! Bandymas {attempt+1}/3")
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] ❌ Išimtis: {e}")
            return False

    print(f"    [4/4] 🚨 Visi WP bandymai nepavyko")
    return False


def run_wealth_bot(politician_name):
    num = stats['ok'] + stats['fail'] + stats['skip'] + 1
    print(f"\n{'='*55}")
    print(f"💎 [{num}] {politician_name}")
    print(f"{'='*55}")

    # 1. Nuotrauka
    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        img_id = upload_image_to_wp(politician_name, wiki_img)

    # 2. Gemini – TRUMPESNIS promptas = greitesnis atsakas
    prompt = (
        f"Write a 900-word financial article on {politician_name} net worth in 2026. "
        f"Use H2/H3 HTML tags. Bold key facts.\n\n"
        f"Respond ONLY with this JSON, no extra text, no markdown:\n"
        f'{{"article":"<h2>...</h2>...","net_worth":"$XM","job_title":"Title",'
        f'"history":"2020:XM,2026:XM","urls":["https://ballotpedia.org/..."],'
        f'"wealth_sources":["Real Estate"],"assets":"brief text",'
        f'"seo_title":"SEO title","seo_desc":"SEO desc under 160 chars",'
        f'"cats":["US Senate"]}}'
    )

    res = call_gemini_with_retry(prompt)
    if not res or "candidates" not in res:
        print(f"  🚨 PRALEISTA: {politician_name}")
        stats["skip"] += 1
        return

    # 3. JSON parsinavimas
    try:
        full_text = res["candidates"][0]["content"]["parts"][0]["text"]
        print(f"    [3/4] 🔍 Atsakymo ilgis: {len(full_text)} simbolių")
        data = parse_json_from_gemini(full_text)
    except Exception as e:
        print(f"  🚨 JSON klaida: {e}")
        print(f"  📄 Pradžia: {full_text[:400]}")
        stats["fail"] += 1
        return

    # 4. WordPress
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

    print(f"📋 Vardų skaičius: {len(names)}")

    for i, name in enumerate(names):
        run_wealth_bot(name)

        if i < len(names) - 1:
            pause = 20 if (i + 1) % 10 == 0 else 8
            print(f"\n⏸️  Pauzė {pause}s... (✅{stats['ok']} ❌{stats['fail']} ⏭️{stats['skip']})")
            time.sleep(pause)

    print(f"\n{'='*55}")
    print(f"📊 REZULTATAI: ✅ {stats['ok']} | ❌ {stats['fail']} | ⏭️ {stats['skip']}")
    print(f"{'='*55}")
