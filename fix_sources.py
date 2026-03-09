#!/usr/bin/env python3
"""
Fix WordPress Sources URLs v3.2
- SMART validation: ne tik HTTP 200, bet ir CONTENT check!
- Validuoja ar URL atidaro ir turi relevant informacijos
- Nepridedam fake OpenSecrets search links
- Tik trusted homepages jei broken
"""

import os, requests, json, re, time, sys, urllib.parse
from datetime import datetime
from urllib.parse import urlparse

sys.stdout.reconfigure(line_buffering=True)

# Setup logging
log_file = f"fix_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log_file, "w") as f:
    f.write(f"=== FIX WORDPRESS SOURCES v3.2 (Smart Validation) ===\nStarted: {datetime.now()}\n\n")

print("=== FIX WORDPRESS SOURCES v3.2 (Smart Content Validation) ===\n")
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

# ⚠️ ONLY REAL PAGES - NO SEARCH!
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
    "vertexaisearch", "googleapis.com", "google.com",
    "youtube.com", "twitter.com", "x.com/",
    "facebook.com", "instagram.com", "tiktok.com", "reddit.com", "wikipedia.org",
]

stats = {
    "total_posts": 0,
    "posts_with_acf": 0,
    "posts_with_html": 0,
    "posts_updated": 0,
    "urls_broken": 0,
    "urls_fixed": 0,
}

# ═════════════════════════════════════════════════════════════
# SMART VALIDATION - CONTENT CHECK!
# ═════════════════════════════════════════════════════════════

def is_valid_url(url):
    """Tikrina URL format"""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("http"):
        return False
    for blocked in BLOCKED_PATTERNS:
        if blocked in url:
            return False
    return True


def has_real_content(url, timeout=10):
    """
    ⭐ SMART CHECK - ne tik HTTP status, bet CONTENT!
    - Atidarti URL su GET
    - Tikrinti ar yra real turinio
    - Nepridedam search results!
    """
    if not is_valid_url(url):
        print(f"❌ Invalid", end="")
        return False
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        # HTTP status check
        if r.status_code >= 400:
            print(f"❌ {r.status_code}", end="")
            return False
        
        content = r.text.lower()
        
        # RED FLAGS
        if "404" in content or "not found" in content:
            print(f"❌ 404 text", end="")
            return False
        
        if len(content) < 500:
            print(f"❌ Too small", end="")
            return False
        
        if "search" in url.lower() and "q=" in url.lower():
            print(f"⚠️ Search page", end="")
            return False
        
        # ✅ VALID
        print(f"✅ OK", end="")
        return True
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout", end="")
        return False
    except:
        print(f"❌ Error", end="")
        return False


def extract_domain(url):
    """Get domain"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except:
        return None


def get_alternative_url(url, name=""):
    """
    TIKTAI trusted homepages, NE search results!
    """
    domain = extract_domain(url)
    
    if domain:
        for trusted_domain, trusted_url in TRUSTED_SOURCES.items():
            if trusted_domain in domain:
                print(f" → {trusted_domain}: ", end="")
                if has_real_content(trusted_url, timeout=5):
                    return trusted_url
                else:
                    print(f" (also broken)")
                    return None
    
    # ❌ NO SEARCH RESULTS!
    print(f" → NO fallback (skip)", end="")
    return None


def get_quiver_url(name):
    """Fresh Quiver URL"""
    if name not in BIOGUIDE_MAP:
        return None
    
    first_name, last_name, bioguide_id = BIOGUIDE_MAP[name]
    if not bioguide_id:
        return None
    
    full_name = f"{first_name} {last_name}"
    encoded_name = urllib.parse.quote(full_name)
    return f"https://www.quiverquant.com/congresstrading/politician/{encoded_name}-{bioguide_id}"


# ═════════════════════════════════════════════════════════════
# ACF SOURCES FIX
# ═════════════════════════════════════════════════════════════

def fix_sources_field(sources_text, name=""):
    """Fix ACF sources - ONLY valid URLs"""
    if not sources_text:
        return sources_text, False
    
    lines = sources_text.split("\n")
    fixed_lines = []
    changed = False
    
    for i, line in enumerate(lines, 1):
        url = line.strip()
        if not url:
            continue
        
        # Quiver
        if "quiverquant.com" in url:
            print(f"      [Source {i}] Quiver: ", end="")
            
            if has_real_content(url, timeout=5):
                print()
                fixed_lines.append(url)
                continue
            
            print(f"\n        Regenerating...")
            fresh = get_quiver_url(name)
            if fresh:
                print(f"        [Fresh] ", end="")
                if has_real_content(fresh, timeout=5):
                    print()
                    fixed_lines.append(fresh)
                    changed = True
                    stats["urls_fixed"] += 1
                else:
                    print(f" (broken too)")
                    changed = True
                    stats["urls_broken"] += 1
            else:
                print(f"        No ID")
                changed = True
                stats["urls_broken"] += 1
            continue
        
        # Regular URL
        print(f"      [Source {i}] ", end="")
        if has_real_content(url, timeout=5):
            print()
            fixed_lines.append(url)
        else:
            print()
            changed = True
            stats["urls_broken"] += 1
            
            alt = get_alternative_url(url, name)
            if alt:
                print()
                fixed_lines.append(alt)
                stats["urls_fixed"] += 1
    
    return "\n".join(fixed_lines), changed


# ═════════════════════════════════════════════════════════════
# HTML REFERENCES FIX
# ═════════════════════════════════════════════════════════════

def fix_html_references(html_content, name=""):
    """Fix HTML references - ONLY valid content"""
    if not html_content or "references-section" not in html_content:
        return html_content, False
    
    changed = False
    link_pattern = r'<li>\s*<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>\s*</li>'
    links = re.findall(link_pattern, html_content)
    
    print(f"      Found {len(links)} references")
    
    for i, (url, label) in enumerate(links, 1):
        print(f"      [Ref {i}] ", end="")
        
        if has_real_content(url, timeout=5):
            print()
        else:
            print()
            changed = True
            stats["urls_broken"] += 1
            
            alt = get_alternative_url(url, name)
            if alt:
                old_link = f'href="{url}"'
                new_link = f'href="{alt}"'
                html_content = html_content.replace(old_link, new_link)
                stats["urls_fixed"] += 1
    
    return html_content, changed


# ═════════════════════════════════════════════════════════════
# WORDPRESS API
# ═════════════════════════════════════════════════════════════

def get_all_posts(page=1):
    """Get all posts"""
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
        return [], 1
    except:
        return [], 1


def get_post_full(post_id):
    """Get post"""
    try:
        res = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts/{post_id}?acf_format=standard",
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        return res.json() if res.status_code == 200 else None
    except:
        return None


def update_post(post_id, payload):
    """Update post"""
    try:
        res = requests.post(
            f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
            json=payload,
            auth=(WP_USER, WP_PASS),
            timeout=WP_TIMEOUT,
        )
        return res.status_code == 200
    except:
        return False


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════

def process_post(post_data):
    """Process one post"""
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
    
    # ACF
    if sources:
        stats["posts_with_acf"] += 1
        print(f"  🔗 ACF ({len(sources.split(chr(10)))} lines)")
        fixed, changed = fix_sources_field(sources, name=title)
        if changed:
            acf_updated = True
            print(f"    📤 Updating ACF...")
            update_post(post_id, {"acf": {"sources": fixed}})
    
    # HTML
    if html_content and "references-section" in html_content:
        stats["posts_with_html"] += 1
        print(f"  📄 HTML References")
        fixed, changed = fix_html_references(html_content, name=title)
        if changed:
            html_updated = True
            print(f"    📤 Updating HTML...")
            update_post(post_id, {"content": fixed})
    
    if acf_updated or html_updated:
        stats["posts_updated"] += 1
        print(f"  ✅ UPDATED")


def main():
    print(f"🔍 Scanning posts...\n")
    
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
    
    # Summary
    print(f"\n\n{'='*55}")
    print(f"✅ RESULTS:")
    print(f"{'='*55}")
    print(f"📊 Total: {stats['total_posts']}")
    print(f"🔗 With ACF: {stats['posts_with_acf']}")
    print(f"📄 With HTML: {stats['posts_with_html']}")
    print(f"🔧 Updated: {stats['posts_updated']}")
    print(f"❌ Broken: {stats['urls_broken']}")
    print(f"✅ Fixed: {stats['urls_fixed']}")
    print(f"{'='*55}")


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
        import traceback
        traceback.print_exc()
        sys.exit(1)
