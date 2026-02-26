import os
import requests
import json
import re
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

print("--- BOTAS STARTUOJA ---")

GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

WP_TIMEOUT     = 30
IMG_TIMEOUT    = 20
GEMINI_TIMEOUT = 90

WEALTH_OPTIONS = [
    "Stock Market Investments", "Real Estate Holdings", "Venture Capital",
    "Professional Law Practice", "Family Inheritance"
]
CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2,
    "Executive Branch": 3, "State Governors": 4, "United States (USA)": 19
}

stats = {"ok": 0, "fail": 0, "skip": 0}


def find_gemini_url():
    preferred = [
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash",
    ]
    print("  Gauname modeliu sarasa...")
    try:
        res = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}",
            timeout=15
        ).json()
        available = [
            m["name"].replace("models/", "")
            for m in res.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        print(f"  Rasti modeliai: {available}")
    except Exception as e:
        print(f"  Klaida gaunant sarasa: {e}")
        available = []

    chosen = None
    for p in preferred:
        if p in available:
            chosen = p
            break
    if not chosen:
        for m in available:
            if "flash" in m.lower():
                chosen = m
                break
    if not chosen:
        chosen = "gemini-2.0-flash-001"

    print(f"  Bandysime modeli: {chosen}")
    test_payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    for version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{chosen}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            print(f"  {version} -> {r.status_code}")
            if r.status_code in (200, 400):
                print(f"  Naudosime: {version}")
                return url
        except Exception as e:
            print(f"  {version} klaida: {e}")

    print("  Bandome visus galimus modelius...")
    for model in available[:8]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            print(f"  {model} -> {r.status_code}")
            if r.status_code in (200, 400):
                print(f"  Rastas veikiantis: {model}")
                return url
        except Exception as e:
            print(f"  {model}: {e}")

    print("KLAIDA: Nepavyko rasti veikiancio Gemini URL!")
    sys.exit(1)


def get_wiki_image(name):
    print("    [1/4] Wikipedia nuotrauka...")
    try:
        url = (f"https://en.wikipedia.org/w/api.php?action=query&titles={name}"
               f"&prop=pageimages&format=json&pithumbsize=1200")
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        pages = res.get("query", {}).get("pages", {})
        for pg in pages:
            if "thumbnail" in pages[pg]:
                print("    [1/4] Rasta")
                return pages[pg]["thumbnail"]["source"]
        print("    [1/4] Nerasta")
    except Exception as e:
        print(f"    [1/4] Klaida: {e}")
    return None


def upload_image_to_wp(name, img_url):
    print("    [2/4] Keliame nuotrauka i WP...")
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
            print(f"    [2/4] Ikelta (ID: {media_id})")
            return media_id
        print(f"    [2/4] Klaida {res.status_code}: {res.text[:150]}")
    except requests.exceptions.Timeout:
        print("    [2/4] Timeout - tesiame be nuotraukos")
    except Exception as e:
        print(f"    [2/4] {e}")
    return None


def call_gemini(prompt, gemini_url, retries=4):
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 8192
        },
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in [
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]
        ]
    }
    for i in range(retries):
        try:
            print(f"    [3/4] Gemini bandymas {i+1}/{retries}...")
            t0 = time.time()
            response = requests.post(gemini_url, json=payload, timeout=GEMINI_TIMEOUT)
            elapsed = round(time.time() - t0, 1)
            print(f"    [3/4] Atsake per {elapsed}s - statusas: {response.status_code}")
            if response.status_code == 200:
                print("    [3/4] Gemini OK")
                return response.json()
            elif response.status_code in (429, 503):
                print(f"    [3/4] Rate limit. Laukiam {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                print(f"    [3/4] Klaida {response.status_code}: {response.text[:200]}")
                break
        except requests.exceptions.Timeout:
            print(f"    [3/4] TIMEOUT! Laukiam {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, 120)
        except Exception as e:
            print(f"    [3/4] Iskimtis: {e}")
            break
    print("    [3/4] Visi Gemini bandymai nepavyko")
    return None


def parse_json(text):
    for attempt in [text, text.strip()]:
        try:
            return json.loads(attempt)
        except:
            pass
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        try:
            return json.loads(md.group(1))
        except:
            pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    raise ValueError(f"Nepavyko parsinuoti JSON. Pradzia: {text[:300]}")


def format_sources_html(urls):
    """Grazus saltiniai su domeno pavadinimu kaip tekstu."""
    items = []
    for url in urls:
        # Isimame domeno pavadinima kaip display teksta
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{domain}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def post_to_wp(name, data, img_id):
    print("    [4/4] Keliame i WordPress...")

    # Kategorijos - imame iki 2
    cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2]
    # Jei tik 1 kategorija rasta - pridedame "United States (USA)" kaip antra
    if len(cats) == 1:
        if 19 not in cats:
            cats.append(19)

    # Source of wealth - tiksliai is WEALTH_OPTIONS saraso
    raw_sources = data.get("wealth_sources", [])
    matched_sources = [s for s in raw_sources if s in WEALTH_OPTIONS][:2]

    # Net worth - isvalome, paliekame tik skaiciaus formata
    net_worth = data.get("net_worth", "")

    # History - tikslus formatas: "2022:2M,2023:2.5M,2024:3M,2025:3.5M,2026:4M"
    history = data.get("history", "")

    # Assets - trumpas tekstas, tik pagrindiniai 1-2 saltiniai
    assets = data.get("assets", "")

    # SEO laukeliai
    seo_title = data.get("seo_title", f"{name} Net Worth 2026")
    seo_desc  = data.get("seo_desc", f"Learn about {name}'s net worth, assets, and financial portfolio in 2026.")

    sources_html = format_sources_html(data.get("urls", []))

    payload = {
        "title":          f"{name} Net Worth 2026: Financial Portfolio & Assets",
        "content":        data["article"],
        "status":         "publish",
        "featured_media": img_id,
        "categories":     cats,
        "acf": {
            "job_title":         data.get("job_title", ""),
            "net_worth":         net_worth,
            "net_worth_history": history,
            "source_of_wealth":  matched_sources,
            "main_assets":       assets,
            "sources":           sources_html
        },
        "meta": {
            "rank_math_title":       seo_title,
            "rank_math_description": seo_desc,
        }
    }

    for attempt in range(3):
        try:
            print(f"    [4/4] WP POST bandymas {attempt+1}/3...")
            wp_res = requests.post(
                f"{WP_BASE_URL}/wp/v2/posts",
                json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT
            )
            print(f"    [4/4] WP atsake: {wp_res.status_code}")
            if wp_res.status_code == 201:
                link = wp_res.json().get("link", "")
                print(f"    [4/4] Ikeltas! {link}")
                return True
            elif wp_res.status_code in (500, 502, 503, 504):
                print(f"    [4/4] WP serverio klaida. Laukiam {10*(attempt+1)}s...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"    [4/4] WP klaida {wp_res.status_code}: {wp_res.text[:300]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] WP TIMEOUT! Bandymas {attempt+1}/3")
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] Iskimtis: {e}")
            return False
    print("    [4/4] Visi WP bandymai nepavyko")
    return False


def build_prompt(name):
    return f"""You are writing a financial profile article for the website politiciannetworth.com.

Write a 700-900 word article about {name}'s net worth in 2026.
- Use simple language that any reader can understand. Do NOT sound like AI.
- Include 1-2 interesting personal facts or lesser-known details about their career or background.
- Use <h2> and <h3> HTML tags for sections. Use <strong> for key numbers.
- Base net worth estimates ONLY on verified public sources: OpenSecrets, Ballotpedia, financial disclosures, Forbes, or major news outlets.
- For net_worth_history: find realistic yearly estimates for 2022, 2023, 2024, 2025, 2026 from public financial disclosures. Format: "2022:XM,2023:XM,2024:XM,2025:XM,2026:XM" where X is a number in millions (e.g. 2022:1.2M).
- For wealth_sources: pick ONLY from this exact list (max 2): ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
- For assets: write 1 sentence naming the 1-2 main asset types only (e.g. "Investment portfolio and primary residence in Wisconsin.")
- For cats: pick up to 2 from: ["US Senate", "US House of Representatives", "Executive Branch", "State Governors", "United States (USA)"]
- seo_title must be under 60 characters.
- seo_desc must be under 155 characters and include the politician's name and net worth year.
- urls: include 2-3 real, working URLs from opensecrets.org, ballotpedia.org, or senate.gov/house.gov only.

Respond ONLY with valid JSON. No markdown. No extra text. No trailing commas.

{{"article":"<h2>...</h2><p>...</p>","net_worth":"$XM","job_title":"U.S. Senator","history":"2022:XM,2023:XM,2024:XM,2025:XM,2026:XM","urls":["https://ballotpedia.org/...","https://opensecrets.org/..."],"wealth_sources":["Real Estate Holdings","Stock Market Investments"],"assets":"One sentence about main assets only.","seo_title":"{name} Net Worth 2026","seo_desc":"{name} net worth in 2026 estimated at $XM. Learn about their financial portfolio and assets.","cats":["US Senate","United States (USA)"]}}"""


def run_wealth_bot(politician_name, gemini_url):
    num = stats['ok'] + stats['fail'] + stats['skip'] + 1
    print(f"\n{'='*55}")
    print(f"[{num}] {politician_name}")
    print(f"{'='*55}")

    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        img_id = upload_image_to_wp(politician_name, wiki_img)

    prompt = build_prompt(politician_name)

    res = call_gemini(prompt, gemini_url)
    if not res or "candidates" not in res:
        print(f"  PRALEISTA: {politician_name}")
        stats["skip"] += 1
        return

    try:
        full_text = res["candidates"][0]["content"]["parts"][0]["text"]
        print(f"    [3/4] Atsakymo ilgis: {len(full_text)} simboliu")
        data = parse_json(full_text)
    except Exception as e:
        print(f"  JSON klaida: {e}")
        try:
            print(f"  Pradzia: {full_text[:400]}")
        except:
            pass
        stats["fail"] += 1
        return

    ok = post_to_wp(politician_name, data, img_id)
    if ok:
        stats["ok"] += 1
        print(f"  SEKME: {politician_name}")
    else:
        stats["fail"] += 1
        print(f"  NEPAVYKO: {politician_name}")


if __name__ == "__main__":
    if not os.path.exists("names.txt"):
        print("KLAIDA: names.txt nerastas!")
        sys.exit(1)

    print("\nIeskome veikiancio Gemini URL...")
    gemini_url = find_gemini_url()
    print("Gemini URL nustatytas.\n")

    with open("names.txt", "r") as f:
        names = [n.strip() for n in f if n.strip()]

    print(f"Vardu skaicius: {len(names)}")

    for i, name in enumerate(names):
        run_wealth_bot(name, gemini_url)

        if i < len(names) - 1:
            pause = 20 if (i + 1) % 10 == 0 else 8
            print(f"\nPauze {pause}s... (ok={stats['ok']} fail={stats['fail']} skip={stats['skip']})")
            time.sleep(pause)

    print(f"\n{'='*55}")
    print(f"REZULTATAI: ok={stats['ok']} | fail={stats['fail']} | skip={stats['skip']}")
    print(f"{'='*55}")
