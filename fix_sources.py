#!/usr/bin/env python3
import os, requests, json, re, time, sys, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)
log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log_file, "w") as f:
    f.write(f"=== FIX WORDPRESS SOURCES v7.0 ===\n")

print("=== FIX WORDPRESS SOURCES v7.0 (Smart Person-Specific URLs) ===\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

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
}

stats = {"total_posts": 0, "posts_updated": 0, "urls_tested": 0, "urls_valid": 0}

def extract_name_from_title(title):
    title = re.sub(r'\s+Net Worth\s+\d{4}:.*', '', title, flags=re.IGNORECASE)
    return title.strip()

def build_forbes_url(name):
    slug = name.lower().replace(" ", "-")
    return f"https://www.forbes.com/profile/{slug}/"

def build_opensecrets_url(name):
    encoded = urllib.parse.quote(name)
    return f"https://www.opensecrets.org/search?q={encoded}"

def build_ballotpedia_url(name):
    slug = name.replace(" ", "_")
    return f"https://ballotpedia.org/{slug}"

def build_quiverquant_url(name):
    if name not in BIOGUIDE_MAP:
        return None
    first_name, last_name, bioguide_id = BIOGUIDE_MAP[name]
    if not bioguide_id:
        return None
    full_name = f"{first_name} {last_name}"
    encoded_name = urllib.parse.quote(full_name)
    return f"https://www.quiverquant.com/congresstrading/politician/{encoded_name}-{bioguide_id}/"

def is_url_working(url, timeout=10):
    if not url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        if r.status_code >= 400:
            print(f"        HTTP {r.status_code}", end=" ")
            return False
        content = r.text.lower()
        if any(err in content for err in ["404", "not found", "error 500", "server error"]):
            print(f"        Error page", end=" ")
            return False
        if len(r.text) < 1000:
            print(f"        Too small", end=" ")
            return False
        stats["urls_valid"] += 1
        print(f"        ✅", end=" ")
        return True
    except:
        print(f"        Error", end=" ")
        return False

def build_sources_for_person(name):
    print(f"  🔗 Building sources for: {name}")
    sources = []
    
    url = build_forbes_url(name)
    print(f"      Forbes: {url[:60]}", end=" ")
    stats["urls_tested"] += 1
    if is_url_working(url, timeout=8):
        sources.append(url)
        print()
    else:
        print()
    
    url = build_opensecrets_url(name)
    print(f"      OpenSecrets: {url[:60]}", end=" ")
    stats["urls_tested"] += 1
    if is_url_working(url, timeout=8):
        sources.append(url)
        print()
    else:
        print()
    
    url = build_ballotpedia_url(name)
    print(f"      Ballotpedia: {url[:60]}", end=" ")
    stats["urls_tested"] += 1
    if is_url_working(url, timeout=8):
        sources.append(url)
        print()
    else:
        print()
    
    url = build_quiverquant_url(name)
    if url:
        print(f"      QuiverQuant: {url[:60]}", end=" ")
        stats["urls_tested"] += 1
        if is_url_working(url, timeout=8):
            sources.append(url)
            print()
        else:
            print()
    else:
        print(f"      QuiverQuant: (not congress member - skipped)")
    
    print(f"  Result: {len(sources)} working sources")
    return sources

def update_html_references(html_content, sources):
    if not sources or "references-section" not in html_content:
        return html_content
    
    label_map = {
        "forbes.com": "Forbes – Wealth Estimate",
        "opensecrets.org": "OpenSecrets – Personal Finances",
        "ballotpedia.org": "Ballotpedia – Political Biography",
        "quiverquant.com": "Quiver Quantitative – Congress Trading",
    }
    
    new_items = []
    for url in sources:
        label = None
        for domain, lbl in label_map.items():
            if domain in url:
                label = lbl
                break
        if not label:
            label = url.split("/")[2]
        new_items.append(f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{label}</a></li>')
    
    new_list = "\n".join(new_items)
    ref_pattern = r'(<ul>)(.*?)(</ul>)'
    match = re.search(ref_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    if match:
        return html_content[:match.start(2)] + new_list + html_content[match.end(2):]
    return html_content

def get_all_posts(page=1):
    try:
        res = requests.get(f"{WP_BASE_URL}/wp/v2/posts", params={"per_page": 100, "page": page, "status": "publish,future,draft", "order": "desc", "orderby": "modified"}, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
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
        print(f"  ❌ No working sources found")
        return
    
    print(f"  📤 Updating...")
    
    acf_sources = "\n".join(sources)
    if update_post(post_id, {"acf": {"sources": acf_sources}}):
        print(f"    ✅ ACF Updated")
    
    if html_content and "references-section" in html_content:
        new_html = update_html_references(html_content, sources)
        if new_html != html_content:
            if update_post(post_id, {"content": new_html}):
                print(f"    ✅ HTML References Updated")
    
    stats["posts_updated"] += 1
    print(f"  ✅ POST UPDATED")

def main():
    print(f"🔍 Scanning posts (v7.0)...\n")
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
    print(f"✅ RESULTS (v7.0):")
    print(f"{'='*70}")
    print(f"📊 Posts: {stats['total_posts']}")
    print(f"✅ URLs valid: {stats['urls_valid']}/{stats['urls_tested']}")
    print(f"🔧 Posts updated: {stats['posts_updated']}")
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
