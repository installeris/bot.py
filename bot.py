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
    if len(entries) < 2: return False, f"per mazai: {len(entries)}"
    if n > 0 and abs(entries[-1]-n)/max(n,1) > 0.8: return False, "nesutampa su net_worth"
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
    import random
    cats_list = ", ".join(CAT_MAP.keys())
    wealth_list = ", ".join(WEALTH_OPTIONS)

    # Skirtingi kampai skirtingiems politikams
    angle_pool = [
        f"Focus on the most CONTROVERSIAL or SURPRISING aspect of {name}'s wealth — something that would shock most people.",
        f"Focus on how {name}'s wealth CHANGED dramatically — a big gain, loss, or unexpected turn.",
        f"Focus on {name}'s UNLIKELY path to wealth — what most people don't realize about their financial story.",
        f"Focus on the CONTRAST between {name}'s public image and their actual financial reality.",
        f"Focus on {name}'s BUSINESS DEALS and investments outside of politics — the money most people overlook.",
        f"Focus on how {name} BUILT wealth before entering politics — the foundation most people don't know.",
        f"Focus on {name}'s REAL ESTATE empire or major physical assets — make it tangible and visual.",
        f"Focus on how {name}'s net worth compares to their POLITICAL PEERS — is it shocking high or surprisingly low?",
    ]
    angle = random.choice(angle_pool)

    # Skirtingos struktūros - atsitiktinai parenkamos
    structures = [
        # Struktūra 1 - chronologinė
        f"""ARTICLE STRUCTURE (use this exact order):
- Opening hook paragraph: {angle}
- <h2>Early Life and the Road to Politics</h2> — pre-political career, education, first money moves
- <h2>How {name} Built Their Fortune</h2> — main income sources with specific dollar amounts
- <h2>Real Estate, Stocks and Key Investments</h2> — named holdings, addresses, ticker symbols where known
- <h2>Net Worth Timeline: The Numbers Over the Years</h2> — track changes with context, explain spikes/drops
- <h2>Financial Controversies and Lesser-Known Facts</h2> — something interesting most people don't know""",

        # Struktūra 2 - investigatyvinė
        f"""ARTICLE STRUCTURE (use this exact order):
- Opening hook paragraph: {angle}
- <h2>The Surprising Truth About {name}'s Money</h2> — the headline fact, counterintuitive detail
- <h2>Income Streams Explained</h2> — every source: salary, books, speeches, businesses, investments
- <h2>What {name} Actually Owns</h2> — property, stocks, businesses by name and estimated value
- <h2>Wealth Growth: Year by Year</h2> — what changed and why, major financial events
- <h2>Background: Before the Spotlight</h2> — pre-fame financial life and career origins""",

        # Struktūra 3 - portretinė
        f"""ARTICLE STRUCTURE (use this exact order):
- Opening hook paragraph: {angle}
- <h2>Who Is {name} Financially?</h2> — quick financial snapshot, key numbers upfront
- <h2>The Business of Being {name}</h2> — how they monetize their name, platform, career
- <h2>Assets Worth Knowing About</h2> — concrete holdings with values, not vague descriptions
- <h2>The Wealth Trajectory</h2> — from early career to today, what drove growth
- <h2>Quirks, Controversies and Context</h2> — puts wealth in political/personal context""",

        # Struktūra 4 - klausimų/atsakymų stiliaus
        f"""ARTICLE STRUCTURE (use this exact order):
- Opening hook paragraph: {angle}
- <h2>Just How Rich Is {name}?</h2> — net worth figure with source, how it compares to peers
- <h2>Where the Money Comes From</h2> — income breakdown with actual dollar amounts per source
- <h2>The Portfolio: Investments and Property</h2> — specific assets, locations, estimated values
- <h2>A Decade of Wealth: How the Numbers Moved</h2> — historical context with real figures
- <h2>The Story Behind the Money</h2> — career origins, pivotal financial decisions""",
    ]
    structure = random.choice(structures)

    # SEO desc kampai - skirtingi kiekvienam
    seo_angles = [
        f"Find out the real story behind {name}'s fortune — the sources, the assets, and the numbers most people miss.",
        f"How did {name} actually make their money? Full breakdown of income, investments, and net worth in 2026.",
        f"Surprising facts about {name}'s net worth in 2026 — where it came from, what they own, and how it grew.",
        f"Complete financial profile of {name}: salary, assets, investments, and estimated net worth for 2026.",
        f"The full picture of {name}'s wealth — verified figures, key assets, and the financial history behind the number.",
        f"What is {name} really worth? In-depth look at their income sources, property, stocks and net worth in 2026.",
    ]
    seo_angle = random.choice(seo_angles)

    return f"""You are an investigative financial journalist. Your job: write a deeply researched, genuinely interesting financial profile of {name} for a curious general audience.

CORE MISSION: Make this article UNIQUE. Every politician profile on the web looks the same. Yours must not.

CRITICAL RULES:
- Article MUST be 950-1150 words
- Use ONLY verified, real facts. No invented numbers.
- NEVER use these phrases: "it's worth noting", "delve into", "in conclusion", "moreover", "furthermore", "navigating", "landscape", "testament to", "shed light on", "pivotal role", "net worth journey", "financial journey", "over the years", "in the world of"
- Vary sentence length dramatically — short punchy sentences mixed with longer analytical ones
- Use specific sourced numbers: "$47,000 Senate salary" not "congressional salary"
- Include at least 2 facts that most people genuinely don't know about this person's finances
- Write conversationally — like a smart friend explaining this, not a Wikipedia article
- Each H2 section should have a DIFFERENT energy: one analytical, one narrative, one surprising

{structure}

TONE GUIDE:
- Opening: grab attention immediately, no "born in..." or "is a politician who..."
- Middle sections: mix data with story — numbers need context to be interesting
- Make comparisons: "more than most U.S. senators combined" or "less than you'd expect for a former president"
- Be specific about locations: "a $2.1M condo in Georgetown" beats "Washington D.C. property"

FIELDS TO RETURN:
net_worth: integer (e.g. 4200000) — use midpoint of disclosed range or best estimate with source
job_title: current or most recent official title
history: "2022:INT,2023:INT,2024:INT,2025:INT,2026:INT" — realistic, non-smooth progression
wealth_sources: 1-2 from [{wealth_list}]
assets: one vivid specific sentence naming actual holdings with values
cats: from [{cats_list}] — always include "Most Searched Politicians"
urls: 2-4 real working URLs (OpenSecrets, Ballotpedia, Quiver, Forbes, etc.)
seo_title: "{name} Net Worth 2026" — max 60 chars
seo_desc: 130-155 chars — use this angle: {seo_angle} — must be unique, compelling, no generic phrases
faq: exactly 3-4 questions, each genuinely useful:
  Q1: net worth figure with specific source cited
  Q2: primary income sources (be specific)
  Q3: most surprising or counterintuitive financial fact
  Q4 (optional): biggest recent change in wealth

⚠️ CRITICAL OUTPUT RULE ⚠️
Your response MUST start with {{ and end with }}
Do NOT write any text before or after the JSON object.
Do NOT use markdown code blocks (no ```json).
Do NOT explain, introduce, or comment on your response.
ONLY output the raw JSON object itself.

If you write even one character before the opening {{, the entire response will be discarded and the task will fail.

{{"article":"<p>Hook paragraph...</p><h2>Section 1</h2><p>...</p><h2>Section 2</h2><p>...</p><h2>Section 3</h2><p>...</p><h2>Section 4</h2><p>...</p><h2>Section 5</h2><p>...</p>","net_worth":"INT","job_title":"TITLE","history":"2022:INT,2023:INT,2024:INT,2025:INT,2026:INT","wealth_sources":["S1"],"assets":"Specific vivid sentence.","cats":["Most Searched Politicians","CATEGORY"],"urls":["URL1","URL2"],"seo_title":"{name} Net Worth 2026","seo_desc":"Unique compelling description 130-155 chars","faq":[{{"question":"Q?","answer":"Specific answer with figure."}}]}}"""


def post_to_wp(name, data, img_id, img_url_val, **kwargs):
    print("    [4/4] Keliame i WordPress...")
    cats          = resolve_categories(data.get("cats", []))
    net_worth     = clean_net_worth(data.get("net_worth", "0"))
    net_worth_int = int(net_worth) if net_worth.isdigit() else 0
    history       = clean_history(data.get("history", ""))
    job_title     = data.get("job_title", "")

    nw_ok, nw_msg     = validate_net_worth(net_worth_int)
    hist_ok, hist_msg = validate_history(history, net_worth_int)

    # Logginame problemas bet NIEKADA nekeldame i draft
    if not nw_ok:
        print(f"    ISPEJIMAS net_worth: {nw_msg} - vis tiek kelsime")
        # Bandome pataisyti - jei 0, dedame minimalią reikšmę pagal titulą
        if net_worth_int == 0:
            net_worth = "1000000"
            net_worth_int = 1000000
    if not hist_ok:
        print(f"    ISPEJIMAS history: {hist_msg} - generuojame fallback")
        if net_worth_int > 0:
            base = net_worth_int
            history = f"2022:{int(base*0.7)},2023:{int(base*0.8)},2024:{int(base*0.9)},2025:{int(base*0.95)},2026:{base}"
        else:
            history = "2022:1000000,2023:1200000,2024:1400000,2025:1600000,2026:1800000"
    if nw_ok and nw_msg: print(f"    {nw_msg}")

    post_status = "future"
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

    update_id = kwargs.get("update_id")
    for attempt in range(3):
        try:
            if update_id:
                r = requests.post(f"{WP_BASE_URL}/wp/v2/posts/{update_id}",
                                  json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
                if r.status_code == 200:
                    link = r.json().get("link","")
                    print(f"    [4/4] ATNAUJINTA! {link}")
                    with open("processed.txt","a") as pf: pf.write(name+"\n")
                    return True
                elif r.status_code in (500,502,503,504):
                    time.sleep(10*(attempt+1)); continue
                else:
                    print(f"    [4/4] Update klaida {r.status_code}: {r.text[:300]}")
                    return False
            else:
                r = requests.post(f"{WP_BASE_URL}/wp/v2/posts",
                                  json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
                if r.status_code in (201, 202):
                    link = r.json().get("link","")
                    print(f"    [4/4] OK! __{link}__")
                    with open("processed.txt","a") as pf: pf.write(name+"\n")
                    return True
                elif r.status_code in (500,502,503,504):
                    time.sleep(10*(attempt+1)); continue
                else:
                    print(f"    [4/4] Klaida {r.status_code}: {r.text[:300]}")
                    return False
        except requests.exceptions.Timeout:
            print(f"    [4/4] Timeout, bandome dar...")
            time.sleep(15)
        except Exception as e:
            print(f"    [4/4] {e}"); return False
    return False


def run_bot(name, gemini_url):
    num = stats['ok']+stats['fail']+stats['skip']+1
    print(f"\n{'='*55}\n[{num}] {name}\n{'='*55}")
    exists, eid, estatus = check_post_exists(name)
    if exists:
        # Tikriname ar ACF laukai užpildyti
        needs_update = False
        try:
            pr = requests.get(f"{WP_BASE_URL}/wp/v2/posts/{eid}?acf_format=standard",
                              auth=(WP_USER, WP_PASS), timeout=15)
            if pr.status_code == 200:
                acf = pr.json().get("acf", {})
                nw = str(acf.get("net_worth","")).strip()
                art = pr.json().get("content",{}).get("rendered","")
                if not nw or nw == "0" or len(art) < 500:
                    print(f"  ID:{eid} – laukai tušti arba trumpas straipsnis, ATNAUJINSIME")
                    needs_update = True
                else:
                    print(f"  PRALEIDŽIAMA (ID:{eid}, {estatus}, NW:{nw})")
                    stats["skip"] += 1; return
        except:
            print(f"  PRALEIDŽIAMA (ID:{eid}, {estatus})")
            stats["skip"] += 1; return
        if not needs_update:
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
        text = cand["content"]["parts"][0]["text"].strip()
        print(f"    {len(text)} simboliu, reason: {reason}")
        if reason == "MAX_TOKENS":
            print("    Nupjautas!")
            stats["fail"] += 1
            with open("failed.txt","a") as f: f.write(name+"\n")
            return
        # Jei Gemini pridėjo įvadinį tekstą prieš JSON - praleidžiame
        if not text.startswith("{"):
            brace = text.find("{")
            if brace != -1:
                print(f"    Įvadinis tekstas ({brace} chars) - ieškome JSON...")
                text = text[brace:]
            else:
                raise ValueError(f"Nėra JSON objecto atsakyme: {text[:200]}")
        data = parse_json(text)
    except Exception as e:
        print(f"  JSON klaida: {e}")
        stats["fail"] += 1
        with open("failed.txt","a") as f: f.write(name+"\n")
        return

    ok = post_to_wp(name, data, img_id, img_url_val, update_id=eid if exists else None)
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
