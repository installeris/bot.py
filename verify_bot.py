import os
import requests
import json
import time
import re

WP_USER      = os.getenv("WP_USERNAME")
WP_PASS      = os.getenv("WP_APP_PASS")
WP_BASE_URL  = "https://politiciannetworth.com/wp-json"
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")
GEMINI_URL   = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"

THRESHOLD    = 0.20  # 20% skirtumas = įtartina

def ask_gemini(name, current_nw):
    prompt = f"""You are a financial fact-checker. Research {name}'s net worth RIGHT NOW using Google Search.

Find their net worth from AT LEAST 2 of these sources: OpenSecrets, Forbes, Ballotpedia, financial disclosures, Reuters, AP News, QuiverQuant.

Current value in our database: ${current_nw:,}

Return ONLY valid JSON, nothing else:
{{
  "name": "{name}",
  "found_net_worth": INTEGER_OR_NULL,
  "sources_found": ["source1: $amount", "source2: $amount"],
  "confidence": "high/medium/low",
  "verdict": "ok/overestimated/underestimated/unknown",
  "note": "brief explanation if verdict is not ok"
}}

If you cannot find reliable data, set found_net_worth to null and verdict to "unknown"."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
        "tools": [{"google_search": {}}],
    }
    try:
        res = requests.post(GEMINI_URL, json=payload, timeout=60)
        if res.status_code != 200:
            return None
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # Išvalome JSON
        text = re.sub(r'```json|```', '', text).strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"    Gemini klaida: {e}")
    return None

# Gauname visus publish postus
page = 1
all_posts = []
while True:
    res = requests.get(
        f"{WP_BASE_URL}/wp/v2/posts",
        params={"per_page": 100, "page": page, "status": "publish"},
        auth=(WP_USER, WP_PASS),
        timeout=30
    )
    if res.status_code != 200 or not res.json():
        break
    all_posts.extend(res.json())
    page += 1

print(f"Rasta {len(all_posts)} publikuotu postu\n")

to_fix    = []
ok_list   = []
unknown   = []

for i, post in enumerate(all_posts, 1):
    title = post['title']['rendered']
    post_id = post['id']
    name = re.sub(r'\s*Net Worth.*$', '', title).strip()
    acf = post.get('acf', {})
    current_nw = int(acf.get('net_worth', 0) or 0)

    print(f"[{i}/{len(all_posts)}] {name} (dabartinis: ${current_nw:,})")

    if current_nw == 0:
        print(f"    ⚠️  net_worth = 0, praleidžiame")
        to_fix.append({"name": name, "post_id": post_id, "current": 0, "found": None, "reason": "net_worth tuščias"})
        continue

    result = ask_gemini(name, current_nw)

    if not result or result.get("verdict") == "unknown" or result.get("found_net_worth") is None:
        print(f"    ❓ Nepavyko patikrinti")
        unknown.append(name)
        time.sleep(3)
        continue

    found_nw = result["found_net_worth"]
    verdict  = result.get("verdict", "unknown")
    sources  = result.get("sources_found", [])
    note     = result.get("note", "")
    confidence = result.get("confidence", "low")

    # Skaičiuojame skirtumą
    diff_pct = abs(found_nw - current_nw) / max(current_nw, 1)

    if diff_pct > THRESHOLD and verdict != "ok":
        status = "⚠️  SKIRIASI"
        to_fix.append({
            "name": name,
            "post_id": post_id,
            "current": current_nw,
            "found": found_nw,
            "diff_pct": round(diff_pct * 100, 1),
            "verdict": verdict,
            "confidence": confidence,
            "sources": sources,
            "note": note
        })
    else:
        status = "✅ OK"
        ok_list.append(name)

    print(f"    {status} | Gemini: ${found_nw:,} | Skirtumas: {diff_pct*100:.1f}% | {confidence}")
    for s in sources:
        print(f"      - {s}")
    if note:
        print(f"      📝 {note}")

    time.sleep(4)  # Rate limiting

# Rezultatai
print(f"\n{'='*60}")
print(f"✅ OK:          {len(ok_list)}")
print(f"⚠️  Reikia fix: {len(to_fix)}")
print(f"❓ Nežinoma:    {len(unknown)}")

# Išsaugome to_fix.txt
if to_fix:
    with open("to_fix.txt", "w") as f:
        f.write("POSTAI KURIEMS REIKIA PERŽIŪROS\n")
        f.write("="*60 + "\n\n")
        for item in to_fix:
            f.write(f"Politikas:  {item['name']}\n")
            f.write(f"Post ID:    {item['post_id']}\n")
            f.write(f"Dabartinis: ${item.get('current', 0):,}\n")
            if item.get('found'):
                f.write(f"Gemini rado: ${item['found']:,}\n")
                f.write(f"Skirtumas:  {item.get('diff_pct', '?')}%\n")
                f.write(f"Verdiktas:  {item.get('verdict', '?')}\n")
                f.write(f"Confidence: {item.get('confidence', '?')}\n")
            if item.get('sources'):
                f.write(f"Šaltiniai:\n")
                for s in item['sources']:
                    f.write(f"  - {s}\n")
            if item.get('note'):
                f.write(f"Pastaba:    {item['note']}\n")
            f.write("-"*40 + "\n\n")
    print(f"\nIšsaugota: to_fix.txt")

    # names.txt perrašymui
    with open("names_to_rewrite.txt", "w") as f:
        for item in to_fix:
            f.write(item['name'] + "\n")
    print(f"Perrašymui: names_to_rewrite.txt ({len(to_fix)} vardų)")
