#!/usr/bin/env python3
"""
Fix WordPress Sources URLs - Validuoja ir fiksuoja sulaužytas nuorodas
- Pereina PER VISUS posts (scheduled, published, draft)
- Tikrina 'sources' ACF field
- Validuoja URL accessibility
- Fiksuoja broken ones arba keičia į working alternatives
"""

import os, requests, json, re, time, sys, urllib.parse
from datetime import datetime
from urllib.parse import urlparse

sys.stdout.reconfigure(line_buffering=True)
print("=== FIX WORDPRESS SOURCES v2.0 (QuiverQuant Support) ===\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

# ✅ BIOGUIDE MAP - tų pačių iš bot.py
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
    "Rich McCormick": ("Rich", "McCormick", "M000223"),
    "Mark Green": ("Mark", "Green", "G000576"),
    "Josh Hawley": ("Josh", "Hawley", "H001089"),
    "Darrell Issa": ("Darrell Eugene", "Issa", "I000056"),
    "Ron Wyden": ("Ronald Lee", "Wyden", "W000779"),
    "Ronald Reagan": ("Ronald Wilson", "Reagan", ""),
    "Abraham Lincoln": ("Abraham", "Lincoln", ""),
}

stats = {
    "total_posts": 0,
    "with_sources": 0,
    "urls_checked": 0,
    "urls_broken": 0,
    "urls_fixed": 0,
    "posts_updated": 0,
}

# ✅ KREDIBILŪS ŠALTINIAI - jei broken, naudojame šituos
TRUSTED_SOURCES = {
    "opensecrets.org": "https://www.opensecrets.org/",
    "ballotpedia.org": "https://ballotpedia.org/",
    "forbes.com": "https://www.forbes.com/",
    "bloomberg.com": "https://www.bloomberg.com/",
    "reuters.com": "https://www.reuters.com/",
    "apnews.com": "https://apnews.com/",
    "cnbc.com": "https://www.cnbc.com/",
    "businessinsider.com": "https://www.businessinsider.com/",
    "thestreet.com": "https://www.thestreet.com/",
    "washingtonpost.com": "https://www.washingtonpost.com/",
    "nytimes.com": "https://www.nytimes.com/",
    "politico.com": "https://www.politico.com/",
}

# ❌ BLOCKED PATTERNS - niekada nenorime
BLOCKED_PATTERNS = [
    "vertexaisearch",
    "googleapis.com",
    "google.com/search",
    "youtube.com/watch",
    "twitter.com",
    "x.com/",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "reddit.com",
    "wikipedia.org",
]

# ✅ QUIVER SPECIAL HANDLING
QUIVER_PATTERN = r"quiverquant\.com/congresstrading/politician/([A-Za-z%\-]+)-([A-Z0-9]+)"


def get_quiver_url(name):
    """Kuria fresh QuiverQuant URL su bioguide ID"""
    if name not in BIOGUIDE_MAP:
        return None
    
    first_name, last_name, bioguide_id = BIOGUIDE_MAP[name]
    
    if not bioguide_id:
        print(f"      ⚠️ No bioguide ID for {name}")
        return None
    
    # Format: https://www.quiverquant.com/congresstrading/politician/FirstName%20LastName-BIOGUIDE
    full_name = f"{first_name} {last_name}"
    encoded_name = urllib.parse.quote(full_name)
    quiver_url = f"https://www.quiverquant.com/congresstrading/politician/{encoded_name}-{bioguide_id}"
    
    return quiver_url


def validate_quiver_url(url):
    """Tikrina ar QuiverQuant URL veikia"""
    if not url or "quiverquant.com" not in url:
        return False
    
    print(f"      🔗 Quiver check...", end=" ")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.head(url, timeout=8, headers=headers, allow_redirects=True)
        if r.status_code < 400:
            print(f"✅ OK ({r.status_code})")
            return True
        else:
            print(f"❌ {r.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout")
        return False
    except Exception as e:
        print(f"❌ {str(e)[:30]}")
        return False


def is_valid_url(url):
    """Tikrina ar URL yra valid format"""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("http"):
        return False
    for blocked in BLOCKED_PATTERNS:
        if blocked in url:
            return False
    return True


def check_url_accessible(url, timeout=10):
    """Tikrina ar URL accessible (non-blocking check)"""
    if not is_valid_url(url):
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        return r.status_code < 400
    except requests.exceptions.Timeout:
        print(f"      ⏱️ Timeout: {url}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"      ❌ Connection error: {url}")
        return False
    except Exception as e:
        print(f"      ⚠️ Error: {url[:60]} - {str(e)[:40]}")
        return False


def extract_domain(url):
    """Ištraukia domain iš URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except:
        return None


def get_alternative_url(url, name=""):
    """Jei URL broken, siūlo alternative iš trusted sources"""
    domain = extract_domain(url)
    
    # Jei domain yra trusted ir veikia, sukuriam homepage URL
    if domain:
        for trusted_domain, trusted_url in TRUSTED_SOURCES.items():
            if trusted_domain in domain:
                print(f"      → Naudosime trusted: {trusted_url}")
                return trusted_url
    
    # Fallback - opensecrets
    if name:
        # Mėginam OpenSecrets dengan name
        alt = f"https://www.opensecrets.org/search?q={name.replace(' ', '+')}"
        print(f"      → OpenSecrets search: {alt}")
        return alt
    
    return None


def fix_sources_field(sources_text, name="", post_id=0):
    """
    Fiksuoja sources field:
    - Kiekviena nuoroda naujoje linijoje
    - Tikrina kiekvieną URL
    - Fiksuoja broken ones
    - Grąžina updated text
    """
    if not sources_text or not isinstance(sources_text, str):
        return sources_text
    
    lines = sources_text.split("\n")
    fixed_lines = []
    changed = False
    
    for i, line in enumerate(lines, 1):
        url = line.strip()
        
        if not url:
            continue
        
        # Quiver special handling - regenerate URL iš bioguide ID
        if "quiverquant.com" in url:
            print(f"      [Source {i}] Quiver: ", end="")
            
            # Pirmiau tikrinam ar veikia current URL
            if check_url_accessible(url, timeout=5):
                print(f"✅ Working")
                fixed_lines.append(url)
                continue
            
            # Broken - pabandyt regeneruoti iš bioguide ID
            print(f"\n        ❌ Broken, regenerating...")
            fresh_quiver = get_quiver_url(name)
            
            if fresh_quiver and validate_quiver_url(fresh_quiver):
                print(f"        ✅ NEW Quiver URL works!")
                fixed_lines.append(fresh_quiver)
                changed = True
                stats["urls_fixed"] += 1
            else:
                print(f"        ⚠️ Can't regenerate - skipping Quiver")
                changed = True
            continue
        
        # Regular URL check
        print(f"      [Source {i}] {url[:60]}...", end=" ")
        
        if not is_valid_url(url):
            print(f"❌ Invalid format")
            changed = True
            # Pabandyt gauti alternativą
            alt = get_alternative_url(url, name)
            if alt:
                fixed_lines.append(alt)
            continue
        
        if check_url_accessible(url, timeout=5):
            print(f"✅ OK")
            fixed_lines.append(url)
        else:
            print(f"❌ BROKEN")
            changed = True
            # Siūlyt alternative
            alt = get_alternative_url(url, name)
            if alt:
                fixed_lines.append(alt)
            else:
                print(f"        → No alternative, skipping")
    
    fixed_text = "\n".join(fixed_lines)
    
    if changed:
        stats["urls_fixed"] += 1
        print(f"      → UPDATED")
        return fixed_text, True
    
    return sources_text, False


def get_all_posts(page=1):
    """Gauna visus posts (scheduled, published, draft)"""
    try:
        res = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts",
            params={
                "per_page": 100,
                "page": page,
                "status": ["publish", "future", "draft"],  # All statuses
                "order": "desc",
                "orderby": "modified",
            },
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        if res.status_code == 200:
            return res.json(), res.headers.get("X-WP-TotalPages", 1)
        print(f"❌ API Error: {res.status_code}")
        return [], 1
    except Exception as e:
        print(f"❌ Request error: {e}")
        return [], 1


def get_post_full(post_id):
    """Gauna full post data su ACF fields"""
    try:
        res = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts/{post_id}?acf_format=standard",
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print(f"  ❌ Failed to fetch post {post_id}: {e}")
        return None


def update_post(post_id, payload):
    """Atnaujina post ACF fields"""
    try:
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
            json=payload,
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        if res.status_code == 200:
            return True
        print(f"    ❌ Update failed {res.status_code}: {res.text[:200]}")
        return False
    except Exception as e:
        print(f"    ❌ Update error: {e}")
        return False


def process_post(post_data):
    """Apdoroja vieną postą"""
    post_id = post_data.get("id")
    title = post_data.get("title", {})
    if isinstance(title, dict):
        title = title.get("rendered", "Unknown")
    
    acf = post_data.get("acf", {})
    sources = acf.get("sources", "")
    job_title = acf.get("job_title", "")
    
    stats["total_posts"] += 1
    
    if not sources:
        return False
    
    stats["with_sources"] += 1
    
    print(f"\n📄 {post_id} - {title[:50]}")
    print(f"  👤 {job_title}")
    print(f"  🔗 Sources ({len(sources.split(chr(10)))} lines)")
    
    # Fix sources
    fixed_sources, changed = fix_sources_field(sources, name=title, post_id=post_id)
    
    if not changed:
        print(f"  ✅ All sources OK")
        return False
    
    # Atnaujinti WordPress
    print(f"  📤 Updating WordPress...")
    update_payload = {
        "acf": {
            "sources": fixed_sources
        }
    }
    
    if update_post(post_id, update_payload):
        stats["posts_updated"] += 1
        print(f"  ✅ UPDATED")
        return True
    
    return False


def main():
    print(f"🔍 Scaningas WordPress posts...\n")
    
    total_pages = 1
    page = 1
    
    while page <= total_pages:
        print(f"\n📖 Page {page}/{total_pages}")
        posts, total_pages = get_all_posts(page=page)
        
        if not posts:
            print("  ❌ No posts found")
            break
        
        for post in posts:
            post_full = get_post_full(post["id"])
            if post_full:
                process_post(post_full)
                time.sleep(1)  # Rate limiting
        
        page += 1
    
    # Print summary
    print(f"\n\n{'='*55}")
    print(f"✅ REZULTATAI:")
    print(f"{'='*55}")
    print(f"📊 Total posts: {stats['total_posts']}")
    print(f"🔗 Posts with sources: {stats['with_sources']}")
    print(f"🔧 Posts updated: {stats['posts_updated']}")
    print(f"✔️ DONE!")
    print(f"{'='*55}")


if __name__ == "__main__":
    if not WP_USER or not WP_PASS:
        print("❌ KLAIDA: Set WP_USERNAME and WP_APP_PASS env vars!")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Nutraukta vartotojo")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL: {e}")
        sys.exit(1)
