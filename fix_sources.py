#!/usr/bin/env python3
"""
Fix WordPress Sources URLs v3.1
- Validuoja ir fiksuoja sulaužytas nuorodas WordPress
- Pereina PER VISUS posts (scheduled, published, draft)
- Tikrina 'sources' ACF field IR HTML references
- QuiverQuant regeneracija iš bioguide ID
"""

import os, requests, json, re, time, sys, urllib.parse
from datetime import datetime
from urllib.parse import urlparse

sys.stdout.reconfigure(line_buffering=True)

# Setup logging
log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log_file, "w") as f:
    f.write(f"=== FIX WORDPRESS SOURCES v3.1 ===\nStarted: {datetime.now()}\n\n")

print("=== FIX WORDPRESS SOURCES v3.1 (Full HTML + QuiverQuant) ===\n")
print(f"📝 Logs saved to: {log_file}\n")

# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

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
    "celebritynetworth.com": "https://www.celebritynetworth.com/",
}

BLOCKED_PATTERNS = [
    "vertexaisearch", "googleapis.com", "google.com/search",
    "youtube.com/watch", "twitter.com", "x.com/",
    "facebook.com", "instagram.com", "tiktok.com", "reddit.com", "wikipedia.org",
]

stats = {
    "total_posts": 0,
    "posts_with_acf": 0,
    "posts_with_html": 0,
    "posts_updated": 0,
}

# ═════════════════════════════════════════════════════════════
# HELPERS - PRIEŠ VISOS KITOS FUNKCIJOS!
# ═════════════════════════════════════════════════════════════

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


def extract_domain(url):
    """Ištraukia domain iš URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except:
        return None


def check_url_accessible(url, timeout=10):
    """Tikrina ar URL accessible"""
    if not is_valid_url(url):
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        return r.status_code < 400
    except:
        return False


def get_alternative_url(url, name=""):
    """Jei URL broken, siūlo alternative"""
    domain = extract_domain(url)
    
    if domain:
        for trusted_domain, trusted_url in TRUSTED_SOURCES.items():
            if trusted_domain in domain:
                print(f"      → Trusted: {trusted_url}")
                return trusted_url
    
    if name:
        alt = f"https://www.opensecrets.org/search?q={name.replace(' ', '+')}"
        print(f"      → OpenSecrets: {alt}")
        return alt
    
    return None


def get_quiver_url(name):
    """Kuria fresh QuiverQuant URL"""
    if name not in BIOGUIDE_MAP:
        return None
    
    first_name, last_name, bioguide_id = BIOGUIDE_MAP[name]
    
    if not bioguide_id:
        return None
    
    full_name = f"{first_name} {last_name}"
    encoded_name = urllib.parse.quote(full_name)
    quiver_url = f"https://www.quiverquant.com/congresstrading/politician/{encoded_name}-{bioguide_id}"
    
    return quiver_url


def validate_quiver_url(url):
    """Tikrina ar QuiverQuant URL veikia"""
    if not url or "quiverquant.com" not in url:
        return False
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.head(url, timeout=8, headers=headers, allow_redirects=True)
        return r.status_code < 400
    except:
        return False


# ═════════════════════════════════════════════════════════════
# ACF SOURCES FIX
# ═════════════════════════════════════════════════════════════

def fix_sources_field(sources_text, name=""):
    """Fiksuoja sources ACF field"""
    if not sources_text:
        return sources_text, False
    
    lines = sources_text.split("\n")
    fixed_lines = []
    changed = False
    
    for i, line in enumerate(lines, 1):
        url = line.strip()
        
        if not url:
            continue
        
        # Quiver special handling
        if "quiverquant.com" in url:
            print(f"      [Source {i}] Quiver: ", end="")
            
            if check_url_accessible(url, timeout=5):
                print(f"✅ OK")
                fixed_lines.append(url)
                continue
            
            print(f"\n        ❌ Broken, regenerating...")
            fresh_quiver = get_quiver_url(name)
            
            if fresh_quiver and validate_quiver_url(fresh_quiver):
                print(f"        ✅ NEW Quiver URL works!")
                fixed_lines.append(fresh_quiver)
                changed = True
            else:
                print(f"        ⚠️ Can't regenerate - skipping")
                changed = True
            continue
        
        # Regular URL
        print(f"      [Source {i}] {url[:50]}...", end=" ")
        
        if not is_valid_url(url):
            print(f"❌ Invalid")
            changed = True
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
            alt = get_alternative_url(url, name)
            if alt:
                fixed_lines.append(alt)
    
    return "\n".join(fixed_lines), changed


# ═════════════════════════════════════════════════════════════
# HTML REFERENCES FIX
# ═════════════════════════════════════════════════════════════

def fix_html_references(html_content, name=""):
    """Fiksuoja broken URLs HTML content'e"""
    if not html_content or "references-section" not in html_content:
        return html_content, False
    
    changed = False
    
    # Rindi <li><a href="...">...</a></li> patterns
    link_pattern = r'<li>\s*<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>\s*</li>'
    links = re.findall(link_pattern, html_content)
    
    print(f"      Found {len(links)} references")
    
    for i, (url, label) in enumerate(links, 1):
        print(f"      [Ref {i}] {url[:50]}...", end=" ")
        
        if not is_valid_url(url):
            print(f"❌ Invalid")
            continue
        
        if check_url_accessible(url, timeout=5):
            print(f"✅ OK")
        else:
            print(f"❌ BROKEN")
            changed = True
            
            alt = get_alternative_url(url, name)
            if alt:
                old_link = f'href="{url}"'
                new_link = f'href="{alt}"'
                html_content = html_content.replace(old_link, new_link)
                print(f"        → Fixed")
    
    return html_content, changed


# ═════════════════════════════════════════════════════════════
# WORDPRESS API
# ═════════════════════════════════════════════════════════════

def get_all_posts(page=1):
    """Gauna visus posts"""
    try:
        res = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts",
            params={
                "per_page": 100,
                "page": page,
                "status": "publish,future,draft",
                "order": "desc",
                "orderby": "modified",
            },
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        if res.status_code == 200:
            total_pages = int(res.headers.get("X-WP-TotalPages", 1))
            return res.json(), total_pages
        print(f"❌ API Error: {res.status_code}")
        return [], 1
    except Exception as e:
        print(f"❌ Request error: {e}")
        return [], 1


def get_post_full(post_id):
    """Gauna full post data"""
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
        print(f"  ❌ Failed to fetch post {post_id}")
        return None


def update_post(post_id, payload):
    """Atnaujina post"""
    try:
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
            json=payload,
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        return res.status_code == 200
    except Exception as e:
        print(f"    ❌ Update error: {e}")
        return False


# ═════════════════════════════════════════════════════════════
# MAIN LOGIC
# ═════════════════════════════════════════════════════════════

def process_post(post_data):
    """Apdoroja vieną postą"""
    post_id = post_data.get("id")
    title = post_data.get("title", {})
    if isinstance(title, dict):
        title = title.get("rendered", "Unknown")
    
    acf = post_data.get("acf", {})
    sources = acf.get("sources", "")
    
    content = post_data.get("content", {})
    if isinstance(content, dict):
        html_content = content.get("raw", "")
    else:
        html_content = content
    
    stats["total_posts"] += 1
    
    print(f"\n📄 {post_id} - {title[:50]}")
    
    acf_updated = False
    html_updated = False
    
    # ACF SOURCES
    if sources:
        stats["posts_with_acf"] += 1
        print(f"  🔗 ACF Sources ({len(sources.split(chr(10)))} lines)")
        fixed_sources, changed = fix_sources_field(sources, name=title)
        
        if changed:
            acf_updated = True
            print(f"    📤 Updating ACF...")
            update_post(post_id, {"acf": {"sources": fixed_sources}})
    
    # HTML REFERENCES
    if html_content and "references-section" in html_content:
        stats["posts_with_html"] += 1
        print(f"  📄 HTML References")
        fixed_html, changed = fix_html_references(html_content, name=title)
        
        if changed:
            html_updated = True
            print(f"    📤 Updating HTML...")
            update_post(post_id, {"content": fixed_html})
    
    # Summary
    if acf_updated or html_updated:
        stats["posts_updated"] += 1
        print(f"  ✅ UPDATED")
        return True
    
    return False


def main():
    print(f"🔍 Scanning WordPress posts...\n")
    
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
                time.sleep(1)
        
        page += 1
    
    # Summary
    print(f"\n\n{'='*55}")
    print(f"✅ REZULTATAI:")
    print(f"{'='*55}")
    print(f"📊 Total posts: {stats['total_posts']}")
    print(f"🔗 Posts with ACF sources: {stats['posts_with_acf']}")
    print(f"📄 Posts with HTML references: {stats['posts_with_html']}")
    print(f"🔧 Posts updated: {stats['posts_updated']}")
    print(f"{'='*55}")


if __name__ == "__main__":
    if not WP_USER or not WP_PASS:
        print("❌ KLAIDA: Set WP_USERNAME and WP_APP_PASS env vars!")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
