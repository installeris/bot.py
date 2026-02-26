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
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192},
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


# ─────────────────────────────────────────────────────────────────────────────
def make_slug(name):
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return f"{slug}-net-worth"


def parse_dollar_to_int(val_str):
    """
    Konvertuoja bet koki net worth stringa i integer (pilnas skaicius).
    "$1.2M" -> 1200000
    "$410K" -> 410000
    "$1.5B" -> 1500000000
    "1200000" -> 1200000
    """
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


def int_to_display(num):
    """
    Konvertuoja integer i graziai atrodanti displeja.
    1200000   -> "$1.2M"
    410000    -> "$410K"
    1500000000 -> "$1.5B"
    """
    if num >= 1_000_000_000:
        return f"${num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        val = num / 1_000_000
        return f"${val:.1f}M" if val != int(val) else f"${int(val)}M"
    elif num >= 1_000:
        val = num / 1_000
        return f"${val:.0f}K"
    else:
        return f"${num}"


def clean_net_worth(raw):
    """
    Grazina display formata: "$1.2M", "$410K", "$1.5B"
    Niekada nerodo tik skaiciaus be vieneto.
    """
    num = parse_dollar_to_int(raw)
    if num == 0:
        return raw  # paliekame original jei neparsino
    return int_to_display(num)


def clean_history(raw):
    """
    Konvertuoja i formata su PILNAIS SKAICIAIS:
    "2022:1.2M,2023:1.5M" -> "2022:1200000,2023:1500000"
    Grafiko komponentas tikisi integer reiksmes.
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
        num = parse_dollar_to_int(m.group(2))
        if num > 0:
            entries.append(f"{year}:{num}")
    return ",".join(entries)


def format_sources_html(urls):
    """
    Grazus saltiniai - tik veikianti nuoroda su etikete.
    SVARBU: plain HTML be extra kodo, nes WP custom field rodo ji kaip HTML.
    """
    label_map = {
        "opensecrets.org":  "OpenSecrets",
        "ballotpedia.org":  "Ballotpedia",
        "senate.gov":       "U.S. Senate",
        "house.gov":        "U.S. House of Representatives",
        "forbes.com":       "Forbes",
        "reuters.com":      "Reuters",
        "ap.org":           "Associated Press",
        "apnews.com":       "AP News",
    }
    items = []
    for url in urls:
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        label = label_map.get(domain, domain)
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


# ─────────────────────────────────────────────────────────────────────────────
def post_to_wp(name, data, img_id):
    print("    [4/4] Keliame i WordPress...")

    # Kategorijos - visada 2
    cats = [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP][:2]
    if len(cats) < 2 and 19 not in cats:
        cats.append(19)

    # Net worth - tvarkingas display formatas
    net_worth_raw = data.get("net_worth", "")
    net_worth_display = clean_net_worth(net_worth_raw)
    print(f"    Net worth: {net_worth_raw} -> {net_worth_display}")

    # History - pilni skaiciai
    history_raw = data.get("history", "")
    history_clean = clean_history(history_raw)
    print(f"    History: {history_clean[:80]}...")

    # Source of wealth - tik is leidžiamo saraso, max 2
    matched_sources = [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:2]
    print(f"    Sources: {matched_sources}")

    # Assets - trumpas tekstas
    assets = data.get("assets", "")

    # Saltiniai - grazus HTML
    sources_html = format_sources_html(data.get("urls", []))

    # SEO
    seo_title = data.get("seo_title", f"{name} Net Worth 2026")[:60]
    seo_desc  = f"Discover {name}'s financial profile, career earnings, and wealth breakdown for 2026. Full analysis inside."
    if len(seo_desc) > 155:
        seo_desc = seo_desc[:152] + "..."
    focus_kw  = f"{name} Net Worth 2026"

    payload = {
        "title":          f"{name} Net Worth 2026",
        "slug":           make_slug(name),
        "content":        data["article"],
        "status":         "publish",
        "featured_media": img_id,
        "categories":     cats,
        "acf": {
            "job_title":         data.get("job_title", ""),
            "net_worth":         net_worth_display,
            "net_worth_history": history_clean,
            "source_of_wealth":  matched_sources,
            "main_assets":       assets,
            "sources":           sources_html,
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
def build_prompt(name):
    return f"""You are a financial researcher writing for politiciannetworth.com.

Your task: write a 700-900 word article about {name}'s estimated net worth in 2026.

RESEARCH INSTRUCTIONS:
- Cross-reference at least 3 sources: OpenSecrets financial disclosures, Ballotpedia, and news sources (Forbes, Reuters, AP, Roll Call).
- OpenSecrets URL format: https://www.opensecrets.org/personal-finances/[name]/net-worth
- net_worth: give the BEST estimate in dollars. Format rules:
  * If under $1,000,000: use format like "$750K" or "$410K"  
  * If $1,000,000 to $999,999,999: use format like "$2.3M" or "$15M"
  * If over $1,000,000,000: use format like "$1.2B"
  * NEVER write just "$410" - always include K, M, or B suffix
- history: net worth estimates for years 2022-2026 as FULL INTEGER DOLLAR AMOUNTS (no M/K/B suffix here).
  Format EXACTLY like this: "2022:1200000,2023:1500000,2024:1800000,2025:2000000,2026:2200000"
  If under $1M example: "2022:350000,2023:370000,2024:390000,2025:400000,2026:410000"
- wealth_sources: analyze their background and pick MAX 2 from EXACTLY this list:
  ["Stock Market Investments", "Real Estate Holdings", "Venture Capital", "Professional Law Practice", "Family Inheritance"]
- assets: ONE short sentence. Name only the 1-2 main asset types. Example: "Primary residence and diversified investment portfolio."
- cats: pick 1-2 from: ["US Senate", "US House of Representatives", "Executive Branch", "State Governors", "United States (USA)"]
- urls: exactly 2-3 real URLs from opensecrets.org, ballotpedia.org, senate.gov, or house.gov

ARTICLE STYLE:
- Simple language for general readers. Do NOT sound like AI.
- Add 1-2 interesting lesser-known personal facts.
- Use <h2> and <h3> HTML tags. Bold key numbers with <strong>.
- 700-900 words total.

Return ONLY valid JSON. No markdown fences. No extra text. No trailing commas.

{{"article":"<h2>...</h2><p>...</p>","net_worth":"$2.3M","job_title":"U.S. Senator","history":"2022:1800000,2023:2000000,2024:2100000,2025:2200000,2026:2300000","urls":["https://www.opensecrets.org/personal-finances/{name.replace(' ','_')}/net-worth","https://ballotpedia.org/{name.replace(' ','_')}"],"wealth_sources":["Real Estate Holdings","Stock Market Investments"],"assets":"Primary residence and investment portfolio.","seo_title":"{name} Net Worth 2026","cats":["US Senate","United States (USA)"]}}"""


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
        full_text = res["candidates"][0]["content"]["parts"][0]["text"]
        print(f"    Atsakymo ilgis: {len(full_text)} simboliu")
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
