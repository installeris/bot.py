#!/usr/bin/env python3
import os, requests, json, re, time, sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log_file, "w") as f:
    f.write(f"=== FIX WORDPRESS SOURCES v6.0 ===\nStarted: {datetime.now()}\n\n")

print("=== FIX WORDPRESS SOURCES v6.0 (Validate + Add Official URLs) ===\n")
print(f"📝 Logs: {log_file}\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

OFFICIAL_SOURCES = {
    "opensecrets.org": ["https://www.opensecrets.org/", "https://www.opensecrets.org/personal-finances/"],
    "ballotpedia.org": ["https://ballotpedia.org/"],
    "forbes.com": ["https://www.forbes.com/"],
    "senate.gov": ["https://www.senate.gov/"],
    "house.gov": ["https://www.house.gov/"],
}

BLOCKED_PATTERNS = ["vertexaisearch", "googleapis.com", "google.com", "youtube.com", "twitter.com", "x.com/", "facebook.com", "instagram.com", "tiktok.com", "reddit.com", "wikipedia.org"]

stats = {"total_posts": 0, "posts_with_sources": 0, "posts_updated": 0, "sources_removed": 0, "sources_added": 0}

def is_official_source(url):
    if not url:
        return False
    url_lower = url.lower()
    for blocked in BLOCKED_PATTERNS:
        if blocked in url_lower:
            return False
    for official in OFFICIAL_SOURCES.keys():
        if official in url_lower:
            return True
    return False

def is_url_really_working(url, timeout=10):
    if not url or not isinstance(url, str):
        return False
    if not is_official_source(url):
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        if r.status_code >= 400:
            return False
        content = r.text.lower()
        if any(err in content for err in ["404", "not found", "page not found", "doesn't exist"]):
            return False
        if len(r.text) < 1000:
            return False
        return True
    except:
        return False

def get_working_official_urls():
    working = []
    print("  🔍 Finding working official sources...")
    for domain, urls in OFFICIAL_SOURCES.items():
        for url in urls:
            print(f"      Testing {domain}...", end=" ")
            if is_url_really_working(url, timeout=5):
                print(f"✅")
                working.append(url)
                break
            else:
                print(f"❌")
    return working

def fix_sources_field(sources_text, name=""):
    print(f"  🔗 Processing sources...")
    lines = sources_text.split("\n") if sources_text else []
    valid_lines = []
    for line in lines:
        url = line.strip()
        if not url:
            continue
        print(f"      Checking: {url[:60]}", end=" ")
        if is_url_really_working(url, timeout=8):
            print(f"✅")
            valid_lines.append(url)
        else:
            print(f"❌ Removed")
            stats["sources_removed"] += 1
    
    if len(valid_lines) < 3:
        print(f"  ➕ Adding official sources (have {len(valid_lines)}, need 3+)...")
        working_urls = get_working_official_urls()
        for url in working_urls:
            if url not in valid_lines:
                valid_lines.append(url)
                print(f"      Added: {url}")
                stats["sources_added"] += 1
            if len(valid_lines) >= 4:
                break
    
    result = "\n".join(valid_lines[:4])
    changed = (result != sources_text)
    print(f"  Result: {len(valid_lines)} sources")
    return result, changed

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
    sources = acf.get("sources", "")
    stats["total_posts"] += 1
    print(f"\n📄 {post_id} - {title[:50]}")
    stats["posts_with_sources"] += 1
    cleaned, changed = fix_sources_field(sources, name=title)
    if cleaned or changed:
        print(f"  📤 Updating sources...")
        if update_post(post_id, {"acf": {"sources": cleaned}}):
            stats["posts_updated"] += 1
            print(f"  ✅ UPDATED")

def main():
    print(f"🔍 Scanning posts (v6.0 - Validate & Add Sources)...\n")
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
    print(f"✅ RESULTS (v6.0):")
    print(f"{'='*70}")
    print(f"📊 Posts scanned: {stats['total_posts']}")
    print(f"❌ Broken removed: {stats['sources_removed']}")
    print(f"➕ Official added: {stats['sources_added']}")
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
