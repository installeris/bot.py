#!/usr/bin/env python3
"""
Fix WordPress Sources URLs v5.0 - FINAL VERSION
- ONLY validuoja existing URLs - ar veikia?
- Jei URL WORKS → PALIK
- Jei URL BROKEN → PAŠALINTI
- NO fake/search URLs, NO replacements
- SAFE: neliečiam sources jei nėra oficialių
"""

import os, requests, json, re, time, sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log_file, "w") as f:
    f.write(f"=== FIX WORDPRESS SOURCES v5.0 (FINAL - Validate & Remove Only) ===\nStarted: {datetime.now()}\n\n")

print("=== FIX WORDPRESS SOURCES v5.0 (FINAL - Validate Only, Remove Broken) ===\n")
print(f"📝 Logs: {log_file}\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

# ✅ OFFICIAL sources ONLY
OFFICIAL_SOURCES = [
    "opensecrets.org",
    "senate.gov",
    "house.gov",
    "ballotpedia.org",
    "forbes.com",
    "bloomberg.com",
    "reuters.com",
    "apnews.com",
    "cnbc.com",
    "businessinsider.com",
    "washingtonpost.com",
    "nytimes.com",
    "politico.com",
    "quiverquant.com",
    "celebritynetworth.com",
]

BLOCKED_PATTERNS = [
    "vertexaisearch", "googleapis.com", "google.com",
    "youtube.com", "twitter.com", "x.com/",
    "facebook.com", "instagram.com", "tiktok.com", "reddit.com", "wikipedia.org",
]

stats = {
    "total_posts": 0,
    "posts_with_sources": 0,
    "urls_checked": 0,
    "urls_valid": 0,
    "urls_broken": 0,
    "posts_updated": 0,
}

# ═════════════════════════════════════════════════════════════
# STRICT VALIDATION ONLY
# ═════════════════════════════════════════════════════════════

def is_official_source(url):
    """Tikrina ar URL iš oficialaus šaltinio"""
    if not url:
        return False
    url_lower = url.lower()
    
    # Check if from blocked
    for blocked in BLOCKED_PATTERNS:
        if blocked in url_lower:
            return False
    
    # Check if from official
    for official in OFFICIAL_SOURCES:
        if official in url_lower:
            return True
    
    return False


def is_url_really_working(url, timeout=10):
    """
    ⭐ STRICT check - ar URL REALLY veikia?
    - GET request
    - HTTP < 400
    - Content > 1KB
    - NO 404/error text
    - NO search pages
    """
    if not url or not isinstance(url, str):
        print(f"    Invalid format", end=" ")
        return False
    
    if not is_official_source(url):
        print(f"    Not official source", end=" ")
        return False
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        # Status check
        if r.status_code >= 400:
            print(f"    HTTP {r.status_code}", end=" ")
            return False
        
        content = r.text.lower()
        
        # Error indicators
        if any(err in content for err in ["404", "not found", "page not found", "doesn't exist"]):
            print(f"    404 text", end=" ")
            return False
        
        if "error" in content and len(r.text) < 2000:
            print(f"    Error page", end=" ")
            return False
        
        # Content size
        if len(r.text) < 1000:
            print(f"    Too small", end=" ")
            return False
        
        # Search result
        if "search" in url.lower() and "q=" in url.lower():
            print(f"    Search page", end=" ")
            return False
        
        # ✅ VALID!
        stats["urls_valid"] += 1
        print(f"    ✅", end=" ")
        return True
        
    except requests.exceptions.Timeout:
        print(f"    Timeout", end=" ")
        return False
    except requests.exceptions.ConnectionError:
        print(f"    No connection", end=" ")
        return False
    except Exception as e:
        print(f"    Error", end=" ")
        return False


# ═════════════════════════════════════════════════════════════
# CLEAN SOURCES - REMOVE BROKEN ONLY
# ═════════════════════════════════════════════════════════════

def validate_sources_field(sources_text):
    """
    Validuojame ACF sources:
    - Kiekvieną URL tikriname
    - Jei WORKS → palikti
    - Jei BROKEN → PAŠALINTI
    - NO replacements
    """
    if not sources_text:
        return sources_text, False
    
    lines = sources_text.split("\n")
    valid_lines = []
    changed = False
    
    for i, line in enumerate(lines, 1):
        url = line.strip()
        
        if not url:
            continue
        
        print(f"      [{i}] {url[:70]}", end=" ")
        stats["urls_checked"] += 1
        
        if is_url_really_working(url, timeout=8):
            valid_lines.append(url)
            print()
        else:
            print()
            stats["urls_broken"] += 1
            changed = True
            # ❌ Pašalinu, ne keičiu!
    
    result = "\n".join(valid_lines)
    return result, changed


# ═════════════════════════════════════════════════════════════
# HTML REFERENCES
# ═════════════════════════════════════════════════════════════

def validate_html_references(html_content):
    """
    Validuojame HTML <a href> links
    Jei WORKS → palikti
    Jei BROKEN → PAŠALINTI
    """
    if not html_content or "references-section" not in html_content:
        return html_content, False
    
    changed = False
    
    # Find <li><a href="...">...</a></li>
    link_pattern = r'<li>\s*<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>\s*</li>'
    links = re.findall(link_pattern, html_content)
    
    print(f"      Found {len(links)} links")
    
    for i, (url, label) in enumerate(links, 1):
        print(f"      [{i}] {url[:70]}", end=" ")
        stats["urls_checked"] += 1
        
        if is_url_really_working(url, timeout=8):
            print()
        else:
            print()
            stats["urls_broken"] += 1
            changed = True
            
            # ❌ Remove entire <li>...</li>
            pattern = f'<li>\\s*<a\\s+href=["\']({re.escape(url)})["\'][^>]*>[^<]*</a>\\s*</li>'
            html_content = re.sub(pattern, '', html_content)
    
    return html_content, changed


# ═════════════════════════════════════════════════════════════
# WORDPRESS API
# ═════════════════════════════════════════════════════════════

def get_all_posts(page=1):
    """Get posts"""
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
    """Get post"""
    try:
        res = requests.get(f"{WP_BASE_URL}/wp/v2/posts/{post_id}?acf_format=standard", auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except:
        return None


def update_post(post_id, payload):
    """Update post"""
    try:
        res = requests.post(f"{WP_BASE_URL}/wp/v2/posts/{post_id}", json=payload, auth=(WP_USER, WP_PASS), timeout=WP_TIMEOUT)
        return res.status_code == 200
    except:
        return False


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════

def process_post(post_data):
    """Process post"""
    post_id = post_data.get("id")
    title = post_data.get("title", {})
    if isinstance(title, dict):
        title = title.get("rendered", "Unknown")
    
    acf = post_data.get("acf", {})
    sources = acf.get("sources", "")
    
    content = post_data.get("content", {})
    html_content = content.get("raw", "") if isinstance(content, dict) else content
    
    stats["total_posts"] += 1
    print(f"\n📄 {post_id} - {title[:50]}")
    
    acf_updated = False
    html_updated = False
    
    # ACF SOURCES
    if sources:
        stats["posts_with_sources"] += 1
        print(f"  🔗 ACF Sources ({len(sources.split(chr(10)))} lines)")
        cleaned, changed = validate_sources_field(sources)
        
        if changed:
            print(f"    📤 Updating (removing broken)...")
            acf_updated = update_post(post_id, {"acf": {"sources": cleaned}})
            if acf_updated:
                print(f"    ✅ ACF Updated")
    
    # HTML REFERENCES
    if html_content and "references-section" in html_content:
        print(f"  📄 HTML References")
        cleaned_html, changed = validate_html_references(html_content)
        
        if changed:
            print(f"    📤 Updating (removing broken)...")
            html_updated = update_post(post_id, {"content": cleaned_html})
            if html_updated:
                print(f"    ✅ HTML Updated")
    
    if acf_updated or html_updated:
        stats["posts_updated"] += 1
        print(f"  ✅ POST UPDATED")


def main():
    print(f"🔍 Scanning posts (FINAL MODE - Validate & Remove Broken Only)...\n")
    
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
    print(f"✅ FINAL RESULTS (v5.0 - Validation Only):")
    print(f"{'='*70}")
    print(f"📊 Posts scanned: {stats['total_posts']}")
    print(f"🔗 Posts with sources: {stats['posts_with_sources']}")
    print(f"🔗 URLs checked: {stats['urls_checked']}")
    print(f"✅ URLs valid (kept): {stats['urls_valid']}")
    print(f"❌ URLs broken (removed): {stats['urls_broken']}")
    print(f"🔧 Posts updated: {stats['posts_updated']}")
    print(f"{'='*70}")
    print(f"📋 Strategy:")
    print(f"   ✅ Keep working official URLs")
    print(f"   ❌ Remove broken URLs")
    print(f"   ⛔ NO replacements, NO search results")
    print(f"   ⛔ ONLY official sources (opensecrets, senate.gov, house.gov, etc)")
    print(f"{'='*70}")


if __name__ == "__main__":
    if not WP_USER or not WP_PASS:
        print("❌ Set WP_USERNAME and WP_APP_PASS env vars!")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
