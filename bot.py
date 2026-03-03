import os, requests, json, re, time, sys, urllib.parse, random
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(line_buffering=True)
print("--- BOTAS STARTUOJA v3.0 ---")

GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
AUTHOR_ID   = 3
WP_TIMEOUT  = 30
IMG_TIMEOUT = 20
GEMINI_TIMEOUT = 180

BIOGUIDE_MAP = {
    "Donald Trump": ("Donald J.", "Trump", ""),
    "Barack Obama": ("Barack", "Obama", ""),
    "Joe Biden": ("Joe", "Biden", "B000444"),
    "Kamala Harris": ("Kamala D.", "Harris", "H001075"),
    "Nancy Pelosi": ("Nancy", "Pelosi", "P000197"),
    "Hillary Clinton": ("Hillary Rodham", "Clinton", "C001041"),
    "Bernie Sanders": ("Bernard", "Sanders", "S000033"),
    "Alexandria Ocasio-Cortez": ("Alexandria", "Ocasio-Cortez", "O000172"),
    "Mike Pence": ("Mike", "Pence", "P000587"),
    "Ron DeSantis": ("Ron", "DeSantis", "D000621"),
    "Gavin Newsom": ("Gavin", "Newsom", ""),
    "Nikki Haley": ("Nikki", "Haley", "H001066"),
    "Pete Buttigieg": ("Pete", "Buttigieg", ""),
    "Marco Rubio": ("Marco", "Rubio", "R000595"),
    "Michelle Obama": ("Michelle", "Obama", ""),
    "George W. Bush": ("George W.", "Bush", ""),
    "Bill Clinton": ("Bill", "Clinton", ""),
    "Mike Bloomberg": ("Michael", "Bloomberg", ""),
    "Jared Kushner": ("Jared", "Kushner", ""),
    "Ivanka Trump": ("Ivanka", "Trump", ""),
    "Condoleezza Rice": ("Condoleezza", "Rice", ""),
    "Elon Musk": ("Elon", "Musk", ""),
    "Dick Cheney": ("Dick", "Cheney", ""),
    "Al Gore": ("Al", "Gore", ""),
    "Tulsi Gabbard": ("Tulsi", "Gabbard", "G000571"),
    "Vivek Ramaswamy": ("Vivek", "Ramaswamy", ""),
    "Robert F. Kennedy Jr.": ("Robert F.", "Kennedy", ""),
    "Liz Cheney": ("Liz", "Cheney", "C001109"),
    "John Kerry": ("John", "Kerry", ""),
    "Chris Christie": ("Chris", "Christie", ""),
    "Ted Cruz": ("Ted", "Cruz", "C001098"),
    "Rand Paul": ("Rand", "Paul", "P000603"),
    "Mitt Romney": ("Mitt", "Romney", "R000615"),
    "Adam Schiff": ("Adam B.", "Schiff", "S001150"),
    "Amy Klobuchar": ("Amy", "Klobuchar", "K000367"),
    "Elizabeth Warren": ("Elizabeth", "Warren", "W000817"),
    "Mitch McConnell": ("Mitch", "McConnell", "M000355"),
    "Chuck Schumer": ("Charles E.", "Schumer", "S000148"),
    "Lindsey Graham": ("Lindsey", "Graham", "G000359"),
}

WEALTH_OPTIONS = [
    "Stock Market Investments", "Real Estate Holdings", "Venture Capital",
    "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties",
    "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets",
]

CAT_MAP = {
    "US Senate": 1, "US House of Representatives": 2, "Executive Branch": 3,
    "Former Presidents": 28, "Vice Presidents": 29, "Cabinet Members": 30,
    "First Ladies & Families": 31, "State Governors": 4, "State Senators": 5,
    "House of Commons": 6, "House of Lords": 7, "European Parliament": 18,
    "United States (USA)": 19, "United Kingdom (UK)": 20,
    "Global": 23, "Most Searched Politicians": 27,
}

PARENT_CAT = {
    1: 19, 2: 19, 3: 19, 4: 19, 5: 19, 6: 20, 7: 20,
    28: 3, 29: 3, 30: 3, 31: 3,
    27: None, 18: None, 19: None, 20: None, 23: None,
}

stats = {"ok": 0, "fail": 0, "skip": 0}


# ─── GEMINI ──────────────────────────────────────────────────────────────────

def find_gemini_url():
    preferred = [
        "gemini-2.5-flash", "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash-001", "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite", "gemini-1.5-flash-latest", "gemini-1.5-flash"
    ]
    print("  Gauname modeliu sarasa...")
    available = []
    try:
        res = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}",
            timeout=15).json()
        available = [m["name"].replace("models/", "") for m in res.get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", [])]
        print(f"  Rasti: {available[:5]}")
    except Exception as e:
        print(f"  Klaida: {e}")

    chosen = next((p for p in preferred if p in available), None) or \
             next((m for m in available if "flash" in m.lower()), "gemini-2.5-flash")
    print(f"  Naudosime: {chosen}")

    test_payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    for version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{chosen}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            print(f"  {version} -> {r.status_code}")
            if r.status_code in (200, 400, 403):
                return url
        except Exception as e:
            print(f"  {version} klaida: {e}")

    print("  Naudojame fallback URL")
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"


def call_gemini(prompt, gemini_url, retries=4):
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 32768},
        "tools": [{"google_search": {}}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in
            ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
             "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    for i in range(retries):
        try:
            print(f"    [3/4] Gemini {i+1}/{retries}...")
            t0 = time.time()
            r = requests.post(gemini_url, json=payload, timeout=GEMINI_TIMEOUT)
            print(f"    [3/4] {r.status_code} ({round(time.time()-t0, 1)}s)")
            if r.status_code == 200:
                return r.json()
            elif r.status_code in (429, 503):
                time.sleep(delay); delay = min(delay * 2, 120)
            else:
                print(f"    [3/4] Klaida: {r.text[:200]}"); break
        except requests.exceptions.Timeout:
            print(f"    [3/4] Timeout"); time.sleep(delay); delay = min(delay * 2, 120)
        except Exception as e:
            print(f"    [3/4] {e}"); break
    return None


# ─── JSON PARSING ─────────────────────────────────────────────────────────────

def fix_json_control_chars(text):
    """Pakeičia realius control simbolius į escape sequences string reikšmėse"""
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            result.append('\\r')
        elif in_string and ch == '\t':
            result.append('\\t')
        else:
            result.append(ch)
    return "".join(result)


def fix_html_quotes_in_json(text):
    """
    Pakeičia HTML atributų double quotes į single quotes JSON stringo viduje.
    Pvz: <a href="url"> -> <a href='url'>
    Naudoja state machine kad teisingai atpažintų JSON string ribas.
    """
    result = []
    i = 0
    in_json_string = False
    escape_next = False

    while i < len(text):
        ch = text[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == '\\' and in_json_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue

        if ch == '"':
            if not in_json_string:
                in_json_string = True
                result.append(ch)
                i += 1
                continue
            else:
                # Ar esame HTML tago viduje?
                recent = "".join(result[-300:])
                last_lt = recent.rfind("<")
                last_gt = recent.rfind(">")
                in_html_tag = last_lt > last_gt

                if in_html_tag:
                    # HTML atributo kabutė - pakeičiame į single quote
                    result.append("'")
                    i += 1
                    # Einame iki kitos closing " ir ją irgi pakeičiame
                    while i < len(text) and text[i] not in ('"', '>'):
                        result.append(text[i])
                        i += 1
                    if i < len(text) and text[i] == '"':
                        result.append("'")
                        i += 1
                    continue
                else:
                    # Tikra JSON stringo pabaiga
                    in_json_string = False
                    result.append(ch)
                    i += 1
                    continue

        result.append(ch)
        i += 1

    return "".join(result)


def extract_fields_by_regex(text):
    """Paskutinis fallback - ištraukia laukus regex kai JSON neparse"""
    data = {}
    art = re.search(r'"article"\s*:\s*"(.*?)(?=",\s*"(?:net_worth|job_title))', text, re.DOTALL)
    if art: data["article"] = art.group(1).replace('\\"', '"')
    nw = re.search(r'"net_worth"\s*:\s*(\d{5,})', text)
    if nw: data["net_worth"] = int(nw.group(1))
    jt = re.search(r'"job_title"\s*:\s*"([^"]{1,150})"', text)
    if jt: data["job_title"] = jt.group(1)
    hist = re.search(r'"history"\s*:\s*"([0-9:,]+)"', text)
    if hist: data["history"] = hist.group(1)
    seo_t = re.search(r'"seo_title"\s*:\s*"([^"]{1,80})"', text)
    if seo_t: data["seo_title"] = seo_t.group(1)
    seo_d = re.search(r'"seo_desc"\s*:\s*"([^"]{20,200})"', text)
    if seo_d: data["seo_desc"] = seo_d.group(1)
    assets = re.search(r'"assets"\s*:\s*"([^"]{5,300})"', text)
    if assets: data["assets"] = assets.group(1)
    cats_m = re.search(r'"cats"\s*:\s*\[([^\]]+)\]', text)
    if cats_m: data["cats"] = re.findall(r'"([^"]+)"', cats_m.group(1))
    ws_m = re.search(r'"wealth_sources"\s*:\s*\[([^\]]+)\]', text)
    if ws_m: data["wealth_sources"] = re.findall(r'"([^"]+)"', ws_m.group(1))
    urls_m = re.search(r'"urls"\s*:\s*\[([^\]]*?)\]', text, re.DOTALL)
    if urls_m:
        found = re.findall(r'"(https?://[^"\s]+)"', urls_m.group(1))
        data["urls"] = [u for u in found if is_valid_source_url(u)][:5]
    if data.get("net_worth"): print(f"    Regex net_worth: {data['net_worth']:,}")
    return data if len(data) >= 4 else None


def parse_json(text):
    text = text.strip()

    # DEBUG - išsaugome raw tekstą analizei
    try:
        with open("last_gemini_raw.txt", "w", encoding="utf-8") as dbf:
            dbf.write(text)
    except: pass

    # 1. Fix control chars + tiesiogiai
    text_fixed = fix_json_control_chars(text)
    for t in [text_fixed, text]:
        try: return json.loads(t)
        except: pass

    # 2. Ištraukiame article lauką ir pakeičiame vidines kabutes
    # Gemini rašo: "The Art of the Deal" su kabutėmis article viduje - tai laužo JSON
    tw = text_fixed  # default
    m = re.search(r'\{"article"\s*:\s*"(.*?)",\s*"net_worth"', text_fixed, re.DOTALL)
    if m:
        art_clean = m.group(1).replace('"', "'")
        tw = text_fixed[:m.start(1)] + art_clean + text_fixed[m.end(1):]
        try:
            return json.loads(tw)
        except json.JSONDecodeError as e:
            snippet = tw[max(0, e.pos-30):e.pos+30]
            print(f"    Article fix klaida pos={e.pos}: {repr(snippet)}")

    # 3. Nuo { iki paskutinio }
    s = tw.find("{")
    e = tw.rfind("}")
    if s != -1 and e != -1 and e > s:
        try: return json.loads(tw[s:e+1])
        except: pass

    # 4. Nupjautas JSON - karpome nuo galo, grąžiname geriausią
    if s != -1:
        chunk = tw[s:]
        best = None
        best_fields = 0
        for _ in range(30):
            last_comma = chunk.rfind(",")
            if last_comma == -1: break
            candidate = chunk[:last_comma]
            for closing in ["}", "}}", "]}", "]}}"]:
                try:
                    parsed = json.loads(candidate + closing)
                    nf = len(parsed.keys())
                    if nf > best_fields:
                        best = parsed; best_fields = nf
                    if nf >= 10:
                        print(f"    JSON atkurtas ({nf} laukai)")
                        return parsed
                except: pass
            chunk = candidate
        if best:
            print(f"    JSON iš dalies atkurtas ({best_fields} laukai)")
            return best

    # 5. Paskutinis fallback - regex
    print("    Bandome regex extraction...")
    result = extract_fields_by_regex(text)
    if result:
        print(f"    Regex OK: {len(result)} laukai")
        return result

    raise ValueError(f"Nepavyko parse JSON: {text[:300]}")


def extract_text_from_gemini(res):
    """Ištraukia JSON tekstą iš Gemini atsakymo, grąžina (text, error)"""
    if not res or "candidates" not in res:
        return None, "no candidates"
    try:
        cand = res["candidates"][0]
        reason = cand.get("finishReason", "UNKNOWN")
        parts = cand.get("content", {}).get("parts", [])

        # Imame tik text parts
        text_parts = [p.get("text", "").strip() for p in parts if "text" in p and p.get("text", "").strip()]
        full_text = "".join(text_parts)
        print(f"    {len(full_text)} simboliu, reason: {reason}, parts: {len(text_parts)}")

        if reason == "MAX_TOKENS":
            return None, "MAX_TOKENS"
        if not full_text:
            return None, "tuscias atsakymas"

        # Su google_search Gemini gali grąžinti: [search_results_text, json_text]
        # Ieškome paskutinio part kuris prasideda { - tai bus JSON
        json_text = None
        for part in reversed(text_parts):
            if part.startswith("{"):
                json_text = part
                print(f"    Rastas JSON part ({len(json_text)} chars)")
                break

        # Jei nerado grynojo JSON part - ieškome { visame tekste
        if not json_text:
            brace = full_text.find("{")
            if brace != -1:
                json_text = full_text[brace:]
                print(f"    JSON rasta pozicijoje {brace}")
            else:
                return None, f"nera JSON: {full_text[:150]}"

        return json_text, None
    except Exception as e:
        return None, str(e)


def check_required_fields(data):
    """Tikrina ar visi būtini laukai užpildyti. Grąžina trūkstamų sąrašą."""
    missing = []
    article = data.get("article", "")
    if not article or len(article) < 800:
        missing.append(f"article per trumpas ({len(article)} chars, reikia 800+)")
    nw = str(data.get("net_worth", "")).strip()
    if not nw or nw in ("0", "INT", ""):
        missing.append("net_worth tuščias")
    hist = data.get("history", "")
    if not hist or "INT" in hist or hist.count(":") < 3:
        missing.append("history tuščia arba placeholder")
    if not str(data.get("job_title", "")).strip():
        missing.append("job_title tuščias")
    # faq ir urls - tik įspėjimas, ne blokeris
    faq = data.get("faq", [])
    if not faq:
        print("    ĮSPĖJIMAS: faq tuščias - bus generuojamas automatiškai")
        data["faq"] = [
            {"question": f"What is their net worth in 2026?",
             "answer": f"Estimated at ${int(data.get('net_worth', 0)):,} based on public disclosures."},
            {"question": "What are their primary income sources?",
             "answer": data.get("assets", "Multiple income sources including investments and career earnings.")},
        ]
    urls = data.get("urls", [])
    if not urls:
        print("    ĮSPĖJIMAS: urls tuščias")
    return missing


# ─── IMAGES ──────────────────────────────────────────────────────────────────

def get_wiki_image(name):
    print("    [1/4] Wikipedia nuotrauka...")
    headers = {"User-Agent": "PoliticianNetWorthBot/1.0"}

    def fetch_thumb(title):
        try:
            enc = requests.utils.quote(title)
            res = requests.get(
                f"https://en.wikipedia.org/w/api.php?action=query&titles={enc}&prop=pageimages&format=json&pithumbsize=1200",
                headers=headers, timeout=10).json()
            for pg in res.get("query", {}).get("pages", {}).values():
                if "thumbnail" in pg:
                    return pg["thumbnail"]["source"]
        except: pass
        return None

    thumb = fetch_thumb(name)
    if thumb:
        print("    [1/4] Rasta tiesiogiai"); return thumb

    try:
        enc = requests.utils.quote(name)
        res = requests.get(
            f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={enc}&srlimit=3&format=json",
            headers=headers, timeout=10).json()
        name_parts = [p for p in name.lower().split() if len(p) > 3]
        for result in res.get("query", {}).get("search", []):
            found = result.get("title", "")
            if any(p in found.lower() for p in name_parts):
                thumb = fetch_thumb(found)
                if thumb:
                    print(f"    [1/4] Rasta per Search ({found})"); return thumb
    except Exception as e:
        print(f"    Search klaida: {e}")

    try:
        enc = requests.utils.quote(name)
        res = requests.get(
            f"https://en.wikipedia.org/w/api.php?action=opensearch&search={enc}&limit=3&format=json",
            headers=headers, timeout=10).json()
        for found in res[1]:
            thumb = fetch_thumb(found)
            if thumb:
                print(f"    [1/4] Rasta per OpenSearch ({found})"); return thumb
    except: pass

    print("    [1/4] Nerasta"); return None


def upload_image_to_wp(name, img_url):
    print("    [2/4] Keliame nuotrauka...")
    try:
        img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=IMG_TIMEOUT)
        img_res.raise_for_status()
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/media",
            data=img_res.content,
            headers={"Content-Disposition": f"attachment; filename={name.replace(' ', '_')}.jpg",
                     "Content-Type": "image/jpeg"},
            auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        if res.status_code == 201:
            d = res.json()
            media_url = (d.get("media_details", {}).get("sizes", {})
                          .get("medium", {}).get("source_url") or d.get("source_url", ""))
            print(f"    [2/4] Ikelta (ID:{d['id']})"); return d["id"], media_url
        print(f"    [2/4] Klaida {res.status_code}")
    except requests.exceptions.Timeout:
        print("    [2/4] Timeout")
    except Exception as e:
        print(f"    [2/4] {e}")
    return None, ""


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def parse_to_int(v):
    v = str(v).strip().replace(",", "").replace("$", "")
    try:
        if v.upper().endswith("B"): return int(float(v[:-1]) * 1_000_000_000)
        if v.upper().endswith("M"): return int(float(v[:-1]) * 1_000_000)
        if v.upper().endswith("K"): return int(float(v[:-1]) * 1_000)
        return int(float(v))
    except: return 0


def clean_net_worth(raw):
    n = parse_to_int(raw); return str(n) if n > 0 else "0"


def clean_history(raw):
    if not raw: return ""
    entries = []
    for part in raw.split(","):
        m = re.match(r"(\d{4}):(.+)", part.strip())
        if m:
            n = parse_to_int(m.group(2))
            if n > 0: entries.append(f"{m.group(1)}:{n}")
    return ",".join(entries)


def make_slug(name):
    s = re.sub(r"[^a-z0-9\s-]", "", name.lower().strip())
    s = re.sub(r"\s+", "-", s)
    return f"{s}-net-worth"


def resolve_categories(cat_names):
    cat_ids = {27}  # Visada "Most Searched Politicians"
    for n in cat_names:
        if n in CAT_MAP:
            cid = CAT_MAP[n]; cat_ids.add(cid)
            p = PARENT_CAT.get(cid)
            if p: cat_ids.add(p)
    if len(cat_ids) <= 1: cat_ids.add(19)  # Fallback: United States
    cat_ids.discard(None)
    return list(cat_ids)


BLOCKED_URL_PATTERNS = [
    "vertexaisearch.cloud.google.com", "googleapis.com", "google.com/search",
    "gstatic.com", "googleusercontent.com", "youtube.com/watch",
    "twitter.com", "x.com/", "facebook.com", "instagram.com", "tiktok.com",
]

def is_valid_source_url(url):
    url = url.strip()
    if not url or not url.startswith("http"):
        return False
    for blocked in BLOCKED_URL_PATTERNS:
        if blocked in url:
            return False
    return True

def format_sources(urls, name=""):
    seen = set()
    final = []
    quiver_added = False
    for url in urls:
        url = url.strip()
        if "quiverquant.com" in url:
            if not quiver_added and name in BIOGUIDE_MAP:
                fn, ln, bio = BIOGUIDE_MAP[name]
                if bio:
                    ne = urllib.parse.quote(f"{fn} {ln}")
                    qu = f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}"
                    final.append(qu); quiver_added = True
            continue
        if is_valid_source_url(url) and url not in seen:
            seen.add(url)
            final.append(url)
        if len(final) >= 5:
            break
    if not quiver_added and name in BIOGUIDE_MAP:
        fn, ln, bio = BIOGUIDE_MAP[name]
        if bio:
            ne = urllib.parse.quote(f"{fn} {ln}")
            final.append(f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}")
    return "\n".join(u for u in final if u)


def build_faq_html(faq_items):
    if not faq_items: return ""
    schema = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": i["question"],
                         "acceptedAnswer": {"@type": "Answer", "text": i["answer"]}}
                        for i in faq_items]
    }, ensure_ascii=False)
    items_html = "".join(
        f'<div class="pnw-faq-item"><div class="pnw-faq-q">{i["question"]}</div>'
        f'<div class="pnw-faq-a">{i["answer"]}</div></div>'
        for i in faq_items)
    return f"""
<script type="application/ld+json">{schema}</script>
<div class="pnw-faq-wrap">
<h2 class="pnw-faq-title">Frequently Asked Questions</h2>
{items_html}
</div>
<style>
.pnw-faq-wrap{{max-width:850px;margin:40px auto}}
.pnw-faq-title{{font-size:22px!important;font-weight:800!important;color:#0f172a!important;margin-bottom:20px!important;padding-bottom:10px;border-bottom:2px solid #10b981}}
.pnw-faq-item{{margin-bottom:14px;padding:16px 20px;background:#f8fafc;border-radius:10px;border-left:4px solid #10b981}}
.pnw-faq-q{{font-weight:700;color:#0f172a;font-size:15px;margin-bottom:7px}}
.pnw-faq-a{{color:#475569;font-size:14px;line-height:1.6}}
</style>"""


def build_references_html(urls):
    month_year = datetime.now().strftime("%B %Y")
    label_map = {
        "opensecrets.org": "OpenSecrets – Personal Finances",
        "ballotpedia.org": "Ballotpedia – Political Biography",
        "disclosures-clerk.house.gov": "U.S. House Financial Disclosures",
        "quiverquant.com": "Quiver Quantitative – Congress Trading",
        "senate.gov": "U.S. Senate – Official Profile",
        "house.gov": "U.S. House – Official Profile",
        "forbes.com": "Forbes – Wealth Estimate",
        "reuters.com": "Reuters", "apnews.com": "AP News",
        "celebrity": "Celebrity Net Worth",
        "cnbc.com": "CNBC", "businessinsider.com": "Business Insider",
        "thestreet.com": "The Street", "washingtonpost.com": "Washington Post",
    }
    items = []
    seen_domains = set()
    for url in urls:
        if not is_valid_source_url(url):
            continue
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        label = next((v for k, v in label_map.items() if k in domain), domain)
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')
        if len(items) >= 5:
            break
    if not items:
        return ""
    return f"""
<hr style="margin:40px 0 20px">
<div class="references-section">
<h2>References &amp; Sources</h2>
<p><em>Last updated: {month_year}. Net worth estimates are based on public financial disclosures and independent research.</em></p>
<ul>{"".join(items)}</ul>
</div>"""


def check_post_exists(name):
    slug = make_slug(name)
    try:
        res = requests.get(f"{WP_BASE_URL}/wp/v2/posts",
                           params={"slug": slug, "status": "any"},
                           auth=(WP_USER, WP_PASS), timeout=15)
        if res.status_code == 200 and res.json():
            e = res.json()[0]; return True, e.get("id"), e.get("status")
    except Exception as ex:
        print(f"  check_post_exists klaida: {ex}")
    return False, None, None


# ─── PROMPT ──────────────────────────────────────────────────────────────────

def build_prompt(name):
    cats_list = ", ".join(CAT_MAP.keys())
    wealth_list = ", ".join(WEALTH_OPTIONS)

    angles = [
        f"Focus on the most CONTROVERSIAL or SURPRISING aspect of {name}'s wealth.",
        f"Focus on how {name}'s wealth CHANGED dramatically — a big gain, loss, or unexpected turn.",
        f"Focus on the CONTRAST between {name}'s public image and their actual financial reality.",
        f"Focus on {name}'s BUSINESS DEALS and investments outside politics — money most people overlook.",
        f"Focus on how {name} BUILT wealth before entering politics — the foundation most don't know.",
        f"Focus on {name}'s REAL ESTATE or major physical assets — make it tangible.",
        f"Focus on how {name}'s net worth compares to political peers — shockingly high or surprisingly low?",
    ]
    angle = random.choice(angles)

    structures = [
        f"""- Opening hook: {angle}
- <h2>Early Life and the Road to Politics</h2> — pre-political career, education, first money moves
- <h2>How {name} Built Their Fortune</h2> — income sources with specific dollar amounts
- <h2>Real Estate, Stocks and Key Investments</h2> — named holdings, addresses, ticker symbols
- <h2>Net Worth Timeline: The Numbers Over the Years</h2> — changes with context, explain spikes/drops
- <h2>Financial Controversies and Lesser-Known Facts</h2> — interesting facts most people don't know""",

        f"""- Opening hook: {angle}
- <h2>The Surprising Truth About {name}'s Money</h2> — headline fact, counterintuitive detail
- <h2>Income Streams Explained</h2> — every source: salary, books, speeches, businesses
- <h2>What {name} Actually Owns</h2> — property, stocks, businesses by name and value
- <h2>Wealth Growth: Year by Year</h2> — what changed and why, major financial events
- <h2>Background: Before the Spotlight</h2> — pre-fame financial life and career origins""",

        f"""- Opening hook: {angle}
- <h2>Just How Rich Is {name}?</h2> — net worth figure with source, comparison to peers
- <h2>Where the Money Comes From</h2> — income breakdown with actual dollar amounts per source
- <h2>The Portfolio: Investments and Property</h2> — specific assets, locations, estimated values
- <h2>A Decade of Wealth: How the Numbers Moved</h2> — historical context with real figures
- <h2>The Story Behind the Money</h2> — career origins, key financial decisions""",
    ]
    structure = random.choice(structures)

    seo_angles = [
        f"How did {name} actually make their money? Full breakdown of income, investments and net worth 2026.",
        f"Surprising facts about {name}'s net worth in 2026 — where it came from and how it grew.",
        f"Complete financial profile: {name}'s salary, assets, investments and estimated net worth for 2026.",
        f"The real story behind {name}'s fortune — verified sources, key assets and the numbers.",
        f"What is {name} really worth? Full breakdown of income sources, property and net worth 2026.",
    ]
    seo_angle = random.choice(seo_angles)

    return f"""You are an investigative financial journalist. Write a deeply researched, unique financial profile of {name} for a general audience.

CRITICAL — NET WORTH ACCURACY: Use your Google Search tool RIGHT NOW to find the latest 2025-2026 net worth for {name}. Search: "{name} net worth 2025 Forbes". Training data is outdated — always use search results for the actual figure. Net worths change drastically (e.g. Trump went from $3B to $7B+ after Truth Social IPO).

RULES:
- Article MUST be 950-1150 words
- ONLY verified real facts — no invented numbers
- BANNED phrases: "it's worth noting", "delve into", "in conclusion", "moreover", "furthermore", "navigating", "landscape", "testament to", "shed light on", "pivotal role", "net worth journey", "financial journey", "in the world of"
- Vary sentence length — short punchy sentences mixed with longer analytical ones
- Use specific sourced numbers: "$47,000 Senate salary" not "congressional salary"
- Include 2+ facts most people genuinely don't know about this person's finances
- Write conversationally — smart friend explaining, not Wikipedia

ARTICLE STRUCTURE:
{structure}

TONE:
- Opening: grab attention immediately, no "born in..." intros
- Mix data with story — numbers need context
- Be specific: "a $2.1M condo in Georgetown" beats "Washington D.C. property"

RETURN THIS EXACT JSON STRUCTURE — every field required:
{{
  "article": "<p>Hook...</p><h2>...</h2><p>...</p>... (full HTML, 950-1150 words)",
  "net_worth": 4200000,
  "job_title": "Current or most recent official title",
  "history": "2022:3000000,2023:3500000,2024:3800000,2025:4000000,2026:4200000",
  "wealth_sources": ["Real Estate Holdings", "Book Deals & Royalties"],
  "assets": "One vivid specific sentence naming actual holdings with values",
  "cats": ["Most Searched Politicians", "one category from list"],
  "urls": ["https://...", "https://...", "https://..."],
  "seo_title": "{name} Net Worth 2026",
  "seo_desc": "130-155 char unique description",
  "faq": [
    {{"question": "What is {name}'s net worth in 2026?", "answer": "Direct answer with figure and source."}},
    {{"question": "How did {name} make their money?", "answer": "Specific income sources with amounts."}},
    {{"question": "What is {name}'s most valuable asset?", "answer": "Specific asset with estimated value."}},
    {{"question": "How has {name}'s net worth changed recently?", "answer": "Recent change with context."}}
  ]
}}

CATEGORIES to choose from: {cats_list}
WEALTH SOURCES to choose from: {wealth_list}
SEO DESC ANGLE: {seo_angle}

⚠️ OUTPUT RULES — CRITICAL:
1. Start your response with {{ — nothing before it
2. End with }} — nothing after it
3. No markdown, no ```json, no explanations
4. net_worth must be a plain integer (no quotes, no $ sign)
5. All 11 fields are REQUIRED — missing any field = failure
6. In the "article" HTML field: DO NOT use any HTML links or anchor tags at all. No <a href=...> tags. Plain HTML only: <p>, <h2>, <h3>, <strong>, <em>, <ul>, <li>. Links break the JSON parser."""


# ─── WORDPRESS ───────────────────────────────────────────────────────────────

def post_to_wp(name, data, img_id, img_url_val, post_id=None):
    print("    [4/4] Keliame i WordPress...")

    cats          = resolve_categories(data.get("cats", []))
    nw_raw        = data.get("net_worth", 0)
    net_worth     = clean_net_worth(nw_raw)
    net_worth_int = int(net_worth) if net_worth.isdigit() else 0
    history       = clean_history(data.get("history", ""))
    job_title     = data.get("job_title", "").strip()

    # Sinchronizuojame: paskutinė history reikšmė = net_worth
    if history and net_worth_int > 0:
        h_parts = history.split(",")
        last_year = h_parts[-1].split(":")[0] if ":" in h_parts[-1] else "2026"
        h_parts[-1] = f"{last_year}:{net_worth_int}"
        history = ",".join(h_parts)

    print(f"    NW: {net_worth} | history: {history.count(',') + 1 if history else 0} entries | cats: {cats}")

    seo_desc = data.get("seo_desc", "").strip()
    if len(seo_desc) < 50:
        seo_desc = f"Complete financial profile of {name}: net worth, income sources, assets and wealth history for 2026."

    faq_items = data.get("faq", [])
    urls      = data.get("urls", [])

    full_article = (
        data.get("article", "")
        + build_faq_html(faq_items)
        + build_references_html(urls)
    )

    post_num     = stats["ok"] + stats["fail"] + stats["skip"] + 1
    schedule_str = (datetime.now(timezone.utc) + timedelta(minutes=124 * post_num)).strftime("%Y-%m-%dT%H:%M:%S")
    print(f"    Suplanuota: {schedule_str}")

    payload = {
        "title":          f"{name} Net Worth 2026",
        "slug":           make_slug(name),
        "content":        full_article,
        "status":         "future",
        "date":           schedule_str,
        "author":         AUTHOR_ID,
        "featured_media": img_id,
        "categories":     cats,
        "acf": {
            "job_title":         job_title,
            "net_worth":         net_worth,
            "net_worth_history": history,
            "source_of_wealth":  [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:4],
            "main_assets":       data.get("assets", "").strip(),
            "sources":           format_sources(urls, name),
            "photo_url":         img_url_val or "",
        },
        "meta": {
            "rank_math_title":         f"{name} Net Worth 2026",
            "rank_math_description":   seo_desc[:160],
            "rank_math_focus_keyword": f"{name} Net Worth 2026",
        }
    }

    # Jei update - naudojame PATCH, jei naujas - POST
    for attempt in range(3):
        try:
            if post_id:
                r = requests.post(f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
                                  json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
                success = r.status_code == 200
            else:
                r = requests.post(f"{WP_BASE_URL}/wp/v2/posts",
                                  json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
                success = r.status_code in (201, 202)

            if success:
                link = r.json().get("link", "")
                action = "ATNAUJINTA" if post_id else "IKELTA"
                print(f"    [4/4] {action}! {link}")
                with open("processed.txt", "a") as pf: pf.write(name + "\n")
                return True
            elif r.status_code in (500, 502, 503, 504):
                print(f"    [4/4] Server klaida {r.status_code}, bandome dar...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"    [4/4] Klaida {r.status_code}: {r.text[:400]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] Timeout, bandome dar..."); time.sleep(15)
        except Exception as e:
            print(f"    [4/4] {e}"); return False
    return False


# ─── MAIN BOT LOGIC ───────────────────────────────────────────────────────────

def run_bot(name, gemini_url):
    num = stats["ok"] + stats["fail"] + stats["skip"] + 1
    print(f"\n{'='*55}\n[{num}] {name}\n{'='*55}")

    # Tikriname ar postas jau egzistuoja
    exists, post_id, post_status = check_post_exists(name)
    if exists:
        # Tikriname ar reikia update (tušti ACF laukai ar per trumpas straipsnis)
        needs_update = False
        try:
            pr = requests.get(f"{WP_BASE_URL}/wp/v2/posts/{post_id}?acf_format=standard",
                              auth=(WP_USER, WP_PASS), timeout=15)
            if pr.status_code == 200:
                pdata = pr.json()
                acf   = pdata.get("acf", {})
                nw    = str(acf.get("net_worth", "")).strip()
                art   = pdata.get("content", {}).get("rendered", "")
                faq_present = "pnw-faq-wrap" in art
                if not nw or nw == "0" or len(art) < 500 or not faq_present:
                    missing_info = []
                    if not nw or nw == "0": missing_info.append("net_worth")
                    if len(art) < 500: missing_info.append(f"article ({len(art)} chars)")
                    if not faq_present: missing_info.append("FAQ")
                    print(f"  ID:{post_id} – trūksta: {', '.join(missing_info)} → ATNAUJINSIME")
                    needs_update = True
                else:
                    print(f"  PRALEIDŽIAMA (ID:{post_id}, {post_status}, NW:{nw})")
                    stats["skip"] += 1; return
        except Exception as ex:
            print(f"  Klaida tikrinant postą: {ex}")
            print(f"  PRALEIDŽIAMA (ID:{post_id})")
            stats["skip"] += 1; return
        if not needs_update:
            stats["skip"] += 1; return

    # Nuotrauka
    img_id, img_url_val = None, ""
    wiki_img = get_wiki_image(name)
    if wiki_img:
        img_id, img_url_val = upload_image_to_wp(name, wiki_img)

    # Gemini – iki 3 bandymų kol gauti pilnus duomenis
    data = None
    for attempt in range(3):
        if attempt > 0:
            print(f"    ↻ Pakartojame Gemini ({attempt+1}/3) — trūko laukų, bandome iš naujo...")
            time.sleep(10)

        res = call_gemini(build_prompt(name), gemini_url)
        text, err = extract_text_from_gemini(res)

        if err:
            print(f"    Gemini klaida: {err}")
            if err == "MAX_TOKENS":
                stats["fail"] += 1
                with open("failed.txt", "a") as f: f.write(name + "\n")
                return
            continue

        try:
            parsed = parse_json(text)
        except Exception as e:
            print(f"    JSON parse klaida: {e}")
            continue

        missing = check_required_fields(parsed)
        if missing:
            print(f"    Trūksta laukų: {', '.join(missing)}")
            continue

        # Visi laukai OK
        print(f"    ✓ Visi laukai užpildyti")
        data = parsed
        break

    if data is None:
        print(f"  NEPAVYKO gauti pilnų duomenų po 3 bandymų → failed.txt")
        stats["fail"] += 1
        with open("failed.txt", "a") as f: f.write(name + "\n")
        return

    ok = post_to_wp(name, data, img_id, img_url_val, post_id=post_id if exists else None)
    if ok:
        stats["ok"] += 1; print(f"  ✓ SĖKMĖ: {name}")
    else:
        stats["fail"] += 1; print(f"  ✗ NEPAVYKO: {name}")
        with open("failed.txt", "a") as f: f.write(name + "\n")


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists("names.txt"):
        print("KLAIDA: names.txt nerastas!"); sys.exit(1)

    gemini_url = find_gemini_url()
    print(f"Gemini paruoštas.\n")

    with open("names.txt") as f:
        names = [n.strip() for n in f if n.strip()]
    print(f"Vardai: {len(names)}\n")

    for i, name in enumerate(names):
        run_bot(name, gemini_url)
        if i < len(names) - 1:
            pause = 20 if (i + 1) % 10 == 0 else 8
            print(f"\nPauzė {pause}s (ok={stats['ok']} fail={stats['fail']} skip={stats['skip']})")
            time.sleep(pause)

    print(f"\n{'='*55}")
    print(f"REZULTATAI: ok={stats['ok']} | fail={stats['fail']} | skip={stats['skip']}")
    print(f"{'='*55}")
