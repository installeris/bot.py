import os
import requests

WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Gauname kelis future postus ir tikriname ACF
res = requests.get(
    f"{WP_BASE_URL}/wp/v2/posts",
    params={"per_page": 5, "status": "future"},
    auth=(WP_USER, WP_PASS),
    timeout=30
)

posts = res.json()
print(f"Tikrinami {len(posts)} future postai:\n")

for post in posts:
    title = post['title']['rendered']
    acf = post.get('acf', {})
    nw = acf.get('net_worth', 'TUŠČIAS')
    sources = acf.get('sources', 'TUŠČIAS')
    history = acf.get('net_worth_history', 'TUŠČIAS')
    job = acf.get('job_title', 'TUŠČIAS')

    print(f"  {title[:45]}")
    print(f"    net_worth:    {nw}")
    print(f"    job_title:    {job}")
    print(f"    history:      {history[:40] if history != 'TUŠČIAS' else 'TUŠČIAS'}")
    print(f"    sources:      {sources[:60] if sources != 'TUŠČIAS' else 'TUŠČIAS'}")
    print()
