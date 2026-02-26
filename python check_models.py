import os
import requests

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

print("🔍 Tikriname galimus Gemini modelius...\n")

# Gauti visų modelių sąrašą
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
res = requests.get(url, timeout=15)

if res.status_code != 200:
    print(f"❌ Klaida: {res.status_code} – {res.text}")
else:
    models = res.json().get("models", [])
    flash_models = [m for m in models if "flash" in m["name"].lower() and "generateContent" in m.get("supportedGenerationMethods", [])]
    
    print(f"✅ Rasti Flash modeliai (generateContent):\n")
    for m in flash_models:
        name = m["name"].replace("models/", "")
        print(f"  → {name}")
    
    if not flash_models:
        print("⚠️ Nė vieno flash modelio nerasta. Visi modeliai:")
        for m in models:
            print(f"  {m['name']}")
