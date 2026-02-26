def run_wealth_bot(politician_name):
    print(f"\n💎 Ruošiamas: {politician_name}")
    
    wiki_img = get_wiki_image(politician_name)
    if not wiki_img:
        print(f"  ⏭️ PRALEIDŽIAMA: Nuotrauka nerasta.")
        return

    img_id = None
    try:
        img_res = requests.get(wiki_img, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {"Content-Disposition": f"attachment; filename={politician_name.replace(' ', '_')}.jpg", "Content-Type": "image/jpeg"}
        res = requests.post(f"{WP_BASE_URL}/wp/v2/media", data=img_res.content, headers=headers, auth=(WP_USER, WP_PASS))
        img_id = res.json()["id"] if res.status_code == 201 else None
    except: pass
    
    if not img_id:
        print(f"  ⏭️ PRALEIDŽIAMA: Nepavyko įkelti nuotraukos.")
        return

    # PATOBULINTAS PROMPTAS: Milijonai, Įdomūs faktai ir SEO
    prompt = (
        f"Write an 850-word high-authority financial profile for {politician_name} (2026 update). \n"
        f"STYLE: Conversational, expert, not boring. Use H2/H3, **bolding**, and bullet points. \n"
        f"CONTENT: Include a 'Key Financial Milestones' section with interesting facts and a detailed net worth history (2018-2026). \n"
        f"IMPORTANT: Net worth MUST be in Millions (e.g., $5.4M, $12.8M). Do not use small numbers. \n"
        f"SELECT: Choose exactly 2 items for wealth_sources from: {WEALTH_OPTIONS}. \n"
        f"SELECT: Choose max 2 major assets for the 'assets' field. \n"
        f"Return ONLY JSON: {{\"article\": \"HTML\", \"net_worth\": \"$10.5M\", \"job\": \"Senator\", "
        f"\"history\": \"2018:$4M,2021:$7M,2024:$9M,2026:$10.5M\", \"urls\": [\"URL1\"], "
        f"\"wealth_sources\": [\"Stock Market Investments\", \"Real Estate Holdings\"], "
        f"\"assets\": \"Stock Portfolio, Residential Property\", \"seo_title\": \"Title\", \"seo_desc\": \"Desc\", \"cats\": [\"United States (USA)\"]}}"
    )

    res = call_gemini_with_retry(prompt)
    if res and 'candidates' in res:
        try:
            full_text = res['candidates'][0]['content']['parts'][0]['text']
            json_str = re.search(r'\{.*\}', full_text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Šaltinių HTML
            sources_html = "<strong>Financial Data Sources:</strong><ul>"
            for u in data.get("urls", []):
                sources_html += f'<li><a href="{u}" target="_blank" rel="nofollow noopener">{u}</a></li>'
            sources_html += "</ul>"

            payload = {
                "title": f"{politician_name} Net Worth 2026: Financial Strategy & Portfolio",
                "content": data["article"],
                "status": "publish",
                "featured_media": img_id,
                "categories": [CAT_MAP[c] for c in data.get("cats", []) if c in CAT_MAP],
                "acf": {
                    "job_title": data.get("job", ""),
                    "net_worth": data.get("net_worth", ""), # Čia dabar bus $10.5M, o ne $1
                    "net_worth_history": data.get("history", ""),
                    "source_of_wealth": data.get("wealth_sources", [])[:2], # Čia užpildo checkboxus
                    "main_assets": data.get("assets", ""), # Tik 1-2 pagrindiniai
                    "sources": sources_html
                },
                "rank_math_title": data.get("seo_title", ""),
                "rank_math_description": data.get("seo_desc", ""),
                "rank_math_focus_keyword": f"{politician_name} net worth"
            }
            
            wp_res = requests.post(f"{WP_BASE_URL}/wp/v2/posts", json=payload, auth=(WP_USER, WP_PASS))
            if wp_res.status_code == 201:
                print(f"  ✅ SĖKMĖ: {politician_name} (Net Worth: {data.get('net_worth')})")
            else:
                print(f"  ❌ WP Klaida: {wp_res.text}")
        except Exception as e:
            print(f"  🚨 Klaida: {e}")
