import os
import requests

WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

# Gauti paskutinį straipsnį ir pažiūrėti kaip ACF laukus grąžina
res = requests.get(
    f"{WP_BASE_URL}/wp/v2/posts?per_page=1&status=publish",
    auth=(WP_USER, WP_PASS)
)
posts = res.json()
if posts:
    post = posts[0]
    post_id = post["id"]
    print(f"Post: {post['title']['rendered']} (ID: {post_id})")
    print(f"ACF laukai:")
    acf = post.get("acf", {})
    for key, val in acf.items():
        print(f"  {key}: {repr(val)}")
