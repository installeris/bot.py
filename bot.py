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
        "gemini-2.0-flash-001", "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite", "gemini-2.0-flash",
        "gemini-flash-latest", "gemini-1.5-flash",
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
        print(f"  Klaida: {e}")
        available = []

    chosen = next((p for p in preferred if p in available), None)
    if not chosen:
        chosen = next((m for m in available if "flash" in m.lower()), "gemini-2.0-flash-001")
    print(f"  Bandysime: {chosen}")

    test_payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    for version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{chosen}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            print(f"  {version} -> {r.status_code}")
            if r.status_code in (200, 400):
                return url
        except Exception as e:
            print(f"  {version} klaida: {e}")

    for model in available[:8]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            print(f"  {model} -> {r.status_code}")
            if r.status_code in (200, 400):
                print(f"  Rastas: {model}")
                return url
        except:
            pass

    print("KLAIDA: Nepavyko rasti Gemini URL!")
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
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 8192},
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                      "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
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
    print("    [3/4] Visi bandymai nepavyko")
    return None


def parse_json(text):
    for t in [text, text.strip()]:
        try:
            return json.loads(t)
        except:
            pass
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        try:
            return json.loads(md.group(1))
        except:
            pass
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        try:
            return json.loads(text[s:e+1])
        except:
            pass
    raise ValueError(f"Nepavyko parsinuoti JSON. Pradzia: {text[:300]}")


def make_slug(name):
    """Sukuria SEO slug: pvz. 'Tammy Baldwin' -> 'tammy-baldwin-net-worth'"""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return f"{slug}-net-worth"


def format_sources_html(urls):
    """
    Svarbu: sources laukelis turi buti tik plain HTML <ul><li>...,
    nes WP custom field rodo ji kaip HTML. Naudojame domeno pavadinima
    kaip anchor teksta.
    """
    items = []
    for url in urls:
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        label = domain.replace("opensecrets.org", "OpenSecrets") \
                      .replace("ballotpedia.org", "Ballotpedia") \
                      .replace("senate.gov", "U.S. Senate") \
                      .replace("house.gov", "U.S. House") \
                      .replace("forbes.com", "Forbes")
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def clean_net_worth(raw):
    """
    Paliekame $XM arba $XB formata.
    Pvz: "$1.2M" -> "$1.2M", "$1,200,000" -> "$1.2M"
    """
    raw = str(raw).strip()
    # Jei jau tvarkingas formatas
    if re.match(r"^\$[\d,\.]+[MBK]?$", raw):
        return raw
    # Bandome isskirti skaiciu
    nums = re.findall(r"[\d,\.]+", raw)
    if nums:
        num = float(nums[0].replace(",", ""))
        if num >= 1_000_000_000:
            return f"${num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"${num/1_000:.0f}K"
        else:
            return f"${num:.1f}M"
    return raw


def clean_history(raw):
    """
    Formatas turi buti: 2022:1200000,2023:1500000,2024:1800000,2025:2000000,2026:2200000
    Pilni skaiciai (ne 0.05M) - kad grafike teisingai atvaizduotu.
    Konvertuojame jei gauta M/B formatu.
    """
    if not raw:
        return ""
    entries = []
    for part in raw.split(","):
        part = part.strip()
        m = re.match(r"(\d{4}):(.+)", part)
        if not m:
            continue
        year = m.group(1)
        val_raw = m.group(2).strip()
        # Konvertuojame i skaiciu
        try:
            if val_raw.endswith("B") or val_raw.endswith("b"):
                num = float(val_raw[:-1]) * 1_000_000_000
            elif val_raw.endswith("M") or val_raw.endswith("m"):
                num = float(val_raw[:-1]) * 1_000_000
            elif val_raw.endswith("K") or val_raw.endswith("k"):
                num = float(val_raw[:-1]) * 1_000
            else:
                num = float(val_raw.replace(",", ""))
            entries.append(f"{year}:{int(num)}")
        except:
            entries.append(part)
    return ",".join(entries)


def post_to_wp(name, data, img_id):
    print("    [4/4] Keliame i WordPress...")

    # Kategorijos - visada 2
    cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2]
    if len(cats) < 2 and 19 not in cats:
        cats.append(19)  # pridedame "United States (USA)"

    # Saltiniai - grazus HTML
    sources_html = format_sources_html(data.get("urls", []))

    # Net worth - tvarkingas formatas
    net_worth = clean_net_worth(data.get("net_worth", ""))

    # History - pilni skaiciai
    history = clean_history(data.get("history", ""))

    # Source of wealth - tik is leidžiamo saraso
    matched_sources = [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2]

    # Assets - trumpas tekstas
    assets = data.get("assets", "")

    # SEO
    seo_title = data.get("seo_title", f"{name} Net Worth 2026")[:60]

    # Description - BEZ net worth sumos (kad zmogus eitu i svetaine)
    seo_desc = f"Explore {name}'s financial background, career earnings, and key assets in 2026. Full breakdown inside."
    if len(seo_desc) > 155:
        seo_desc = seo_desc[:152] + "..."

    # Focus keyword
    focus_keyword = f"{name} Net Worth 2026"

    # Slug - tvarkingas
    slug = make_slug(name)

    # Straipsnio pavadinimas - be metaduomenu, tik vardas
    title = f"{name} Net Worth 2026"

    payload = {
        "title":          title,
        "slug":           slug,
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
            "rank_math_title":          seo_title,
            "rank_math_description":    seo_desc,
            "rank_math_focus_keyword":  focus_keyword,
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
                resp_data = wp_res.json()
                link = resp_data.get("link", "")
                actual_slug = resp_data.get("slug", "")
                print(f"    [4/4] Ikeltas! {link}")
                print(f"    [4/4] Slug: {actual_slug}")
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
    return f"""You are writing a financial profile for politiciannetworth.com.

Write a 700-900 word article about {name}'s net worth in 2026.
Rules:
- Simple, human language. Do NOT sound like AI. Add 1-2 interesting lesser-known facts.
- Use <h2> and <h3> HTML tags. Use <strong> for key numbers.
- Base ALL estimates ONLY on real public sources: OpenSecrets, Ballotpedia, official financial disclosures, Forbes, Reuters, AP.
- net_worth: the most accurate estimate you can find, in format "$XM" or "$XB". If under $1M use "$X00K".
- history: realistic yearly net worth for 2022,2023,2024,2025,2026 in FULL NUMBERS (not 0.05M - write the actual dollar amount like 1200000). Format: "2022:1200000,2023:1500000,2024:1800000,2025:2000000,2026:2200000"
- wealth_sources: pick MAX 2 from EXACTLY this list: ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
- assets: ONE sentence naming only the 1-2 main asset types. Example: "Investment portfolio and primary residence in Wisconsin."
- cats: pick 1-2 from: ["US Senate", "US House of Representatives", "Executive Branch", "State Governors", "United States (USA)"]
- seo_title: under 60 chars, example: "{name} Net Worth 2026"
- urls: 2-3 real working URLs from opensecrets.org, ballotpedia.org, senate.gov, or house.gov only.

Return ONLY valid JSON. No markdown. No extra text. No trailing commas.

{{"article":"<h2>...</h2><p>...</p>","net_worth":"$XM","job_title":"U.S. Senator","history":"2022:1200000,2023:1500000,2024:1800000,2025:2000000,2026:2200000","urls":["https://ballotpedia.org/...","https://opensecrets.org/..."],"wealth_sources":["Real Estate Holdings","Stock Market Investments"],"assets":"One sentence about main assets.","seo_title":"{name} Net Worth 2026","cats":["US Senate","United States (USA)"]}}"""


def run_wealth_bot(politician_name, gemini_url):
    num = stats['ok'] + stats['fail'] + stats['skip'] + 1
    print(f"\n{'='*55}")
    print(f"[{num}] {politician_name}")
    print(f"{'='*55}")

    img_id = None
    wiki_img = get_wiki_image(politician_name)
    if wiki_img:
        img_id = upload_image_to_wp(politician_name, wiki_img)

    res = call_gemini(build_prompt(politician_name), gemini_url)
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
