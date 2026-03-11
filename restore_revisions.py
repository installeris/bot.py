"""
restore_revisions.py
Grąžina WordPress postus į ankstesnę revisiją.
Randa visus postus modifikuotus po nurodyto laiko ir atstatyta ankstesnę versiją.

Naudojimas:
  python restore_revisions.py

Env kintamieji (tokie patys kaip bote):
  WP_USERNAME, WP_APP_PASS
"""

import os, requests, json, sys
from datetime import datetime, timezone

WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"
WP_TIMEOUT  = 30

# Botas sugadino postus šiandien nuo 7:36 LT laiku (UTC+3 → UTC 4:36)
# Pakeisk jei reikia:
DAMAGED_AFTER_UTC = "2026-03-11T04:36:00"

AUTH = (WP_USER, WP_PASS)


def get_all_posts_modified_after(dt_str):
    """Gauna visus postus modifikuotus po nurodytos datos."""
    posts = []
    page = 1
    print(f"\nIeškome postų modifikuotų po {dt_str} UTC...")
    while True:
        r = requests.get(
            f"{WP_BASE_URL}/wp/v2/posts",
            params={
                "per_page": 100,
                "page": page,
                "modified_after": dt_str,
                "orderby": "modified",
                "order": "desc",
            },
            auth=AUTH,
            timeout=WP_TIMEOUT,
        )
        if r.status_code == 400:
            break  # nėra daugiau puslapių
        if r.status_code != 200:
            print(f"  Klaida gaunant postus: {r.status_code} {r.text[:200]}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        print(f"  Puslapis {page}: rasta {len(batch)} postų")
        if len(batch) < 100:
            break
        page += 1
    print(f"  Iš viso rasta: {len(posts)} sugadintų postų\n")
    return posts


def get_revisions(post_id):
    """Gauna visas revisijas postui."""
    r = requests.get(
        f"{WP_BASE_URL}/wp/v2/posts/{post_id}/revisions",
        params={"per_page": 10, "orderby": "date", "order": "desc"},
        auth=AUTH,
        timeout=WP_TIMEOUT,
    )
    if r.status_code != 200:
        return []
    return r.json()


def restore_to_revision(post_id, revision):
    """Atnaujina postą su revisijos turinio duomenimis."""
    # Kopijuojame svarbiausius laukus iš revisijos
    payload = {}

    if revision.get("title", {}).get("raw"):
        payload["title"] = revision["title"]["raw"]
    elif revision.get("title", {}).get("rendered"):
        payload["title"] = revision["title"]["rendered"]

    if revision.get("content", {}).get("raw"):
        payload["content"] = revision["content"]["raw"]
    elif revision.get("content", {}).get("rendered"):
        payload["content"] = revision["content"]["rendered"]

    if revision.get("excerpt", {}).get("raw"):
        payload["excerpt"] = revision["excerpt"]["raw"]

    if not payload:
        print(f"    ✗ Revisija tuščia — nieko negrąžiname")
        return False

    r = requests.post(
        f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
        json=payload,
        auth=AUTH,
        timeout=WP_TIMEOUT,
    )
    return r.status_code in (200, 201)


def restore_all():
    if not WP_USER or not WP_PASS:
        print("KLAIDA: WP_USERNAME arba WP_APP_PASS nenustatyti!")
        sys.exit(1)

    damaged_posts = get_all_posts_modified_after(DAMAGED_AFTER_UTC)

    if not damaged_posts:
        print("Nerasta sugadintų postų — viskas gerai!")
        return

    ok_count = 0
    fail_count = 0
    skip_count = 0
    failed_log = []

    for i, post in enumerate(damaged_posts):
        post_id   = post["id"]
        title     = post.get("title", {}).get("rendered", f"ID:{post_id}")
        modified  = post.get("modified", "?")
        print(f"[{i+1}/{len(damaged_posts)}] {title[:55]} (ID:{post_id}, mod:{modified[:16]})")

        revisions = get_revisions(post_id)

        if good_rev is None:
            print(f"    ✗ Nerasta revisija prieš {DAMAGED_AFTER_UTC} — nėra ko grąžinti")
            skip_count += 1
            continue

        # Revisijos surūšiuotos desc — ieškome pirmos PRIEŠ sugadinimo laiką
        damage_dt = datetime.fromisoformat(DAMAGED_AFTER_UTC).replace(tzinfo=timezone.utc)
        good_rev = None
        for rev in revisions:
            rev_date_str = rev.get("date_gmt") or rev.get("date", "")
            try:
                rev_dt = datetime.fromisoformat(rev_date_str.replace("Z", "+00:00"))
                if rev_dt.tzinfo is None:
                    rev_dt = rev_dt.replace(tzinfo=timezone.utc)
                if rev_dt < damage_dt:
                    good_rev = rev
                    break  # pirmoji (naujausia) revisija prieš sugadinimą
            except Exception:
                continue
        rev_id     = good_rev.get("id")
        rev_date   = good_rev.get("date", "?")[:16]
        rev_author = good_rev.get("author", "?")

        print(f"    Grąžiname į revisiją ID:{rev_id} ({rev_date})")

        success = restore_to_revision(post_id, good_rev)
        if success:
            print(f"    ✓ Atstatyta!")
            ok_count += 1
        else:
            print(f"    ✗ Nepavyko atstatyti")
            fail_count += 1
            failed_log.append(f"ID:{post_id} | {title[:60]} | https://politiciannetworth.com/wp-admin/post.php?post={post_id}&action=edit")

    print(f"\n{'='*50}")
    print(f"REZULTATAI:")
    print(f"  ✓ Atstatyta:     {ok_count}")
    print(f"  ✗ Nepavyko:      {fail_count}")
    print(f"  ⚠ Praleista:     {skip_count}")
    print(f"  Iš viso:         {len(damaged_posts)}")
    print(f"{'='*50}\n")

    if failed_log:
        with open("failed_restore.txt", "w") as f:
            f.write(f"Nepavyko atstatyti {len(failed_log)} postų:\n\n")
            for line in failed_log:
                f.write(line + "\n")
        print(f"⚠ Nepavykę postai išsaugoti: failed_restore.txt")
    else:
        print("✓ Visi postai atstatyti sėkmingai!")


if __name__ == "__main__":
    restore_all()
