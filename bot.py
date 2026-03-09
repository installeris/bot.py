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
    "Rich McCormick": ("Rich", "McCormick", "M001216"),
    "Mark Green": ("Mark E.", "Green", "G000590"),
    "Josh Hawley": ("Josh", "Hawley", "H001089"),
    "Darrell Issa": ("Darrell", "Issa", "I000056"),
    "Ron Wyden": ("Ron", "Wyden", "W000779"),
    "Ronald Reagan": ("Ronald", "Reagan", ""),
    "Abraham Lincoln": ("Abraham", "Lincoln", ""),
}

WEALTH_OPTIONS = [
    "Stock Market Investments", "Real Estate Holdings", "Venture Capital",
    "Professional Law Practice", "Family Inheritance", "Book Deals & Royalties",
    "Corporate Board Seats", "Consulting Fees", "Hedge Fund Interests", "Cryptocurrency Assets",
]

# Žinomi net worth skaičiai iš patikimų šaltinių (Forbes/Bloomberg/CelebrityNetWorth 2025-2026)
KNOWN_NET_WORTHS = {
    "Donald Trump":               7300000000,
    "Barack Obama":               70000000,
    "Joe Biden":                  10000000,
    "Kamala Harris":              8000000,
    "Hillary Clinton":            120000000,   # Forbes ~$120M (ne $50M)
    "Bernie Sanders":             3000000,
    "Nancy Pelosi":               260000000,
    "Mike Bloomberg":             110000000000,
    "Elon Musk":                  300000000000,
    "Ali Khamenei":               95000000000,  # Setad empire - visur taip cituojama
    "Michelle Obama":             70000000,
    "George W. Bush":             50000000,
    "Bill Clinton":               120000000,
    "Nikki Haley":                8000000,
    "Ron DeSantis":               2000000,
    "Gavin Newsom":               20000000,
    "Marco Rubio":                2000000,
    "Ted Cruz":                   4000000,
    "Mitt Romney":                300000000,
    "Alexandria Ocasio-Cortez":   200000,
    "Pete Buttigieg":             1500000,
    "Jared Kushner":              800000000,
    "Ivanka Trump":               300000000,
    "Condoleezza Rice":           8000000,
    "Dick Cheney":                90000000,    # ne $150M
    "Al Gore":                    300000000,
    "Tulsi Gabbard":              2000000,     # ne $55M
    "Vivek Ramaswamy":            950000000,
    "Robert F. Kennedy Jr.":      12000000,
    "Liz Cheney":                 8000000,
    "Lindsey Graham":             3000000,
    "Mike Pence":                 3000000,
    "John Kerry":                 250000000,   # Teresa Heinz turtas
    "Mitch McConnell":            35000000,
    "Paul Ryan":                  9000000,
    # Nauji 2026-03-09
    "Rich McCormick":             1000000,    # GA kongresistas, ~$1M
    "Mark Green":                 4000000,    # TN kongresistas, ~$4M
    "Josh Hawley":                2000000,    # MO senatorius, ~$2M
    "Darrell Issa":               500000000,  # CA kongresistas, ~$500M (turtingiausias kongrese)
    "Ron Wyden":                  3000000,    # OR senatorius, ~$3M
    "Ronald Reagan":              13000000,   # mirė su ~$13M
    "Abraham Lincoln":            110000,     # ~$110K istoriškai
}

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
    nw = re.search(r'"net_worth"\s*:\s*"?(\d+)"?', text)
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
        data["urls"] = [u for u in found if is_valid_source_url(u)][:4]
    # FAQ - traukiame visus question/answer porus
    faq_items = re.findall(
        r'\{\s*"question"\s*:\s*"([^"]+)"\s*,\s*"answer"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
        text, re.DOTALL
    )
    if faq_items:
        data["faq"] = [{"question": q, "answer": a.replace('\\"', '"')} for q, a in faq_items]
    if data.get("net_worth"): print(f"    Regex net_worth: {data['net_worth']:,}")
    if data.get("faq"): print(f"    Regex faq: {len(data['faq'])} items")
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
    """Ištraukia JSON tekstą ir grounding URLs iš Gemini atsakymo"""
    if not res or "candidates" not in res:
        return None, None, "no candidates"
    try:
        cand = res["candidates"][0]
        reason = cand.get("finishReason", "UNKNOWN")
        parts = cand.get("content", {}).get("parts", [])

        # Imame tik text parts
        text_parts = [p.get("text", "").strip() for p in parts if "text" in p and p.get("text", "").strip()]
        full_text = "".join(text_parts)
        print(f"    {len(full_text)} simboliu, reason: {reason}, parts: {len(text_parts)}")

        if reason == "MAX_TOKENS":
            return None, None, "MAX_TOKENS"
        if not full_text:
            return None, None, "tuscias atsakymas"

        # Ištraukiame grounding URLs iš metadata (realios Google Search nuorodos)
        grounding_urls = []
        gm = cand.get("groundingMetadata", {})
        all_chunks = gm.get("groundingChunks", [])
        print(f"    groundingChunks: {len(all_chunks)}")

        # webSearchQueries - paieškos užklausos (ne URL, bet matyti kas ieškota)
        wsq = gm.get("webSearchQueries", [])
        if wsq: print(f"    webSearchQueries: {wsq[:3]}")

        # groundingSupports - gali turėti tikrus URL
        supports = gm.get("groundingSupports", [])
        if supports:
            print(f"    groundingSupports[0] keys: {list(supports[0].keys()) if supports else []}")
            print(f"    groundingSupports[0]: {str(supports[0])[:200]}")

        # Visi chunk URL yra vertexaisearch redirect - nerealūs, praleisti
        # Vietoj to imsime iš Gemini JSON "urls" lauko arba generuosime iš webSearchQueries

        # Su google_search Gemini gali grąžinti: [search_results_text, json_text]
        json_text = None
        for part in reversed(text_parts):
            if part.startswith("{"):
                json_text = part
                print(f"    Rastas JSON part ({len(json_text)} chars)")
                break

        if not json_text:
            brace = full_text.find("{")
            if brace != -1:
                json_text = full_text[brace:]
                print(f"    JSON rasta pozicijoje {brace}")
            else:
                return None, grounding_urls, f"nera JSON: {full_text[:150]}"

        return json_text, grounding_urls, None
    except Exception as e:
        return None, None, str(e)


def validate_net_worth(name, net_worth_int):
    """Tikrina ar net_worth realistiškas. Jei per toli nuo žinomo – override."""
    known = KNOWN_NET_WORTHS.get(name)
    if not known:
        return net_worth_int
    # Jei Gemini grąžino 0 arba labai mažą - naudojame žinomą
    if net_worth_int <= 0:
        print(f"    ⚠️ NW=0, naudojame žinomą: {known:,}")
        return known
    ratio = net_worth_int / known
    if ratio > 2.5 or ratio < 0.3:
        print(f"    ⚠️ NW {net_worth_int:,} neatitinka žinomo {known:,} (ratio={ratio:.1f}x) → naudojame žinomą")
        return known
    return net_worth_int


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
    # faq - jei mažiau nei 4, papildome
    faq = data.get("faq", [])
    name_val = data.get("job_title", "this politician")
    nw_val = data.get("net_worth", 0)
    nw_fmt = f"${int(nw_val):,}" if str(nw_val).isdigit() else str(nw_val)
    auto_faq = [
        {"question": "What is their net worth in 2026?",
         "answer": f"Estimated at {nw_fmt} based on public financial disclosures and independent research."},
        {"question": "What are their primary income sources?",
         "answer": data.get("assets", "Multiple income sources including investments and career earnings.")},
        {"question": "How has their wealth changed recently?",
         "answer": "Their net worth has evolved over recent years based on career moves, investments and market conditions."},
        {"question": "What is their most valuable asset?",
         "answer": data.get("assets", "Real estate and investment portfolio represent the bulk of their wealth.")},
    ]
    if not faq:
        print("    ĮSPĖJIMAS: faq tuščias - generuojamas automatiškai")
        data["faq"] = auto_faq
    elif len(faq) < 4:
        print(f"    ĮSPĖJIMAS: faq tik {len(faq)}/4 - papildome")
        needed = [q for q in auto_faq if not any(q["question"] == f["question"] for f in faq)]
        data["faq"] = faq + needed[:4 - len(faq)]
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


def fix_history_last(history, net_worth_int):
    """Paskutinė history reikšmė VISADA = net_worth"""
    if not history or net_worth_int <= 0:
        return history
    parts = history.split(",")
    last = parts[-1]
    if ":" in last:
        year = last.split(":")[0]
        parts[-1] = f"{year}:{net_worth_int}"
    return ",".join(parts)


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
    "vertexaisearch", "googleapis.com", "google.com/search",
    "gstatic.com", "googleusercontent.com", "youtube.com/watch",
    "twitter.com", "x.com/", "facebook.com", "instagram.com", "tiktok.com",
    "reddit.com", "wikipedia.org",
]

TRUSTED_SOURCE_DOMAINS = [
    "forbes.com", "bloomberg.com", "businessinsider.com", "cnbc.com",
    "wsj.com", "nytimes.com", "washingtonpost.com", "thehill.com",
    "politico.com", "reuters.com", "apnews.com", "cnn.com",
    "foxnews.com", "usatoday.com", "marketwatch.com", "investopedia.com",
    "celebritynetworth.com", "moneyinc.com", "wealthygorilla.com",
    "opensecrets.org", "ballotpedia.org", "govtrack.us", "congress.gov",
    "rollcall.com", "thestreet.com", "bankrate.com", "gobankingrates.com",
    "time.com", "theatlantic.com", "nationalreview.com", "slate.com",
]

_URL_CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def is_valid_source_url(url):
    url = url.strip()
    if not url or not url.startswith("http"):
        return False
    for blocked in BLOCKED_URL_PATTERNS:
        if blocked in url:
            return False
    return True

def check_url_alive(url, timeout=10):
    """
    Tikrina ar URL egzistuoja.
    - 200-399 = OK (veikia)
    - 403/429 = botų blokas, bet puslapis EGZISTUOJA → laikome OK
    - 404/410/500+ = neegzistuoja arba klaida → False
    """
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True,
                         headers=_URL_CHECK_HEADERS, stream=True)
        r.close()
        # 403/429 = anti-bot, bet URL realus
        if r.status_code in (403, 429, 401):
            return True
        return r.status_code < 400
    except requests.exceptions.SSLError:
        return False  # SSL klaida - tikrai problema
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        # Timeout gali reikšti kad serveris yra, bet lėtas - laikome True
        return True
    except Exception:
        return False

def search_real_sources(name, needed=4):
    """
    Ieško realių straipsnių apie politiką per DuckDuckGo HTML.
    Grąžina sąrašą veikiančių URL iš patikimų domenų.
    """
    queries = [
        f"{name} net worth 2026",
        f"{name} net worth forbes",
        f"{name} net worth wealth",
    ]
    found = []
    seen_domains = set()

    for query in queries:
        if len(found) >= needed:
            break
        try:
            params = {"q": query, "kl": "us-en"}
            r = requests.get("https://html.duckduckgo.com/html/", params=params,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                             timeout=12)
            if r.status_code != 200:
                continue

            # Ieškom URL iš DDG rezultatų
            raw_urls = re.findall(r'href="(https?://[^"&]+)"', r.text)
            for url in raw_urls:
                if len(found) >= needed:
                    break
                url = url.strip()
                # Filtruojam: tik patikimi domenai
                domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
                if not any(td in domain for td in TRUSTED_SOURCE_DOMAINS):
                    continue
                # Nerodyti DDG pačių puslapių
                if "duckduckgo.com" in url:
                    continue
                # Nerodyti per daug to paties domeno
                base_domain = ".".join(domain.split(".")[-2:])
                if base_domain in seen_domains:
                    continue
                # Tikrinti ar URL gyvas
                print(f"      Tikrinama: {url[:70]}...")
                if check_url_alive(url):
                    found.append(url)
                    seen_domains.add(base_domain)
                    print(f"      ✓ Veikia: {url[:70]}")
                else:
                    print(f"      ✗ Neveikia: {url[:70]}")
            time.sleep(1)  # DDG rate limit
        except Exception as e:
            print(f"      DDG paieška nepavyko: {e}")
            continue

    return found


def verify_and_fix_sources(urls, name=""):
    """
    Patikrina kiekvieną URL ar veikia. Neveikiančius pakeičia per DDG paiešką.
    Grąžina sąrašą iki 4 veikiančių URL.
    """
    print(f"    [sources] Tikriname {len(urls)} URL...")
    verified = []
    bad_count = 0

    for url in urls:
        url = url.strip()
        if not is_valid_source_url(url):
            continue
        if check_url_alive(url):
            verified.append(url)
            print(f"    [sources] ✓ {url[:65]}")
        else:
            bad_count += 1
            print(f"    [sources] ✗ Neveikia: {url[:65]}")

    # Jei trūksta — papildom iš DDG
    needed = 4 - len(verified)
    if needed > 0:
        print(f"    [sources] Ieškome {needed} papildomų šaltinių per DDG...")
        extra = search_real_sources(name, needed=needed + 2)
        # Nerodyti jau turimų domenų
        existing_domains = set(".".join(re.sub(r"https?://(www\.)?","",u).split("/")[0].split(".")[-2:]) for u in verified)
        for u in extra:
            base = ".".join(re.sub(r"https?://(www\.)?","",u).split("/")[0].split(".")[-2:])
            if base not in existing_domains and u not in verified:
                verified.append(u)
                existing_domains.add(base)
            if len(verified) >= 4:
                break

    print(f"    [sources] Galutinis skaičius: {len(verified)} šaltiniai")
    return verified[:4]


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
                    final.append(f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}")
                    quiver_added = True
            continue
        if is_valid_source_url(url) and url not in seen:
            seen.add(url)
            final.append(url)
        if len(final) >= 4:
            break
    if not quiver_added and name in BIOGUIDE_MAP:
        fn, ln, bio = BIOGUIDE_MAP[name]
        if bio:
            ne = urllib.parse.quote(f"{fn} {ln}")
            final.append(f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}")
    return "\n".join(u for u in final if u)


def build_toc_html(article_html):
    """Generuoja Table of Contents iš H2 tagų su anchor ID"""
    import re as _re
    h2s = _re.findall(r'<h2[^>]*>(.*?)</h2>', article_html, _re.IGNORECASE | _re.DOTALL)
    if len(h2s) < 2:
        return article_html, ""

    new_html = article_html
    toc_items = []
    for i, h2_text in enumerate(h2s):
        clean = _re.sub('<[^>]+>', '', h2_text).strip()
        anchor = f"toc-{i+1}-{_re.sub(r'[^a-z0-9]+', '-', clean.lower()).strip('-')[:40]}"
        toc_items.append(f'<li style="margin:0"><a href="#{anchor}" style="color:#2563eb;text-decoration:none">{clean}</a></li>')
        # Pridedame id į H2 tagą
        new_html = new_html.replace(f'<h2>{h2_text}</h2>', f'<h2 id="{anchor}">{h2_text}</h2>', 1)

    toc = (
        '<div class="pnw-toc" style="background:#f8fafc;border:1px solid #e2e8f0;'
        'border-radius:8px;padding:20px 24px;margin:0 0 32px;display:inline-block;min-width:260px;max-width:100%">'
        '<p style="font-weight:700;font-size:15px;margin:0 0 10px;color:#0f172a">Table of Contents</p>'
        '<ol style="margin:0;padding-left:20px;line-height:1.9">'
        + "".join(toc_items)
        + '</ol></div>'
    )
    return new_html, toc


def build_article_css():
    return """<style>
.pnw-article{max-width:780px;font-size:17px;line-height:1.75;color:#1e293b}
.pnw-article p{margin:0 0 20px}
.pnw-article h2{font-size:26px;font-weight:800;color:#0f172a;margin:44px 0 14px;padding-top:8px;border-top:2px solid #e2e8f0;line-height:1.3}
.pnw-article h3{font-size:19px;font-weight:700;color:#0f172a;margin:28px 0 10px}
.pnw-article ul,.pnw-article ol{margin:0 0 20px;padding-left:24px}
.pnw-article li{margin-bottom:6px}
.pnw-article strong{color:#0f172a}
</style>"""


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
        if len(items) >= 4:
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
        f"""ANGLE: {angle}

Create 5 H2 headings that are SPECIFIC to {name} — based on actual facts you find about them.
DO NOT use generic headings like "Income Streams Explained" or "The Number Behind X's Name".
Each H2 must reference something REAL and SPECIFIC about {name}'s finances.

Examples of GOOD specific H2s (these are just examples — create your own based on {name}'s actual story):
- "How Mar-a-Lago Became Trump's Cash Machine" (specific property)
- "The $65M Obama Book Deal That Changed Everything" (specific deal with amount)
- "From $-1M Debt to $8M: Nikki Haley's Fastest Payday" (specific contrast)
- "Why Sanders Owns 3 Houses on a Senator's Salary" (specific counterintuitive fact)
- "The Setad Fund: Khamenei's $95B Shadow Empire" (specific organization)

Structure: opening hook → 5 unique H2 sections based on {name}'s real financial story""",

        f"""ANGLE: {angle}

Write 5 H2 headings that could ONLY apply to {name} — not to any other politician.
Each heading must contain either: a specific dollar amount, a specific asset name, a specific year, or a specific surprising fact.

Structure: opening hook → 5 unique H2 sections. Each section must feel like it belongs in a magazine profile of {name} specifically.""",

        f"""ANGLE: {angle}

Your H2 headings must be so specific that a reader instantly knows this article is about {name}.
Use real names of properties, real dollar figures, real years, real events from {name}'s financial history.

Structure: opening hook → 5 unique H2 sections that tell {name}'s specific financial story from search results.""",
    ]
    structure = random.choice(structures)

    seo_angle = f"Write a completely unique meta description for {name} based on the most surprising or interesting financial fact you find. Include the actual net worth figure. 130-150 characters. No generic templates."

    return f"""You are a financial reporter writing for a general audience. Write a unique, well-researched profile of {name}'s finances.

CRITICAL — NET WORTH ACCURACY:
1. Search RIGHT NOW: "{name} net worth 2026" + "{name} net worth site:forbes.com OR site:bloomberg.com OR site:celebritynetworth.com"
2. Use the figure that appears MOST OFTEN across credible sources. Do not invent or average.
3. Use the MOST COMMONLY REPORTED net worth figure — even if it includes controlled assets:
   - Ali Khamenei: most sources cite ~$95 billion (Setad empire) → net_worth = 95000000000
   - Donald Trump: Forbes 2025 cites ~$7.3B → net_worth = 7300000000
   - Kamala Harris: OpenSecrets/Forbes cite ~$8M → net_worth = 8000000
   - Barack Obama: Celebrity Net Worth cites ~$70M → net_worth = 70000000
4. NEVER invent a figure. If sources conflict, use the LOWER credible estimate.
5. "history" must use REAL verified figures for each year — not a trend line you made up.
   - Search: "{name} net worth [year]" for multiple years if needed
   - Show real declines if they happened
   - Last entry MUST equal net_worth exactly

WRITING RULES:
- Article MUST be 1050-1250 words
- Article MUST have minimum 5 H2 sections
- ONLY verified real facts — no invented numbers
- Use specific numbers: "$47,000 Senate salary" not "congressional salary"
- Include 2+ facts most people genuinely don't know about this person's finances
- Write like a smart friend explaining over coffee — casual, clear, direct
- Short sentences. Plain words. No jargon. If a 12-year-old can't understand it, rewrite it.
- Avoid long paragraphs — max 3 sentences per paragraph
- Be specific: "a $2.1M condo in Georgetown" beats "Washington D.C. property"
- No academic tone, no formal language, no complex sentence structures

BANNED WORDS AND PHRASES — never use these:
"it's worth noting", "delve into", "in conclusion", "moreover", "furthermore",
"navigating", "landscape", "testament to", "shed light on", "pivotal role",
"net worth journey", "financial journey", "in the world of", "underscores",
"showcases", "lucrative", "multifaceted", "demonstrates", "significant",
"notably", "it is important to note", "interestingly", "this allowed him/her to",
"leveraged", "garnered", "accumulated wealth", "amassed", "robust portfolio"

ARTICLE STRUCTURE:
{structure}

TONE:
- Opening: grab attention immediately — a surprising number, a contrast, a little-known fact. Never start with "born in..."
- Mix data with story — numbers need context and human interest
- Avoid corporate/AI-sounding language. Write the way a journalist would actually talk.

FAQ RULES — ALL 4 ARE REQUIRED, no exceptions:
- Each answer must be 2-3 sentences with specific figures
- Questions should be what real people actually Google
- Answers must directly answer the question — no filler

RETURN THIS EXACT JSON STRUCTURE — every field required:
{{
  "article": "<p>Hook...</p><h2>...</h2><p>...</p>... (full HTML, 1050-1250 words, minimum 5 H2 sections)",
  "net_worth": 7300000000,
  "job_title": "Current or most recent official title",
  "history": "2018:2500000000,2020:2800000000,2022:3000000000,2024:4200000000,2025:7300000000,2026:7300000000",
  "wealth_sources": ["Real Estate Holdings", "Book Deals & Royalties", "Stock Market Investments"],
  "assets": "One vivid specific sentence naming actual holdings with dollar values",
  "cats": ["Most Searched Politicians", "one category from list"],
  "urls": ["https://forbes.com/...", "https://opensecrets.org/...", "https://example.com/..."],
  "seo_title": "REQUIRED: '{name} Net Worth 2026: [unique hook]'. Hook = specific fact/contrast/figure from your research. Examples: 'From Debt to $8M', 'Middle-Class Joe\\'s $10M Secret', 'The $7B Truth Nobody Talks About'. FULL title must be 50-70 characters. Count carefully — do not cut off mid-word.",
  "seo_desc": "130-150 char description — must include the net worth figure and one surprising fact",
  "faq": [
    {{"question": "What is {name}'s net worth in 2026?", "answer": "2-3 sentences. Specific figure with source and context."}},
    {{"question": "How did {name} make their money?", "answer": "2-3 sentences. Specific income sources with dollar amounts."}},
    {{"question": "What is {name}'s most valuable asset?", "answer": "2-3 sentences. Specific asset with estimated value."}},
    {{"question": "How has {name}'s wealth changed over time?", "answer": "2-3 sentences. Key turning points with numbers."}}
  ]
}}

CATEGORIES to choose from: {cats_list}
WEALTH SOURCES to choose from (pick 2-4 that genuinely apply): {wealth_list}
SEO DESC ANGLE: {seo_angle}

URLS RULES — CRITICAL:
- "urls" must contain 3-4 REAL, WORKING URLs from credible sources you actually used
- Use: forbes.com, bloomberg.com, opensecrets.org, ballotpedia.org, reuters.com, apnews.com, cnbc.com, businessinsider.com, thestreet.com, washingtonpost.com, nytimes.com, politico.com
- DO NOT use vertexaisearch, google.com, youtube.com, twitter.com, facebook.com, instagram.com, wikipedia.org
- If you cannot find exact article URLs, use the homepage of the source (e.g. "https://www.forbes.com/profile/donald-trump/")
- NEVER leave urls as ["https://...", ...] — always put real URLs

⚠️ OUTPUT RULES — CRITICAL:
1. Start your response with {{ — nothing before it
2. End with }} — nothing after it
3. No markdown, no ```json, no explanations
4. net_worth must be a plain integer (no quotes, no $ sign)
5. All 11 fields are REQUIRED — missing any = failure. FAQ must have exactly 4 items.
6. In the "article" field: NO HTML links or anchor tags. Use only: <p>, <h2>, <h3>, <strong>, <em>, <ul>, <li>. Links break the JSON parser."""


# ─── WORDPRESS ───────────────────────────────────────────────────────────────

def post_to_wp(name, data, img_id, img_url_val, post_id=None):
    print("    [4/4] Keliame i WordPress...")

    cats          = resolve_categories(data.get("cats", []))
    nw_raw        = data.get("net_worth", 0)
    net_worth     = clean_net_worth(nw_raw)
    net_worth_int = int(net_worth) if net_worth.isdigit() else 0
    net_worth_int = validate_net_worth(name, net_worth_int)
    net_worth     = str(net_worth_int) if net_worth_int > 0 else net_worth
    history       = clean_history(data.get("history", ""))
    job_title     = data.get("job_title", "").strip()

    print(f"    NW: {net_worth} | history: {history.count(',') + 1 if history else 0} entries | cats: {cats}")

    seo_desc = data.get("seo_desc", "").strip()
    if len(seo_desc) < 50:
        seo_desc = f"Complete financial profile of {name}: net worth, income sources, assets and wealth history for 2026."
    if len(seo_desc) > 150:
        seo_desc = seo_desc[:150].rsplit(' ', 1)[0]

    faq_items = data.get("faq", [])
    urls      = data.get("urls", [])
    print(f"    URLs gauta: {len(urls)}, po filtro: {len([u for u in urls if is_valid_source_url(u)])}")

    article_html = data.get("article", "")
    article_html = article_html.replace('\\n', ' ').replace('\\r', '').strip()
    # Jei Gemini įdėjo FAQ į article - išimame
    if "pnw-faq" in article_html or "Frequently Asked Questions" in article_html:
        import re as _re
        article_html = _re.sub(r'<div[^>]*pnw-faq[^>]*>.*?</div>\s*', '', article_html, flags=_re.DOTALL)
        article_html = _re.sub(r'<h2[^>]*>[^<]*FAQ[^<]*</h2>.*', '', article_html, flags=_re.DOTALL | _re.IGNORECASE)
    article_with_ids, toc_html = build_toc_html(article_html)

    full_article = (
        build_article_css()
        + toc_html
        + f'<div class="pnw-article">{article_with_ids}</div>'
        + build_faq_html(faq_items)
        + build_references_html(urls)
    )

    post_num     = stats["ok"] + stats["fail"] + stats["skip"] + 1
    schedule_str = (datetime.now(timezone.utc) + timedelta(minutes=124 * post_num)).strftime("%Y-%m-%dT%H:%M:%S")
    print(f"    Suplanuota: {schedule_str}")

    payload = {
        "title":          data.get("seo_title", f"{name} Net Worth 2026"),
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
            "net_worth_history": fix_history_last(history, net_worth_int),
            "source_of_wealth":  [s for s in data.get("wealth_sources", []) if s in WEALTH_OPTIONS][:4],
            "main_assets":       data.get("assets", "").strip(),
            "sources":           format_sources(urls, name),
            "photo_url":         img_url_val or "",
        },
        "meta": {
            "rank_math_title":         data.get("seo_title", f"{name} Net Worth 2026")[:70],
            "rank_math_description":   seo_desc[:150],
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
                src   = str(acf.get("sources", "")).strip()
                title = pdata.get("title", {}).get("rendered", "")
                faq_present   = "pnw-faq-wrap" in art
                toc_present   = "pnw-toc" in art
                title_has_hook = ":" in title  # "Name Net Worth 2026: Hook"
                sources_ok    = src and "http" in src

                missing_info = []
                if not nw or nw == "0":          missing_info.append("net_worth")
                if len(art) < 500:               missing_info.append(f"article({len(art)})")
                if not faq_present:              missing_info.append("FAQ")
                if not toc_present:              missing_info.append("TOC")
                if not sources_ok:               missing_info.append("sources")
                if not title_has_hook:           missing_info.append("title_hook")

                if missing_info:
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
        text, grounding_urls, err = extract_text_from_gemini(res)

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

        # Papildome URLs iš grounding metadata jei JSON urls tuščias/mažas
        if grounding_urls:
            existing = parsed.get("urls", [])
            merged = existing + [u for u in grounding_urls if u not in existing]
            parsed["urls"] = merged[:6]  # max 6, format_sources sutrumpins iki 4

        missing = check_required_fields(parsed)
        if missing:
            print(f"    Trūksta laukų: {', '.join(missing)}")
            continue

        # ── URL VERIFIKACIJA: tikriname ar sources veikia, keičiame blogus ──
        raw_urls = parsed.get("urls", [])
        raw_urls = [u for u in raw_urls if is_valid_source_url(u)]
        parsed["urls"] = verify_and_fix_sources(raw_urls, name=name)

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
