#!/usr/bin/env python3
import os, requests, json, re, time, sys, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)
log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

print("=== FIX WORDPRESS SOURCES v8.0 (FINAL - Real Working URLs) ===\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

# Only REAL working sources
SOURCES_CONFIG = {
    "opensecrets": {
        "name": "OpenSecrets – Personal Finances",
        "url_template": lambda name: f"https://www.opensecrets.org/search?q={name.replace(' ', '+')}"
    },
    "ballotpedia": {
        "name": "Ballotpedia – Political Biography",
        "url_template": lambda name: f"https://ballotpedia.org/{name.replace(' ', '_')}"
    },
}

BIOGUIDE_MAP = {
    "Joe Biden": ("Joe", "Biden", "B000444"),
    "Kamala Harris": ("Kamala D.", "Harris", "H001075"),
    "Nancy Pelosi": ("Nancy", "Pelosi", "P000197"),
    "Bernie Sanders": ("Bernard", "Sanders", "S000033"),
    "Alexandria Ocasio-Cortez": ("Alexandria", "Ocasio-Cortez", "O000172"),
    "Ron DeSantis": ("Ron", "DeSantis", "D000621"),
    "Nikki Haley": ("Nikki", "Haley", "H001066"),
    "Marco Rubio": ("Marco", "Rubio", "R000595"),
    "Tulsi Gabbard": ("Tulsi", "Gabbard", "G000571"),
    "Liz Cheney": ("Liz", "Cheney", "C001109"),
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
    "Rick Scott": ("Rick", "Scott", "S001217"),
}

stats = {"total_posts": 0, "posts_updated": 0, "sources_added": 0}

def extract_name_from_title(title):
    title = re.sub(r'\s*Net Worth.*', '', title, flags=re.IGNORECASE)
    return title.strip()

def is_url_working(url, timeout=10):
    if not url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        if r.status_code >= 400:
            return False
        
        content = r.text.lower()
        if any(err in content for err in ["404", "not found", "error 500"]):
            return False
        
        if len(r.text) < 1000:
            return False
        
        return True
    except:
        return False

def build_sources_for_person(name):
    print(f"  🔗 Building sources for: {name}")
    sources = []
    
    # OpenSecrets
    url = SOURCES_CONFIG["opensecrets"]["url_template"](name)
    print(f"      OpenSecrets: {url[:60]}", end=" ")
    if is_url_working(url, timeout=10):
        print(f"✅")
        sources.append({"url": url, "label": SOURCES_CONFIG["opensecrets"]["name"]})
    else:
        print(f"❌")
    
    # Ballotpedia
    url = SOURCES_CONFIG["ballotpedia"]["url_template"](name)
    print(f"      Ballotpedia: {url[:60]}", end=" ")
    if is_url_working(url, timeout=10):
        print(f"✅")
        sources.append({"url": url, "label": SOURCES_CONFIG["ballotpedia"]["name"]})
    else:
        print(f"❌")
    
    print(f"  Result: {len(sources)} working sources")
    return sources

def update_acf_sources(sources):
    """Format sources for ACF - just URLs, one per line"""
    return "\n".join([s["url"] for s in sources])

def update_html_references(html_content, sources):
    """Update HTML references section with new URLs"""
    if not sources or "references-section" not in html_content:
        return html_content
    
    # Build list items
    new_items = []
    for source in sources:
        new_items.append(f'<li><a href="{source["url"]}" target="_blank" rel="nofollow noopener">{source["label"]}</a></li>')
    
    new_list = "\n".join(new_items)
    
    # Find and replace <ul>...</ul> in references section
    ref_pattern = r'(<div class="references-section">.*?<ul>)(.*?)(</ul>)'
    match = re.search(ref_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    if match:
        return html_content[:match.start(2)] + new_list + html_content[match.end(2):]
    
    return html_content

def get_all_posts(page=1):
    try:
        res = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts",
            params={"per_page": 100, "page": page, "status": "publish,future,draft", "order": "desc", "orderby": "modified"},
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        if res.status_code == 200:
            total_pages = int(res.headers.get("X-WP-TotalPages", 1))
            return res.json(), total_pages
        return [], 1
    except:
        return [], 1

def get_post_full(post_id):
    try:
        res = requests.get(f"{WP_BASE_URL}/wp/v2/posts/{post_id}?acf_format=standard", auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def update_post(post_id, payload):
    try:
        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts/{post_id}", json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        return res.status_code == 200
    except:
        return False

def process_post(post_data):
    post_id = post_data.get("id")
    title = post_data.get("title", {})
    if isinstance(title, dict):
        title = title.get("rendered", "Unknown")
    
    acf = post_data.get("acf", {})
    content = post_data.get("content", {})
    html_content = content.get("raw", "") if isinstance(content, dict) else content
    
    stats["total_posts"] += 1
    print(f"\n📄 {post_id} - {title[:60]}")
    
    name = extract_name_from_title(title)
    print(f"  👤 Person: {name}")
    
    sources = build_sources_for_person(name)
    
    if not sources:
        print(f"  ❌ No working sources found - SKIPPING")
        return
    
    print(f"  📤 Updating BOTH ACF + HTML...")
    
    # Update ACF
    acf_sources = update_acf_sources(sources)
    if update_post(post_id, {"acf": {"sources": acf_sources}}):
        print(f"    ✅ ACF sources updated")
        stats["sources_added"] += 1
    
    # Update HTML
    if html_content and "references-section" in html_content:
        new_html = update_html_references(html_content, sources)
        if new_html != html_content:
            if update_post(post_id, {"content": new_html}):
                print(f"    ✅ HTML references updated")
    
    stats["posts_updated"] += 1
    print(f"  ✅ POST FULLY UPDATED")

def main():
    print(f"🔍 Scanning posts (v8.0 - Real Working URLs)...\n")
    
    total_pages = 1
    page = 1
    
    while page <= total_pages:
        print(f"\n📖 Page {page}/{total_pages}")
        posts, total_pages = get_all_posts(page=page)
        
        if not posts:
            break
        
        for post in posts:
            post_full = get_post_full(post["id"])
            if post_full:
                process_post(post_full)
                time.sleep(1)
        
        page += 1
    
    print(f"\n\n{'='*70}")
    print(f"✅ FINAL RESULTS (v8.0):")
    print(f"{'='*70}")
    print(f"📊 Posts scanned: {stats['total_posts']}")
    print(f"✅ Posts updated: {stats['posts_updated']}")
    print(f"📝 Sources added: {stats['sources_added']}")
    print(f"{'='*70}")
    print(f"📋 Sources Used:")
    print(f"   ✅ OpenSecrets – Personal Finances")
    print(f"   ✅ Ballotpedia – Political Biography")
    print(f"{'='*70}")

if __name__ == "__main__":
    if not WP_USER or not WP_PASS:
        print("❌ Set env vars!")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL: {e}")
        sys.exit(1)
