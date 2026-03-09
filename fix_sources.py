#!/usr/bin/env python3
"""
Fix WordPress Sources v10.1 (Master URLs) - FINAL
- Uses person_urls_research.py data
- Updates ALL posts
- BOTH ACF sources + HTML references
"""

import os, requests, json, re, time, sys
from person_urls_master import PERSON_URLS

sys.stdout.reconfigure(line_buffering=True)

print("=== FIX WORDPRESS SOURCES v10.1 (Master URLs) (FINAL - ALL Posts) ===\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

stats = {"total_posts": 0, "posts_updated": 0, "posts_skipped": 0}

def extract_name_from_title(title):
    title = re.sub(r'\s*Net Worth.*', '', title, flags=re.IGNORECASE).strip()
    return title

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
    except Exception as e:
        print(f"  Error getting posts: {e}")
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
    except Exception as e:
        print(f"    Update error: {e}")
        return False

def update_html_references(html_content, sources):
    """Update HTML references section"""
    if not sources or "references-section" not in html_content:
        return html_content, False
    
    new_items = []
    for source in sources:
        new_items.append(f'<li><a href="{source["url"]}" target="_blank" rel="nofollow noopener">{source["label"]}</a></li>')
    
    new_list = "\n".join(new_items)
    
    # Find <ul>...</ul> in references section
    ref_pattern = r'(<div class="references-section">.*?<ul>)(.*?)(</ul>)'
    match = re.search(ref_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    if match:
        new_html = html_content[:match.start(2)] + new_list + html_content[match.end(2):]
        return new_html, new_html != html_content
    
    return html_content, False

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
    print(f"  👤 {name}")
    
    # Get URLs for this person
    if name not in PERSON_URLS:
        print(f"  ⚠️ No data found - SKIPPING")
        stats["posts_skipped"] += 1
        return
    
    sources = PERSON_URLS[name]
    if not sources:
        print(f"  ❌ No sources - SKIPPING")
        stats["posts_skipped"] += 1
        return
    
    print(f"  🔗 Found {len(sources)} sources")
    print(f"  📤 Updating...")
    
    # Update ACF
    acf_sources = "\n".join([s["url"] for s in sources])
    if update_post(post_id, {"acf": {"sources": acf_sources}}):
        print(f"    ✅ ACF updated")
    
    # Update HTML
    new_html, changed = update_html_references(html_content, sources)
    if changed:
        if update_post(post_id, {"content": new_html}):
            print(f"    ✅ HTML updated")
    
    stats["posts_updated"] += 1
    print(f"  ✅ UPDATED")

def main():
    print(f"🔍 Scanning ALL posts...\n")
    
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
                time.sleep(0.5)
        
        page += 1
    
    print(f"\n\n{'='*70}")
    print(f"✅ FINAL RESULTS (v10.1 (Master URLs)):")
    print(f"{'='*70}")
    print(f"📊 Total posts: {stats['total_posts']}")
    print(f"✅ Updated: {stats['posts_updated']}")
    print(f"⚠️ Skipped: {stats['posts_skipped']}")
    print(f"{'='*70}")

if __name__ == "__main__":
    if not WP_USER or not WP_PASS:
        print("❌ Set WP_USERNAME and WP_APP_PASS!")
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
