import os, requests, json, re, time, sys, urllib.parse
sys.stdout.reconfigure(line_buffering=True)
print("--- BOTAS STARTUOJA ---")

GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
AUTHOR_ID   = 3
WP_TIMEOUT  = 30
IMG_TIMEOUT = 20
GEMINI_TIMEOUT = 120

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


def find_gemini_url():
    preferred = [
        "gemini-2.0-flash-001", "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash", "gemini-2.0-flash-lite",
        "gemini-flash-latest", "gemini-1.5-flash-latest", "gemini-1.5-flash"
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
             next((m for m in available if "flash" in m.lower()), "gemini-2.0-flash")
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

    for model in available[:10]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=test_payload, timeout=20)
            if r.status_code in (200, 400, 403):
                print(f"  Rastas: {model}")
                return url
        except:
            pass

    # Hardcoded fallback
    print("  Naudojame fallback URL")
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"


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
        except:
            pass
        return None

    # 1. Tiesiogiai
    thumb = fetch_thumb(name)
    if thumb:
        print("    [1/4] Rasta tiesiogiai")
        return thumb

    # 2. Wikipedia Search API - randa teisingą puslapį net jei vardas skiriasi
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
                    print(f"    [1/4] Rasta per Search ({found})")
                    return thumb
    except Exception as e:
        print(f"      Search klaida: {e}")

    # 3. OpenSearch fallback
    try:
        enc = requests.utils.quote(name)
        res = requests.get(
            f"https://en.wikipedia.org/w/api.php?action=opensearch&search={enc}&limit=3&format=json",
            headers=headers, timeout=10).json()
        for found in res[1]:
            thumb = fetch_thumb(found)
            if thumb:
                print(f"    [1/4] Rasta per OpenSearch ({found})")
                return thumb
    except:
        pass

    print("    [1/4] Nerasta")
    return None


def upload_image_to_wp(name, img_url):
    print("    [2/4] Keliame nuotrauka...")
    try:
        img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=IMG_TIMEOUT)
        img_res.raise_for_status()
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/media",
            data=img_res.content,
            headers={"Content-Disposition": f"attachment; filename={name.replace(' ','_')}.jpg",
                     "Content-Type": "image/jpeg"},
            auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        if res.status_code == 201:
            d = res.json()
            media_url = (d.get("media_details",{}).get("sizes",{})
                          .get("medium",{}).get("source_url") or d.get("source_url",""))
            print(f"    [2/4] Ikelta (ID:{d['id']})")
            return d["id"], media_url
        print(f"    [2/4] Klaida {res.status_code}")
    except requests.exceptions.Timeout:
        print("    [2/4] Timeout")
    except Exception as e:
        print(f"    [2/4] {e}")
    return None, None


def call_gemini(prompt, gemini_url, retries=4):
    delay = 15
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 32768},
        "tools": [{"google_search": {}}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in
            ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
             "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    for i in range(retries):
        try:
            print(f"    [3/4] Gemini {i+1}/{retries}...")
            t0 = time.time()
            r = requests.post(gemini_url, json=payload, timeout=GEMINI_TIMEOUT)
            print(f"    [3/4] {r.status_code} ({round(time.time()-t0,1)}s)")
            if r.status_code == 200:
                return r.json()
            elif r.status_code in (429, 503):
                time.sleep(delay); delay = min(delay*2, 120)
            else:
                print(f"    [3/4] Klaida: {r.text[:200]}"); break
        except requests.exceptions.Timeout:
            print(f"    [3/4] Timeout"); time.sleep(delay); delay = min(delay*2,120)
        except Exception as e:
            print(f"    [3/4] {e}"); break
    return None


def parse_json(text):
    # 1. Tiesiogiai
    for t in [text, text.strip()]:
        try: return json.loads(t)
        except: pass
    # 2. Iš markdown bloko
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        try: return json.loads(md.group(1))
        except: pass
    # 3. Nuo { iki paskutinio }
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        try: return json.loads(text[s:e+1])
        except: pass
    # 4. Jei JSON nupjautas - bandome uzdaryti
    if s != -1:
        chunk = text[s:]
        # Pridedame trescius kabliatasskius prie neuzbaigtu lauku
        chunk = re.sub(r',\s*"[^"]+": "[^"]*$', '', chunk)  # nupjauta reiksme
        chunk = re.sub(r',\s*"[^"]+": \[$', '', chunk)     # nupjautas masyvas
        # Bandome uzdaryti JSON
        for closing in ['"}', '"}}', '"]}', '"]}}}']:
            try: return json.loads(chunk + closing)
            except: pass
        # Paskutinis bandymas - ieskome article lauko ir konstruojame minimal JSON
        article_m = re.search(r'"article":\s*"(.*?)"(?=,\s*"net_worth")', chunk, re.DOTALL)
        nw_m = re.search(r'"net_worth":\s*"?(\d+)"?', chunk)
        job_m = re.search(r'"job_title":\s*"([^"]*)"', chunk)
        if article_m and nw_m:
            minimal = {
                "article": article_m.group(1).replace('\\"', '"'),
                "net_worth": nw_m.group(1),
                "job_title": job_m.group(1) if job_m else "Politician",
                "history": "2022:0,2023:0,2024:0,2025:0,2026:0",
                "wealth_sources": [],
                "assets": "",
                "cats": ["Most Searched Politicians"],
                "urls": [],
                "seo_title": "",
                "seo_desc": "",
                "faq": []
            }
            print("    PERSPEJIMAS: JSON buvo nupjautas - naudojame minimal versija")
            return minimal
    raise ValueError(f"JSON klaida: {text[:300]}")


def parse_to_int(v):
    v = str(v).strip().replace(",","").replace("$","")
    try:
        if v.upper().endswith("B"): return int(float(v[:-1])*1_000_000_000)
        if v.upper().endswith("M"): return int(float(v[:-1])*1_000_000)
        if v.upper().endswith("K"): return int(float(v[:-1])*1_000)
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

def validate_net_worth(n):
    if n <= 0: return False, "0 arba neigiamas"
    if n < 10_000: return False, f"per mazas: ${n:,}"
    if n > 100_000_000_000: return False, "per didelis"
    if n > 500_000_000: return True, f"ISPEJIMAS: ${n/1_000_000:.0f}M"
    return True, ""

def validate_history(h, n):
    if not h: return False, "tuscias"
    entries = []
    for part in h.split(","):
        m = re.match(r"(\d{4}):(\d+)", part.strip())
        if m:
            entries.append(int(m.group(2)))
    if len(entries) < 3: return False, f"per mazai: {len(entries)}"
    if n > 0 and abs(entries[-1]-n)/max(n,1) > 0.5: return False, "nesutampa su net_worth"
    return True, ""

def check_post_exists(name):
    slug = make_slug(name)
    res = requests.get(f"{WP_BASE_URL}/wp/v2/posts",
                       params={"slug": slug, "status": "any"},
                       auth=(WP_USER, WP_PASS), timeout=15)
    if res.status_code == 200 and res.json():
        e = res.json()[0]; return True, e.get("id"), e.get("status")
    return False, None, None

def make_slug(name):
    s = re.sub(r"[^a-z0-9\s-]", "", name.lower().strip())
    s = re.sub(r"\s+", "-", s)
    return f"{s}-net-worth"

def format_sources(urls, name=""):
    final = []
    quiver_added = False
    for url in urls:
        if "quiverquant.com" in url:
            if not quiver_added and name in BIOGUIDE_MAP:
                fn, ln, bio = BIOGUIDE_MAP[name]
                if bio:
                    ne = urllib.parse.quote(f"{fn} {ln}")
                    final.append(f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}")
                    quiver_added = True
            continue
        final.append(url.strip())
    if not quiver_added and name in BIOGUIDE_MAP:
        fn, ln, bio = BIOGUIDE_MAP[name]
        if bio:
            ne = urllib.parse.quote(f"{fn} {ln}")
            final.append(f"https://www.quiverquant.com/congresstrading/politician/{ne}-{bio}")
    return "\n".join(u for u in final if u)

def resolve_categories(cat_names):
    cat_ids = {27}
    for n in cat_names:
        if n in CAT_MAP:
            cid = CAT_MAP[n]; cat_ids.add(cid)
            p = PARENT_CAT.get(cid)
            if p: cat_ids.add(p)
    if len(cat_ids) <= 1: cat_ids.add(19)
    cat_ids.discard(None)
    return list(cat_ids)

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
    from datetime import datetime
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
    }
    items = []
    for url in urls:
        domain = re.sub(r"https?://(www\.)?","",url).split("/")[0]
        label = next((v for k,v in label_map.items() if k in domain), domain)
        items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')
    return f"""
<hr style="margin:40px 0 20px">
<div class="references-section">
<h2>References &amp; Sources</h2>
<p><em>Last updated: {month_year}. Net worth estimates are based on public financial disclosures and independent research.</em></p>
<ul>{"".join(items)}</ul>
</div>"""

def build_prompt(name):
    cats_list = ", ".join(CAT_MAP.keys())
    wealth_list = ", ".join(WEALTH_OPTIONS)
    return f"""You are an experienced financial journalist writing for a general audience. Research {name} and write an accurate, engaging financial profile that reads like a human expert wrote it — not an AI.

CRITICAL RULES:
- Article MUST be 900-1100 words in the "article" field
- Use ONLY verified facts. Never invent numbers.
- Write naturally — vary sentence length, use contractions occasionally
- BANNED phrases: "it's worth noting", "delve into", "in conclusion", "moreover", "furthermore", "navigating", "landscape", "testament to", "shed light on", "plays a pivotal role"
- Start with ONE surprising or counterintuitive financial fact — hook the reader immediately
- Use specific numbers with source: "$4.2M (per OpenSecrets)" not "significant wealth"
- Include at least one genuinely interesting personal financial detail most people don't know

ARTICLE STRUCTURE:
- Opening paragraph: Most surprising financial fact. No generic intros.
- <h2>How {name} Makes Money</h2> — salary, speaking fees, books, businesses. Specific amounts.
- <h2>Assets and Investments</h2> — real estate, stocks, businesses. Name actual holdings.
- <h2>Net Worth Over the Years</h2> — track changes, explain jumps or drops
- <h2>The Road to Wealth: Background and Career</h2> — career before politics, 1-2 lesser-known personal facts

TONE: Write like explaining to a smart curious friend. Plain English. Make it interesting and human, not clinical.

FIELDS:
net_worth: integer dollars (e.g. 4200000). Must be from real sources.
job_title: current/most recent real title
history: "2022:INT,2023:INT,2024:INT,2025:INT,2026:INT" real data, not perfectly smooth
wealth_sources: 1-2 from [{wealth_list}]
assets: one specific sentence with real holdings
cats: from [{cats_list}] — always include "Most Searched Politicians"
urls: 2-4 real URLs with actual financial data on this person
seo_title: "{name} Net Worth 2026" (under 60 chars)
seo_desc: 120-155 chars, unique, no exact net worth figure
faq: exactly 3-4 questions:
  Q1: current net worth with figure and source
  Q2: how they made their money (specific)
  Q3: something surprising (biggest asset, unusual investment)
  Q4 optional: recent wealth change

Return ONLY valid JSON, no markdown:
{{"article":"<p>Hook...</p><h2>How {name} Makes Money</h2><p>...</p><h2>Assets and Investments</h2><p>...</p><h2>Net Worth Over the Years</h2><p>...</p><h2>The Road to Wealth: Background and Career</h2><p>...</p>","net_worth":"INT","job_title":"TITLE","history":"2022:INT,2023:INT,2024:INT,2025:INT,2026:INT","wealth_sources":["S1"],"assets":"Specific sentence.","cats":["Most Searched Politicians","CATEGORY"],"urls":["URL1","URL2"],"seo_title":"{name} Net Worth 2026","seo_desc":"120-155 chars","faq":[{{"question":"How much is {name} worth in 2026?","answer":"Direct answer with figure."}},{{"question":"How did {name} make their money?","answer":"Specific sources."}},{{"question":"What is {name}'s biggest asset?","answer":"Specific asset."}}]}}"""


def post_to_wp(name, data, img_id, img_url_val):
    print("    [4/4] Keliame i WordPress...")
    cats          = resolve_categories(data.get("cats", []))
    net_worth     = clean_net_worth(data.get("net_worth", "0"))
    net_worth_int = int(net_worth) if net_worth.isdigit() else 0
    history       = clean_history(data.get("history", ""))
    job_title     = data.get("job_title", "")

    nw_ok, nw_msg     = validate_net_worth(net_worth_int)
    hist_ok, hist_msg = validate_history(history, net_worth_int)
    post_status = "draft" if (not nw_ok or not hist_ok) else "future"
    if not nw_ok: print(f"    NET WORTH: {nw_msg}")
    if not hist_ok: print(f"    HISTORY: {hist_msg}")
    if nw_ok and nw_msg: print(f"    {nw_msg}")
    print(f"    Status: {post_status} | NW: {net_worth} | Cats: {cats}")

    seo_desc = data.get("seo_desc", "")
    if len(seo_desc) < 50:
        seo_desc = f"Explore {name}'s financial profile in 2026. Full breakdown of assets, career earnings, and wealth sources."

    full_article = (data["article"]
                    + build_faq_html(data.get("faq", []))
                    + build_references_html(data.get("urls", [])))

    from datetime import datetime, timezone, timedelta
    post_num = stats["ok"] + stats["fail"] + stats["skip"] + 1
    schedule_str = (datetime.now(timezone.utc) + timedelta(minutes=124*post_num)).strftime("%Y-%m-%dT%H:%M:%S")
    print(f"    Suplanuota: {schedule_str}")

    payload = {
        "title": f"{name} Net Worth 2026",
        "slug": make_slug(name),
        "content": full_article,
        "status": post_status,
        "date": schedule_str if post_status == "future" else None,
        "author": AUTHOR_ID,
        "featured_media": img_id,
        "categories": cats,
        "acf": {
            "job_title": job_title,
            "net_worth": net_worth,
            "net_worth_history": history,
            "source_of_wealth": [s for s in data.get("wealth_sources",[]) if s in WEALTH_OPTIONS][:2],
            "main_assets": data.get("assets",""),
            "sources": format_sources(data.get("urls",[]), name),
            "photo_url": img_url_val,
        },
        "meta": {
            "rank_math_title": data.get("seo_title", f"{name} Net Worth 2026")[:60],
            "rank_math_description": seo_desc[:160],
            "rank_math_focus_keyword": f"{name} Net Worth 2026",
        }
    }

    for attempt in range(3):
        try:
            r = requests.post(f"{WP_BASE_URL}/wp/v2/posts",
                              json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
            if r.status_code in (201, 202):
                print(f"    [4/4] OK! {r.json().get('link','')}")
                with open("processed.txt","a") as pf: pf.write(name+"\n")
                return True
            elif r.status_code in (500,502,503,504):
                time.sleep(10*(attempt+1))
            else:
                print(f"    [4/4] Klaida {r.status_code}: {r.text[:300]}")
                return False
        except requests.exceptions.Timeout:
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] {e}"); return False
    return False


def run_bot(name, gemini_url):
    num = stats['ok']+stats['fail']+stats['skip']+1
    print(f"\n{'='*55}\n[{num}] {name}\n{'='*55}")
    exists, eid, estatus = check_post_exists(name)
    if exists:
        print(f"  PRALEIDŽIAMA (ID:{eid}, {estatus})")
        stats["skip"] += 1; return

    img_id, img_url_val = None, ""
    wiki_img = get_wiki_image(name)
    if wiki_img:
        img_id, img_url_val = upload_image_to_wp(name, wiki_img)

    res = call_gemini(build_prompt(name), gemini_url)
    if not res or "candidates" not in res:
        stats["skip"] += 1; return

    try:
        cand = res["candidates"][0]
        reason = cand.get("finishReason","UNKNOWN")
        text = cand["content"]["parts"][0]["text"]
        print(f"    {len(text)} simboliu, reason: {reason}")
        if reason == "MAX_TOKENS":
            print("    Nupjautas!")
            stats["fail"] += 1
            with open("failed.txt","a") as f: f.write(name+"\n")
            return
        data = parse_json(text)
    except Exception as e:
        print(f"  JSON klaida: {e}")
        stats["fail"] += 1
        with open("failed.txt","a") as f: f.write(name+"\n")
        return

    ok = post_to_wp(name, data, img_id, img_url_val)
    if ok:
        stats["ok"] += 1; print(f"  SEKME: {name}")
    else:
        stats["fail"] += 1; print(f"  NEPAVYKO: {name}")
        with open("failed.txt","a") as f: f.write(name+"\n")


if __name__ == "__main__":
    if not os.path.exists("names.txt"):
        print("KLAIDA: names.txt nerastas!"); sys.exit(1)

    gemini_url = find_gemini_url()
    print(f"Gemini paruostas.\n")

    with open("names.txt") as f:
        names = [n.strip() for n in f if n.strip()]
    print(f"Vardai: {len(names)}")

    for i, name in enumerate(names):
        run_bot(name, gemini_url)
        if i < len(names)-1:
            pause = 20 if (i+1)%10==0 else 8
            print(f"\nPauze {pause}s (ok={stats['ok']} fail={stats['fail']} skip={stats['skip']})")
            time.sleep(pause)

    print(f"\n{'='*55}")
    print(f"REZULTATAI: ok={stats['ok']} | fail={stats['fail']} | skip={stats['skip']}")
    print(f"{'='*55}")
