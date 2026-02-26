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

# Autorius "Financial Research Team" - rask WP Admin -> Users -> ID
AUTHOR_ID      = 3   # <- pakeisk i tikra "Financial Research Team" vartotojo ID
WP_TIMEOUT     = 30
IMG_TIMEOUT    = 20
GEMINI_TIMEOUT = 120

# ── Pilnas wealth options sąrašas ─────────────────────────────────────────────
WEALTH_OPTIONS = [
    "Stock Market Investments",
    "Real Estate Holdings",
    "Venture Capital",
    "Professional Law Practice",
    "Family Inheritance",
    "Book Deals & Royalties",
    "Corporate Board Seats",
    "Consulting Fees",
    "Hedge Fund Interests",
    "Cryptocurrency Assets",
]

# ── Kategorijų žemėlapis ──────────────────────────────────────────────────────
CAT_MAP = {
    "US Senate":                   1,
    "US House of Representatives": 2,
    "Executive Branch":            3,
    "State Governors":             4,
    "State Senators":              5,
    "House of Commons":            6,
    "House of Lords":              7,
    "Germany":                     8,
    "France":                      9,
    "Italy":                       10,
    "Spain":                       11,
    "Poland":                      12,
    "Romania":                     13,
    "Netherlands":                 14,
    "Belgium":                     15,
    "Greece":                      16,
    "Sweden":                      17,
    "European Parliament":         18,
    "United States (USA)":         19,
    "United Kingdom (UK)":         20,
    "Global":                      23,
}

# Tėvinės kategorijos
PARENT_CAT = {
    1:  19,  # US Senate -> United States (USA)
    2:  19,  # US House -> United States (USA)
    3:  19,  # Executive Branch -> United States (USA)
    4:  19,  # State Governors -> United States (USA)
    5:  19,  # State Senators -> United States (USA)
    6:  20,  # House of Commons -> United Kingdom (UK)
    7:  20,  # House of Lords -> United Kingdom (UK)
    8:  18,  # Germany -> European Parliament
    9:  18,  # France -> European Parliament
    10: 18,  # Italy -> European Parliament
    11: 18,  # Spain -> European Parliament
    12: 18,  # Poland -> European Parliament
    13: 18,  # Romania -> European Parliament
    14: 18,  # Netherlands -> European Parliament
    15: 18,  # Belgium -> European Parliament
    16: 18,  # Greece -> European Parliament
    17: 18,  # Sweden -> European Parliament
}

stats = {"ok": 0, "fail": 0, "skip": 0}


# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
def call_gemini(prompt, gemini_url, retries=4):
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16384},
        "tools": [{"google_search": {}}],
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


# ─────────────────────────────────────────────────────────────────────────────
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
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return f"{slug}-net-worth"


def parse_to_int(val_str):
    """$2.3M -> 2300000, $410K -> 410000, 2300000 -> 2300000"""
    val_str = str(val_str).strip().replace(",", "").replace("$", "")
    try:
        if val_str.upper().endswith("B"):
            return int(float(val_str[:-1]) * 1_000_000_000)
        elif val_str.upper().endswith("M"):
            return int(float(val_str[:-1]) * 1_000_000)
        elif val_str.upper().endswith("K"):
            return int(float(val_str[:-1]) * 1_000)
        else:
            return int(float(val_str))
    except:
        return 0


def clean_net_worth(raw):
    """-> plain integer string: '2300000'"""
    num = parse_to_int(raw)
    return str(num) if num > 0 else "0"


def clean_history(raw):
    """-> '2022:1200000,2023:1500000,...'"""
    if not raw:
        return ""
    entries = []
    for part in raw.split(","):
        part = part.strip()
        m = re.match(r"(\d{4}):(.+)", part)
        if not m:
            continue
        num = parse_to_int(m.group(2))
        if num > 0:
            entries.append(f"{m.group(1)}:{num}")
    return ",".join(entries)


def format_sources(urls):
    """
    Plain URL per eilutę – kaip svetainė tikisi.
    Pvz:
    https://disclosures-clerk.house.gov/
    https://www.quiverquant.com/
    """
    return "\n".join(url.strip() for url in urls if url.strip())


def resolve_categories(cat_names):
    """Subkategorija + automatiškai tėvinė."""
    cat_ids = set()
    for name in cat_names:
        if name in CAT_MAP:
            cat_id = CAT_MAP[name]
            cat_ids.add(cat_id)
            if cat_id in PARENT_CAT:
                cat_ids.add(PARENT_CAT[cat_id])
    if not cat_ids:
        cat_ids.add(23)  # Global fallback
    return list(cat_ids)


def build_seo_desc(name, job_title, net_worth_raw):
    """
    Unikalus SEO description iki 160 simbolių.
    Kiekvienas politikas gauna skirtingą tekstą.
    """
    num = parse_to_int(net_worth_raw)
    if num >= 1_000_000_000:
        worth_str = f"${num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        worth_str = f"${num/1_000_000:.1f}M"
    elif num >= 1_000:
        worth_str = f"${num/1_000:.0f}K"
    else:
        worth_str = "millions"

    desc = f"{name}, {job_title}, has an estimated net worth of {worth_str} in 2026. Explore their assets, income sources, and full financial breakdown."
    return desc[:160]


# ─────────────────────────────────────────────────────────────────────────────
def post_to_wp(name, data, img_id):
    print("    [4/4] Keliame i WordPress...")

    cats = resolve_categories(data.get("cats", []))
    print(f"    Kategorijos: {cats}")

    net_worth = clean_net_worth(data.get("net_worth", "0"))
    print(f"    Net worth: {data.get('net_worth','')} -> {net_worth}")

    history = clean_history(data.get("history", ""))
    print(f"    History: {history[:80]}")

    sources = format_sources(data.get("urls", []))

    matched_sources = [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2]
    print(f"    Wealth sources: {matched_sources}")

    assets = data.get("assets", "")
    job_title = data.get("job_title", "")

    seo_title = data.get("seo_title", f"{name} Net Worth 2026")[:60]
    seo_desc  = build_seo_desc(name, job_title, data.get("net_worth", "0"))
    focus_kw  = f"{name} Net Worth 2026"

    print(f"    SEO desc ({len(seo_desc)} chars): {seo_desc}")

    # References sekcija straipsnio apačioje
    refs_html = build_references_html(
        data.get("urls", []),
        job_title,
        net_worth
    )
    full_article = data["article"] + refs_html

    payload = {
        "title":          f"{name} Net Worth 2026",
        "slug":           make_slug(name),
        "content":        full_article,
        "status":         "publish",
        "author":         AUTHOR_ID,
        "featured_media": img_id,
        "categories":     cats,
        "acf": {
            "job_title":         job_title,
            "net_worth":         net_worth,
            "net_worth_history": history,
            "source_of_wealth":  matched_sources,
            "main_assets":       assets,
            "sources":           sources,
        },
        "meta": {
            "rank_math_title":         seo_title,
            "rank_math_description":   seo_desc,
            "rank_math_focus_keyword": focus_kw,
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
                resp = wp_res.json()
                print(f"    [4/4] Ikeltas! {resp.get('link','')} | slug: {resp.get('slug','')}")
                return True
            elif wp_res.status_code in (500, 502, 503, 504):
                print(f"    [4/4] WP serverio klaida. Laukiam {10*(attempt+1)}s...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"    [4/4] WP klaida {wp_res.status_code}: {wp_res.text[:400]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] WP TIMEOUT! Bandymas {attempt+1}/3")
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] Iskimtis: {e}")
            return False
    print("    [4/4] Visi WP bandymai nepavyko")
    return False


# ─────────────────────────────────────────────────────────────────────────────
def build_references_html(urls, job_title, net_worth_display):
    """
    Gražus References sekcija straipsnio apačioje su schema markup.
    """
    from datetime import datetime
    month_year = datetime.now().strftime("%B %Y")

    label_map = {
        "opensecrets.org":        "OpenSecrets – Personal Finances",
        "ballotpedia.org":        "Ballotpedia – Political Biography",
        "disclosures-clerk.house.gov": "U.S. House Financial Disclosures",
        "quiverquant.com":        "Quiver Quantitative – Congress Trading",
        "senate.gov":             "U.S. Senate – Official Profile",
        "house.gov":              "U.S. House – Official Profile",
        "parliament.uk":          "UK Parliament – Member Profile",
        "europarl.europa.eu":     "European Parliament – MEP Profile",
        "forbes.com":             "Forbes – Wealth Estimate",
        "reuters.com":            "Reuters",
        "apnews.com":             "AP News",
    }

    items = []
    for i, url in enumerate(urls, 1):
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        label = domain
        for key, val in label_map.items():
            if key in domain:
                label = val
                break
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')

    refs_html = "".join(items)

    return f"""
<hr style="margin: 40px 0 20px;">
<div class="references-section">
  <h2>References &amp; Sources</h2>
  <p><em>Last updated: {month_year}. Net worth estimates are based on public financial disclosures and independent research.</em></p>
  <ul>{refs_html}</ul>
</div>"""


def build_prompt(name):
    cats_list = ", ".join(CAT_MAP.keys())
    wealth_list = ", ".join(WEALTH_OPTIONS)
    return f"""You are a financial researcher. Your job is to find REAL, ACCURATE information about {name} and write a financial profile.

DO NOT use placeholder values. DO NOT copy example values. Every field must be based on real research.

STEP 1 - RESEARCH {name}:
- Find their actual job title (Senator, Congressman, Prime Minister, CEO, MEP, etc.)
- Find their actual net worth from: OpenSecrets, Ballotpedia, Forbes, financial disclosures, Reuters, AP, Roll Call, quiverquant.com, disclosures-clerk.house.gov
- Find their actual main income sources and assets
- Find their actual political chamber/country to assign correct category

STEP 2 - FILL THESE FIELDS with REAL data:

net_worth: their actual estimated net worth as plain integer dollars. 
  Examples: 2300000 = $2.3M, 410000 = $410K, 1500000000 = $1.5B
  This MUST be their real estimated net worth, not a placeholder.

job_title: their REAL current job title. Examples: "U.S. Senator", "Member of Parliament", "MEP", "State Governor", "Prime Minister", "CEO"

history: their REAL estimated net worth for each year 2022-2026 as plain integers.
  These numbers MUST vary realistically based on actual financial disclosure trends.
  Format: "2022:INTEGER,2023:INTEGER,2024:INTEGER,2025:INTEGER,2026:INTEGER"
  Example for someone worth $2.3M: "2022:1600000,2023:1900000,2024:2100000,2025:2200000,2026:2300000"
  Example for someone worth $50M: "2022:35000000,2023:40000000,2024:44000000,2025:47000000,2026:50000000"

wealth_sources: analyze HOW this specific person actually made their money.
  Pick 1-2 that TRULY apply to THIS person from this list: [{wealth_list}]
  Think carefully - a lawyer turned senator picks "Professional Law Practice", a tech investor picks "Stock Market Investments", someone with inherited money picks "Family Inheritance".

assets: ONE sentence describing THIS person's actual main assets. Be specific. Example: "Primary home in Wisconsin and a diversified mutual fund portfolio." NOT a generic description.

cats: pick 1-2 categories that match THIS person's actual role and country: [{cats_list}]

urls: 2-3 real working URLs for THIS person from: opensecrets.org, ballotpedia.org, disclosures-clerk.house.gov, quiverquant.com, senate.gov, house.gov, parliament.uk, europarl.europa.eu

seo_title: "{name} Net Worth 2026" (under 60 chars)

STEP 3 - WRITE the article:
- 700-900 words about {name} specifically
- Simple language, not AI-sounding
- Add 1-2 interesting lesser-known personal facts about {name}
- Use <h2> and <h3> HTML tags, bold key numbers with <strong>

Return ONLY valid JSON. No markdown. No extra text. No trailing commas.

{{"article":"<h2>...</h2><p>...</p>","net_worth":"REAL_INTEGER","job_title":"REAL_JOB_TITLE","history":"2022:REAL_INT,2023:REAL_INT,2024:REAL_INT,2025:REAL_INT,2026:REAL_INT","urls":["REAL_URL_1","REAL_URL_2"],"wealth_sources":["REAL_SOURCE_1"],"assets":"One specific sentence about their actual assets.","seo_title":"{name} Net Worth 2026","cats":["REAL_CATEGORY"]}}"""


# ─────────────────────────────────────────────────────────────────────────────
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
        candidate = res["candidates"][0]
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        full_text = candidate["content"]["parts"][0]["text"]
        print(f"    Atsakymo ilgis: {len(full_text)} simboliu, finishReason: {finish_reason}")
        if finish_reason == "MAX_TOKENS":
            print("    PERSPEJIMAS: Gemini nupjove atsakyma! Bandome dar karta...")
            stats["fail"] += 1
            return
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


# ─────────────────────────────────────────────────────────────────────────────
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
