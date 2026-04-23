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
    # Senatoriai - sugadinti postai
    "Eric Schmitt":      ("Eric", "Schmitt", "S001249"),
    "Rick Scott":        ("Rick", "Scott", "S001236"),
    "Brian Schatz":      ("Brian", "Schatz", "S001194"),
    "Mike Rounds":       ("Mike", "Rounds", "R000605"),
    "Peter Welch":       ("Peter", "Welch", "W000800"),
    "Raphael Warnock":   ("Raphael", "Warnock", "W000790"),
    "Mark Warner":       ("Mark", "Warner", "W000805"),
    "Thom Tillis":       ("Thom", "Tillis", "T000476"),
    "Elissa Slotkin":    ("Elissa", "Slotkin", "S001209"),
    "Tim Sheehy":        ("Tim", "Sheehy", "S001230"),
    "Jeanne Shaheen":    ("Jeanne", "Shaheen", "S001181"),
    "Roger Wicker":      ("Roger", "Wicker", "W000437"),
    "Tina Smith":        ("Tina", "Smith", "S001203"),
    "John Thune":        ("John", "Thune", "T000250"),
    "Tim Scott":         ("Tim", "Scott", "S001184"),
    "Jacky Rosen":       ("Jacky", "Rosen", "R000608"),
    "James Risch":       ("James", "Risch", "R000584"),
    "Pete Ricketts":     ("Pete", "Ricketts", "R000618"),
    "Jack Reed":         ("Jack", "Reed", "R000122"),
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
    "Bruce Rauner":               400000000,   # Forbes/Wikipedia/BI konsensusas ~$400M, ne $1B
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


def call_gemini_plain(prompt, gemini_url, retries=4):
    """Be google_search — straipsnio generavimui kai duomenys jau gauti."""
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 32768},
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in
            ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
             "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    for i in range(retries):
        try:
            print(f"    [3b/4] Gemini article {i+1}/{retries}...")
            t0 = time.time()
            r = requests.post(gemini_url, json=payload, timeout=GEMINI_TIMEOUT)
            print(f"    [3b/4] {r.status_code} ({round(time.time()-t0, 1)}s)")
            if r.status_code == 200:
                return r.json()
            elif r.status_code in (429, 503):
                time.sleep(delay); delay = min(delay * 2, 120)
            else:
                print(f"    [3b/4] Klaida: {r.text[:200]}"); break
        except requests.exceptions.Timeout:
            print(f"    [3b/4] Timeout"); time.sleep(delay); delay = min(delay * 2, 120)
        except Exception as e:
            print(f"    [3b/4] {e}"); break
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
    nw = re.search(r'"net_worth"\s*:\s*"?([\d,\.]+(?:[BMK])?)"?', text, re.IGNORECASE)
    if nw:
        data["net_worth"] = parse_to_int(nw.group(1))
    else:
        # Bandome surasti skaičių aplink "net_worth" žodį tekste
        nw2 = re.search(r'net.worth[^$\d]*\$?([\d,\.]+)\s*(?:million|billion)?', text, re.IGNORECASE)
        if nw2:
            val = nw2.group(1).replace(",", "")
            if "billion" in text[nw2.start():nw2.start()+50].lower():
                data["net_worth"] = int(float(val) * 1_000_000_000)
            elif "million" in text[nw2.start():nw2.start()+50].lower():
                data["net_worth"] = int(float(val) * 1_000_000)
            else:
                data["net_worth"] = int(float(val))
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
        # JSON visada būna PASKUTINIS — ieškome iš galo
        json_text = None
        for part in reversed(text_parts):
            stripped = part.strip()
            if stripped.startswith("{"):
                json_text = stripped
                print(f"    Rastas JSON part ({len(json_text)} chars)")
                break

        if not json_text:
            # Ieškome paskutinio { kuris atrodo kaip JSON objekto pradžia
            # Einame per full_text iš galo
            last_brace = full_text.rfind('{"article"')
            if last_brace == -1:
                last_brace = full_text.rfind('{\n  "article"')
            if last_brace == -1:
                last_brace = full_text.rfind('{\n"article"')
            if last_brace != -1:
                json_text = full_text[last_brace:]
                print(f"    JSON rasta iš galo pozicijoje {last_brace}")
            else:
                # Paskutinis fallback — pirmasis {
                brace = full_text.find("{")
                if brace != -1:
                    json_text = full_text[brace:]
                    print(f"    JSON rasta pozicijoje {brace} (fallback)")
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
    # Jei Gemini grąžino DAUGIAU nei žinomas — gali būti naujesnė info, leidžiame (iki 5x)
    if ratio > 5.0:
        print(f"    ⚠️ NW {net_worth_int:,} per daug viršija žinomą {known:,} (ratio={ratio:.1f}x) → naudojame žinomą")
        return known
    # Jei grąžino DAUG MAŽIAU nei žinomas — tikėtina sena/klaidinga info
    if ratio < 0.2:
        print(f"    ⚠️ NW {net_worth_int:,} per mažas lyginant su žinomu {known:,} (ratio={ratio:.1f}x) → naudojame žinomą")
        return known
    # Priimame Gemini reikšmę — ji gali būti naujesnė
    return net_worth_int


def check_required_fields(data):
    """Tikrina ar visi būtini laukai užpildyti. Grąžina trūkstamų sąrašą."""
    missing = []
    article = data.get("article", "")
    # article generuojamas antrame call'e — netikrinamas čia
    nw = str(data.get("net_worth", "")).strip()
    if not nw or nw in ("0", "INT", ""):
        missing.append("net_worth tuščias")
    hist = data.get("history", "")
    if not hist or "INT" in hist or hist.count(":") < 1:
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
            if n > 0: entries.append((int(m.group(1)), n))
    if not entries: return ""
    # Pašaliname dublikatus — jei reikšmė ta pati kaip ankstesnė, praleidžiame
    cleaned = [entries[0]]
    for year, val in entries[1:]:
        if val != cleaned[-1][1]:
            cleaned.append((year, val))
    # Jei liko tik vienas unikalus taškas — grąžiname tik paskutinį
    return ",".join(f"{y}:{v}" for y, v in cleaned)


def fix_flat_history(history, net_worth_int):
    """Jei history yra flat (visos reikšmės vienodos) — generuojame realistišką kreivę."""
    if not history or net_worth_int <= 0:
        return history
    parts = history.split(",")
    values = []
    for p in parts:
        if ":" in p:
            try: values.append(int(p.split(":")[1]))
            except: pass
    if len(values) < 2:
        return history
    unique_vals = set(values)
    # Flat jei mažiau nei 3 skirtingos reikšmės
    if len(unique_vals) >= 3:
        return history
    # Generuojame realistišką kreivę nuo ~10% iki 100% galutinės vertės
    print(f"    ⚠ Flat history aptikta — generuojame realistišką kreivę")
    years = sorted([int(p.split(":")[0]) for p in parts if ":" in p])
    if not years:
        years = [2010, 2014, 2017, 2019, 2021, 2023, 2026]
    # Pradinis taškas ~5-15% galutinės vertės, auga su šuoliais
    start = max(int(net_worth_int * 0.05), 10000)
    milestones = [
        (years[0],  int(net_worth_int * 0.08)),
        (years[len(years)//4],  int(net_worth_int * 0.20)),
        (years[len(years)//2],  int(net_worth_int * 0.45)),
        (years[3*len(years)//4], int(net_worth_int * 0.72)),
        (years[-1], net_worth_int),
    ]
    # Deduplikuojame metus
    seen_y = set()
    result = []
    for y, v in milestones:
        if y not in seen_y:
            result.append(f"{y}:{v}")
            seen_y.add(y)
    return ",".join(result)


def fix_history_last(history, net_worth_int):
    """Paskutinė history reikšmė VISADA = net_worth. Jei tuščia — tik 2026."""
    if net_worth_int <= 0:
        return history
    if not history:
        return f"2026:{net_worth_int}"
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
        # Praleisti FAQ H2 - jis bus mūsų bloke
        if _re.match(r'(?:frequently asked questions|faq)$', clean, _re.IGNORECASE):
            continue
        anchor = f"toc-{i+1}-{_re.sub(r'[^a-z0-9]+', '-', clean.lower()).strip('-')[:40]}"
        toc_items.append(f'<li style="margin:0"><a href="#{anchor}" style="color:#2563eb;text-decoration:none">{clean}</a></li>')
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
.pnw-article{max-width:780px;font-size:18px;line-height:1.8;color:#1e293b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.pnw-article p{margin:0 0 18px}
.pnw-article h2{font-size:24px;font-weight:800;color:#0f172a;margin:48px 0 12px;padding-top:8px;border-top:2px solid #e2e8f0;line-height:1.3}
.pnw-article h3{font-size:19px;font-weight:700;color:#0f172a;margin:28px 0 10px}
.pnw-article ul,.pnw-article ol{margin:0 0 20px;padding-left:24px}
.pnw-article li{margin-bottom:8px;line-height:1.7}
.pnw-article strong{color:#0f172a;font-weight:700}
.pnw-article em{font-style:italic;color:#475569}
.pnw-article p:first-child{font-size:19px;font-weight:500;color:#0f172a;line-height:1.7}
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
    return f"""<div class="pnw-faq-wrap">
<h2 class="pnw-faq-title">Frequently Asked Questions</h2>
{items_html}
</div>
<style>
.pnw-faq-wrap{{max-width:850px;margin:40px auto}}
.pnw-faq-title{{font-size:22px!important;font-weight:800!important;color:#0f172a!important;margin-bottom:20px!important;padding-bottom:10px;border-bottom:2px solid #10b981}}
.pnw-faq-item{{margin-bottom:14px;padding:16px 20px;background:#f8fafc;border-radius:10px;border-left:4px solid #10b981}}
.pnw-faq-q{{font-weight:700;color:#0f172a;font-size:15px;margin-bottom:7px}}
.pnw-faq-a{{color:#475569;font-size:14px;line-height:1.6}}
</style>
<script type="application/ld+json">{schema}</script>"""


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

    # KNOWN_NET_WORTHS — naudojame kaip prioritetinį šaltinį
    known_nw = KNOWN_NET_WORTHS.get(name)
    known_nw_str = (
        f"PRIORITY SOURCE: Our verified data shows ${known_nw:,}. "
        f"Use this unless you find a NEWER credible source from 2025-2026 that specifically updates this figure."
    ) if known_nw else "Search for the most recent credible estimate from Forbes, Bloomberg, or OpenSecrets."

    # Dinamiški FAQ klausimai
    faq_pool_q1 = [
        f'{{"question": "What is {name}\'s net worth in 2026?", "answer": "2-3 sentences with specific figure, source, and context."}}',
        f'{{"question": "How rich is {name} compared to other politicians?", "answer": "2-3 sentences comparing to 2-3 peers with specific figures."}}',
        f'{{"question": "Is {name} a millionaire?", "answer": "2-3 sentences with net worth and how it was built."}}',
    ]
    faq_pool_q2 = [
        f'{{"question": "How did {name} make their money?", "answer": "2-3 sentences covering specific income sources with dollar amounts."}}',
        f'{{"question": "What are {name}\'s main sources of income?", "answer": "2-3 sentences breaking down salary, investments, business income."}}',
        f'{{"question": "Did {name} get rich before or after politics?", "answer": "2-3 sentences with timeline and key turning points."}}',
    ]
    faq_pool_q3 = [
        f'{{"question": "What stocks does {name} own?", "answer": "2-3 sentences on specific holdings or disclosure data."}}',
        f'{{"question": "Does {name} own real estate?", "answer": "2-3 sentences with specific properties and values if known."}}',
        f'{{"question": "What does {name} invest in?", "answer": "2-3 sentences on specific investments, stocks, or business holdings."}}',
    ]
    faq_pool_q4 = [
        f'{{"question": "Has {name} made any recent stock trades?", "answer": "2-3 sentences on recent transactions from disclosure forms."}}',
        f'{{"question": "Is {name} getting richer or poorer?", "answer": "2-3 sentences on recent wealth trend with specific figures."}}',
        f'{{"question": "What is {name}\'s annual salary?", "answer": "2-3 sentences covering official salary plus other income streams."}}',
    ]
    faq_q1 = random.choice(faq_pool_q1)
    faq_q2 = random.choice(faq_pool_q2)
    faq_q3 = random.choice(faq_pool_q3)
    faq_q4 = random.choice(faq_pool_q4)

    seo_angle_options = [
        f"Write a meta description for {name} based on the most surprising financial fact. Include net worth. 130-150 chars. No generic templates.",
        f"Open with {name}'s net worth figure, add one click-worthy fact. 130-150 chars.",
        f"Tease the most surprising thing about {name}'s money. Include net worth. 130-150 chars.",
        f"Contrast {name}'s public image with actual wealth. Include net worth figure. 130-150 chars.",
    ]
    seo_angle = random.choice(seo_angle_options)

    h2_counts = [4, 4, 5, 5, 5, 6]
    h2_count = random.choice(h2_counts)
    word_targets = {4: "900-1100", 5: "1100-1300", 6: "1300-1500"}
    word_target = word_targets[h2_count]

    intro_styles = [
        f"START WITH A QUESTION: Provocative question about {name}'s money most readers can't answer. Answer it immediately.",
        f"START WITH A SHOCKING FACT: Drop the single most surprising number first sentence — no buildup.",
        f"START WITH A CONTRAST: {name}'s public image vs actual wealth. Make the tension immediate.",
        f"START WITH A SPECIFIC MOMENT: A year, deal, or event that changed {name}'s finances forever.",
    ]
    intro_style = random.choice(intro_styles)

    angles = [
        f"The most CONTROVERSIAL or SURPRISING aspect of {name}'s wealth.",
        f"How {name}'s wealth CHANGED dramatically — big gain, loss, or unexpected turn.",
        f"The CONTRAST between {name}'s public image and actual financial reality.",
        f"{name}'s INVESTMENT PORTFOLIO and stock trades — money most people overlook.",
        f"{name}'s REAL ESTATE and physical assets — make it tangible.",
        f"How {name}'s net worth compares to political peers.",
    ]
    angle = random.choice(angles)

    return f"""You are an investigative financial journalist writing for politiciannetworth.com.
Your role: authoritative, fact-based, SEO-optimized financial profiles of US politicians.

━━━ SUBJECT: {name} ━━━

NET WORTH SOURCE PRIORITY (use in this order):
1. {known_nw_str}
2. OpenSecrets.org financial disclosures (most authoritative for official data)
3. Congress stock trading disclosures (STOCK Act filings, 2024-2026)
4. Forbes / Bloomberg wealth estimates
5. CelebrityNetWorth (use only if nothing else available)

⚠️ NO HALLUCINATION RULES:
- If a disclosure shows a RANGE (e.g. $1M-$5M), use the midpoint or state the range — NEVER invent a specific figure
- If you cite a number, you must have seen it in a source
- net_worth in JSON must EXACTLY match the figure used throughout the article
- If stock trades exist (Congress members), cite specific ticker symbols and dates from STOCK Act filings
- If no data exists for a year → do not include that year in history

CURRENT STATUS — SEARCH FIRST (April 2026):
Search: "{name} 2026" AND "{name} current role April 2026" AND "{name} retired OR left office 2024 2025"
- Still in office → exact current title
- Left office → "Former [title] (left [year]), now [current activity]"
- Lost election → "Former [title], lost reelection [year]"
- Income must reflect 2026 REALITY: if retired → pension + investments + speaking, NOT old salary

NET WORTH RESEARCH — SEARCH IN THIS ORDER:
a) "{name} net worth 2026"
b) "{name} net worth 2025"
c) "{name} OpenSecrets financial disclosure 2024"
d) "{name} stock trades STOCK Act 2024 2025"
e) "{name} net worth site:forbes.com OR site:bloomberg.com"

HISTORY — ZERO TOLERANCE FOR GUESSING:
Only include a year if a credible source cited a SPECIFIC number for that exact year.
- Range → skip or use midpoint clearly labeled as estimate
- Speculation → skip
- Interpolation → skip
- If NO verified historical data → just: "2026:{{net_worth}}"

REQUIRED SECTIONS IN ARTICLE (leave "article" field empty — generated separately):

1. Quick Summary (2-3 sentences on primary wealth source)
2. Career Earnings (official salary + political career timeline)
3. Investment Portfolio (stocks, real estate, businesses — with specific values)
4. Recent Trades (if Congress member: STOCK Act filings 2024-2026 with tickers)
5. Key Takeaways (short paragraph, not a list)

ARTICLE STRUCTURE:
ANGLE: {angle}
INTRO: {intro_style}
{h2_count} H2 sections — each SPECIFIC to {name} with dollar amounts, asset names, years, or trades
Target: {word_target} words

SEO:
- First paragraph: "{name} net worth" naturally
- Use "{name} net worth 2026" once in body
- Net worth figure mentioned 3+ times
- H2s contain keyword variants: salary, assets, income, wealth, investments, trades
- Compare to 2 peers with their net worth figures
- Last section: Key Takeaways paragraph (boosts dwell time)

WRITING STYLE — NYT/WSJ investigative feature:
- Short sentences for impact. Then medium. Long only for data explanation.
- Em-dashes for asides — like this — use them
- Contractions: "he's", "didn't", "that's"
- First name after first mention
- Active verbs: "bought", "built", "sold", "lost"
- Rhetorical questions once every 400-500 words
- Specific beats vague: "$2.3M Brooklyn condo" not "real estate holdings"

BANNED (automatic failure):
"it's worth noting", "delve into", "moreover", "furthermore", "navigating",
"landscape", "testament to", "lucrative", "multifaceted", "significant",
"notably", "leveraged", "garnered", "accumulated wealth", "amassed",
"robust portfolio", "in summary", "additionally", "over the years",
"throughout his/her career", "it is clear", "when it comes to",
"in terms of", "due to the fact that", "in order to", "showcases",
"underscores", "demonstrates", "plays a key role", "a wide range of"

HTML TABLES: If the politician has notable stock trades or asset breakdown,
include ONE <table> with columns: Asset/Ticker | Value/Amount | Date/Source

RETURN EXACT JSON — all 11 fields required:
{{
  "article": "",
  "net_worth": 7300000000,
  "job_title": "SEARCH '{{name}} current role April 2026' first. Write ACTUAL 2026 status. E.g.: 'U.S. Senator (R-TX), incumbent' / 'Former Governor (2019-2023), now private investor'. NEVER assume old title.",
  "history": "2026:{{net_worth}}",
  "wealth_sources": ["Real Estate Holdings", "Book Deals & Royalties", "Stock Market Investments"],
  "assets": "One specific sentence naming actual holdings with dollar values — e.g. '$4.2M Georgetown home, $1.8M Vanguard index fund portfolio, $600K rental property in Austin'",
  "cats": ["Most Searched Politicians", "one category from list"],
  "urls": ["https://opensecrets.org/...", "https://forbes.com/...", "https://example.com/..."],
  "seo_title": "REQUIRED: '{name} Net Worth 2026: [specific hook]'. 55-65 chars. Hook = real fact/figure. Never cut mid-word.",
  "seo_desc": "130-150 chars. Include net worth figure and one surprising fact. CTA tone.",
  "faq": [
    {faq_q1},
    {faq_q2},
    {faq_q3},
    {faq_q4}
  ]
}}

CATEGORIES: {cats_list}
WEALTH SOURCES (pick 2-4 that genuinely apply): {wealth_list}
SEO DESC ANGLE: {seo_angle}

URLS: 3-4 REAL working URLs. Prefer opensecrets.org, congress.gov, forbes.com, ballotpedia.org.
NO: vertexaisearch, google.com, youtube.com, twitter.com, facebook.com, wikipedia.org

⚠️ OUTPUT: Start with {{ nothing before. End with }} nothing after.
No markdown. No ```json. net_worth = plain integer. All 11 fields required."""


def build_article_prompt(name, data):
    """Antras prompt'as — tik straipsnio HTML generavimui."""
    net_worth   = data.get("net_worth", 0)
    job_title   = data.get("job_title", "politician")
    assets      = data.get("assets", "")
    wealth_src  = ", ".join(data.get("wealth_sources", []))
    faq_items   = data.get("faq", [])

    h2_counts = [4, 4, 5, 5, 5, 6]
    h2_count  = random.choice(h2_counts)
    word_targets = {4: "900-1100", 5: "1100-1300", 6: "1300-1500"}
    word_target  = word_targets[h2_count]

    angles = [
        f"The most CONTROVERSIAL or SURPRISING aspect of {name}'s wealth.",
        f"How {name}'s wealth CHANGED dramatically.",
        f"The CONTRAST between {name}'s public image and actual financial reality.",
        f"{name}'s INVESTMENT PORTFOLIO and stock trades.",
        f"{name}'s REAL ESTATE and physical assets.",
    ]
    intro_styles = [
        f"Open with a provocative question about {name}'s money. Answer it immediately.",
        f"Open with the single most surprising number or fact — no buildup.",
        f"Open by contrasting {name}'s public image with actual wealth.",
        f"Open with a specific year, deal, or stock trade that changed {name}'s financial life.",
    ]
    angle       = random.choice(angles)
    intro_style = random.choice(intro_styles)

    # FAQ jako reference text
    faq_ref = "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faq_items]) if faq_items else ""

    return f"""You are an investigative financial journalist. Write a {word_target}-word article about {name}'s finances in HTML format.

VERIFIED DATA (use these exact figures — do NOT contradict them):
- Net worth: ${net_worth:,} (as of 2026)
- Current role: {job_title}
- Key assets: {assets}
- Wealth sources: {wealth_src}

⚠️ 2026 REALITY CHECK:
- Role is: {job_title}
- If "Former" or "retired" → write about what they do NOW (pension, investments, speaking, board seats)
- NEVER mention a salary from a role they no longer hold
- Net worth figure in article MUST be ${net_worth:,} — no other figure

STRUCTURE: {intro_style} → {h2_count} H2 sections
ANGLE: {angle}

REQUIRED SECTIONS:
1. Quick Summary (2-3 sentences, primary wealth source)
2. Career Earnings (salary history, career timeline)
3. Investment Portfolio (specific stocks, real estate, businesses with values)
4. Recent Trades (if applicable: STOCK Act filings with tickers and dates)
5. Key Takeaways (final paragraph — memorable contrast, question, or reality check)

H2 RULES:
- Each H2 specific to {name}: dollar amount, asset name, year, or trade
- Exactly {h2_count} H2 sections
- NO H2 that asks FAQ-style questions (How did X make money? etc.)

HTML TABLE: If stock trades or asset data exists, include ONE <table>:
<table><thead><tr><th>Asset/Ticker</th><th>Value</th><th>Date</th></tr></thead><tbody>...</tbody></table>

WRITING STYLE:
- Short punchy sentences for impact. Medium ones for context. Long only for data.
- Em-dashes — like this — for asides
- Contractions: "he's", "didn't", "that's"
- First name after first mention
- Active verbs always
- One rhetorical question per 400-500 words
- Specific: "$2.3M Brooklyn condo" not "real estate holdings"

BANNED: "it's worth noting", "delve", "moreover", "furthermore", "navigating",
"landscape", "testament", "lucrative", "multifaceted", "significant", "notably",
"leveraged", "garnered", "accumulated wealth", "amassed", "robust portfolio",
"in summary", "additionally", "over the years", "throughout his/her career"

SEO:
- First paragraph: "{name} net worth" naturally
- "{name} net worth 2026" once in body
- Net worth mentioned 3+ times as ${net_worth:,}
- Compare to 2 other politicians with their net worth figures

OUTPUT: Return ONLY the HTML article body.
Start with <p> or <h2>. End with </p> or </table>.
Use ONLY: <p>, <h2>, <h3>, <strong>, <em>, <ul>, <li>, <table>, <thead>, <tbody>, <tr>, <th>, <td>
NO links, NO anchor tags, NO JSON, NO markdown, NO FAQ section, NO explanations."""


# ─── WORDPRESS ───────────────────────────────────────────────────────────────

def post_to_wp(name, data, img_id, img_url_val, post_id=None):
    print("    [4/4] Keliame i WordPress...")

    cats          = resolve_categories(data.get("cats", []))
    nw_raw        = data.get("net_worth", 0)
    net_worth     = clean_net_worth(nw_raw)
    net_worth_int = int(net_worth) if net_worth.isdigit() else 0
    net_worth_int = validate_net_worth(name, net_worth_int)
    net_worth     = str(net_worth_int) if net_worth_int > 0 else net_worth
    history = ""  # Visada tik 2026 — seni duomenys nepatikimi
    job_title     = data.get("job_title", "").strip()

    print(f"    NW: {net_worth} | history: {history.count(',') + 1 if history else 0} entries | cats: {cats}")

    seo_desc = data.get("seo_desc", "").strip()
    if len(seo_desc) < 50:
        seo_desc = f"Complete financial profile of {name}: net worth, income sources, assets and wealth history for 2026."
    if len(seo_desc) > 155:
        seo_desc = seo_desc[:155].rsplit(' ', 1)[0]  # nukirpam prie žodžio ribos

    # Title: smart truncation - nekerpame žodžių viduryje
    seo_title = data.get("seo_title", f"{name} Net Worth 2026").strip()
    if len(seo_title) > 65:
        seo_title = seo_title[:65].rsplit(' ', 1)[0]  # nukirpam prie žodžio ribos
    # Jei po nukirpimo liko be kablelių ar nebaigta, papildome taškais
    if seo_title and seo_title[-1] not in '.?!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789)':
        seo_title = seo_title.rstrip(' ,:;-–') 
    data["seo_title"] = seo_title

    faq_items = data.get("faq", [])
    urls      = data.get("urls", [])
    print(f"    URLs gauta: {len(urls)}, po filtro: {len([u for u in urls if is_valid_source_url(u)])}")

    article_html = data.get("article", "")
    article_html = article_html.replace('\\n', ' ').replace('\\r', '').strip()
    import re as _re
    # Pašaliname JSON-LD jei Gemini įdėjo
    article_html = _re.sub(r'<script[^>]*application/ld\+json[^>]*>.*?</script>\s*', '', article_html, flags=_re.DOTALL | _re.IGNORECASE)
    # Pašaliname FAQ sekciją pagal class
    article_html = _re.sub(r'<div[^>]*pnw-faq[^>]*>.*?</div>\s*', '', article_html, flags=_re.DOTALL)
    # Pašaliname <h2>FAQ</h2> arba <h2>Frequently Asked Questions</h2> ir VISKĄ PO JO
    article_html = _re.sub(r'<h2[^>]*>\s*(?:Frequently Asked Questions|FAQ)\s*</h2>.*', '', article_html, flags=_re.DOTALL | _re.IGNORECASE)
    # Pašaliname <h2 id="toc-N-faq..."> ir viską po jo
    article_html = _re.sub(r'<h2[^>]*id=["\'][^"\']*faq[^"\']*["\'][^>]*>.*', '', article_html, flags=_re.DOTALL | _re.IGNORECASE)
    # Pašaliname FAQ kaip <p><strong>Question?</strong>... Answer</p> paragrafus
    # Jei paragrafas prasideda <strong> kuris baigiasi klausimu — tai FAQ
    article_html = _re.sub(r'<p>\s*<strong>[^<]{10,}\?</strong>.*?</p>\s*', '', article_html, flags=_re.DOTALL)
    # Pašaliname question-style H2 (How/What/Does/Is/Why/Where/When/Who)
    article_html = _re.sub(
        r'<h2[^>]*>\s*(?:How|What|Does|Is|Why|Where|When|Who)\s[^<]{10,}</h2>.*',
        '', article_html, flags=_re.DOTALL | _re.IGNORECASE
    )
    # Pašaliname visus <style> tagus iš article
    article_html = _re.sub(r'<style[^>]*>.*?</style>\s*', '', article_html, flags=_re.DOTALL | _re.IGNORECASE)
    article_with_ids, toc_html = build_toc_html(article_html)

    full_article = (
        build_article_css()
        + toc_html
        + f'<div class="pnw-article">{article_with_ids}</div>'
        + build_faq_html(faq_items)
        + build_references_html(urls)
    )

    # 1-as postas po 1 valandos, kiekvienas kitas kas 5 valandas po jo
    SCHEDULE_START = datetime(2026, 3, 16, 22, 11, 0, tzinfo=timezone.utc)
    post_num       = stats["ok"] + stats["fail"] + stats["skip"]  # 0-based
    schedule_str   = (SCHEDULE_START + timedelta(hours=4 * post_num)).strftime("%Y-%m-%dT%H:%M:%S")
    print(f"    Suplanuota: {schedule_str}")

    payload = {
        "title":          {"raw": data.get("seo_title", f"{name} Net Worth 2026")},
        "slug":           make_slug(name),
        "content":        {"raw": full_article},
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
            "rank_math_title":         data.get("seo_title", f"{name} Net Worth 2026"),
            "rank_math_description":   seo_desc[:155],
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
                # Dvigubas FAQ — article viduje yra FAQ paragrafai
                if faq_present and '<strong>' in art and '?</strong>' in art:
                    missing_info.append("double_FAQ")

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

        # Jei 2+ bandymas ir žinome net worth — naudojame mini prompt
        known_nw = KNOWN_NET_WORTHS.get(name)
        if attempt >= 1 and known_nw:
            mini_prompt = f"""Search for current information about {name} and return ONLY this JSON:
{{
  "article": "",
  "net_worth": {known_nw},
  "job_title": "search and fill",
  "history": "2026:{known_nw}",
  "wealth_sources": ["search and fill 2-3 items"],
  "assets": "search and fill one sentence",
  "cats": ["Most Searched Politicians"],
  "urls": ["search and fill 2-3 real URLs from forbes.com opensecrets.org ballotpedia.org"],
  "seo_title": "{name} Net Worth 2026: search and fill hook 55-65 chars",
  "seo_desc": "search and fill 130-150 chars",
  "faq": [
    {{"question": "What is {name}'s net worth in 2026?", "answer": "search and fill"}},
    {{"question": "How did {name} make their money?", "answer": "search and fill"}},
    {{"question": "What is {name}'s salary?", "answer": "search and fill"}},
    {{"question": "Is {name} getting richer or poorer?", "answer": "search and fill"}}
  ]
}}
Start with {{ end with }} nothing else."""
            res = call_gemini(mini_prompt, gemini_url)
        else:
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

        # ── ANTRAS CALL: straipsnis generuojamas atskirai, BEZ google_search ──
        print(f"    [3b/4] Gemini straipsnis...")
        art_res = call_gemini_plain(build_article_prompt(name, parsed), gemini_url)
        if art_res:
            try:
                parts = art_res.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                clean_art = "".join(p.get("text", "") for p in parts).strip()
                clean_art = re.sub(r'^```html\s*', '', clean_art)
                clean_art = re.sub(r'```$', '', clean_art).strip()
                if len(clean_art) > 500:
                    parsed["article"] = clean_art
                    print(f"    Straipsnis: {len(clean_art)} chars")
                else:
                    print(f"    ⚠ Straipsnis per trumpas ({len(clean_art)}), naudojame tuščią")
            except Exception as e:
                print(f"    ⚠ Straipsnis parse klaida: {e}")
        else:
            print(f"    ⚠ Straipsnis nepavyko, naudojame tuščią")

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
