#!/usr/bin/env python3
"""
Fix WordPress Sources v14.0 - FINAL
- Uses build_references_html() from bot.py
- Updates BOTH ACF sources + HTML references
"""

import os, requests, json, re, time, sys
from datetime import datetime
from person_urls_master import PERSON_URLS

sys.stdout.reconfigure(line_buffering=True)

print("=== FIX WORDPRESS SOURCES v14.0 (Using bot.py references) ===\n")

WP_USER = os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT = 30

stats = {"total_posts": 0, "posts_updated": 0, "acf_updated": 0, "html_updated": 0, "html_created": 0}

def extract_name_from_title(title):
    title = re.sub(r'\s*Net Worth.*', '', title, flags=re.IGNORECASE).strip()
    return title

def is_valid_source_url(url):
    """From bot.py"""
    url = url.strip()
    if not url or not url.startswith("http"):
        return False
    blocked = ["vertexaisearch", "googleapis.com", "google.com/search",
               "gstatic.com", "googleusercontent.com", "youtube.com/watch",
               "twitter.com", "x.com/", "facebook.com", "instagram.com", "tiktok.com",
               "reddit.com", "wikipedia.org"]
    for b in blocked:
        if b in url:
            return False
    return True

def build_references_html(urls):
    """Exact copy from bot.py"""
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

def update_html_with_references(html_content, urls):
    """
    Remove old references-section and add new one from build_references_html()
    """
    if not urls:
        return html_content, False
    
    new_references = build_references_html(urls)
    if not new_references:
        return html_content, False
    
    # Remove old references-section if exists
    pattern = r'<hr[^>]*>[\s\n]*<div class="references-section">.*?</div>'
    new_html = re.sub(pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Add new references at end
    new_html = new_html.rstrip() + "\n\n" + new_references
    
    return new_html, new_html != html_content

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
        print(f"  ⚠️ No data - SKIPPING")
        return
    
    sources = PERSON_URLS[name]
    if not sources:
        print(f"  ❌ No sources - SKIPPING")
        return
    
    print(f"  🔗 {len(sources)} sources")
    
    updated = False
    
    # 1. Update ACF sources
    print(f"  📝 ACF...", end=" ")
    acf_sources = "\n".join([s["url"] for s in sources])
    if update_post(post_id, {"acf": {"sources": acf_sources}}):
        print(f"✅", end=" ")
        stats["acf_updated"] += 1
        updated = True
    else:
        print(f"❌", end=" ")
    
    # 2. Update HTML references using bot.py function
    print(f"HTML...", end=" ")
    urls = [s["url"] for s in sources]
    new_html, changed = update_html_with_references(html_content, urls)
    if changed:
        if update_post(post_id, {"content": new_html}):
            print(f"✅ UPDATED", end=" ")
            stats["html_updated"] += 1
            updated = True
        else:
            print(f"❌", end=" ")
    else:
        print(f"⚠️", end=" ")
    
    print()
    
    if updated:
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
    print(f"✅ FINAL RESULTS (v14.0):")
    print(f"{'='*70}")
    print(f"📊 Total posts: {stats['total_posts']}")
    print(f"✅ Posts updated: {stats['posts_updated']}")
    print(f"  📝 ACF updated: {stats['acf_updated']}")
    print(f"  📄 HTML updated: {stats['html_updated']}")
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
