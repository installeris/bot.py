import os
import requests
import urllib.parse
import re

WP_USER     = os.getenv("WP_USERNAME")
WP_PASS     = os.getenv("WP_APP_PASS")
WP_BASE_URL = "https://politiciannetworth.com/wp-json"

BIOGUIDE_MAP = {
    "Adam Schiff": ("Adam B.", "Schiff", "S001150"),
    "Alex Padilla": ("Alex", "Padilla", "P000145"),
    "Amy Klobuchar": ("Amy", "Klobuchar", "K000367"),
    "Andy Kim": ("Andy", "Kim", "K000394"),
    "Angela Alsobrooks": ("Angela D.", "Alsobrooks", "A000382"),
    "Angus King": ("Angus S., Jr.", "King", "K000383"),
    "Ashley Moody": ("Ashley", "Moody", "M001244"),
    "Ben Lujan": ("Ben Ray", "Lujan", "L000570"),
    "Bernard Sanders": ("Bernard", "Sanders", "S000033"),
    "Bernie Moreno": ("Bernie", "Moreno", "M001242"),
    "Bill Cassidy": ("Bill", "Cassidy", "C001075"),
    "Bill Hagerty": ("Bill", "Hagerty", "H000601"),
    "Brian Schatz": ("Brian", "Schatz", "S001194"),
    "Catherine Cortez Masto": ("Catherine", "Cortez Masto", "C001113"),
    "Charles Schumer": ("Charles E.", "Schumer", "S000148"),
    "Chris Van Hollen": ("Chris", "Van Hollen", "V000128"),
    "Christopher Coons": ("Christopher A.", "Coons", "C001088"),
    "Christopher Murphy": ("Christopher", "Murphy", "M001169"),
    "Chuck Grassley": ("Chuck", "Grassley", "G000386"),
    "Cindy Hyde-Smith": ("Cindy", "Hyde-Smith", "H001079"),
    "Cory Booker": ("Cory A.", "Booker", "B001288"),
    "Cynthia Lummis": ("Cynthia M.", "Lummis", "L000571"),
    "Dan Sullivan": ("Dan", "Sullivan", "S001198"),
    "David McCormick": ("David", "McCormick", "M001243"),
    "Deb Fischer": ("Deb", "Fischer", "F000463"),
    "Edward Markey": ("Edward J.", "Markey", "M000133"),
    "Elissa Slotkin": ("Elissa", "Slotkin", "S001208"),
    "Elizabeth Warren": ("Elizabeth", "Warren", "W000817"),
    "Eric Schmitt": ("Eric", "Schmitt", "S001227"),
    "Gary Peters": ("Gary C.", "Peters", "P000595"),
    "Jack Reed": ("Jack", "Reed", "R000122"),
    "Jacky Rosen": ("Jacky", "Rosen", "R000608"),
    "James Justice": ("James C.", "Justice", "J000312"),
    "James Lankford": ("James", "Lankford", "L000575"),
    "James Risch": ("James E.", "Risch", "R000584"),
    "Jeanne Shaheen": ("Jeanne", "Shaheen", "S001181"),
    "Jeff Merkley": ("Jeff", "Merkley", "M001176"),
    "Jerry Moran": ("Jerry", "Moran", "M000934"),
    "Jim Banks": ("Jim", "Banks", "B001299"),
    "John Barrasso": ("John", "Barrasso", "B001261"),
    "John Boozman": ("John", "Boozman", "B001236"),
    "John Cornyn": ("John", "Cornyn", "C001056"),
    "John Curtis": ("John R.", "Curtis", "C001114"),
    "John Fetterman": ("John", "Fetterman", "F000479"),
    "John Hickenlooper": ("John W.", "Hickenlooper", "H000273"),
    "John Hoeven": ("John", "Hoeven", "H001061"),
    "John Kennedy": ("John", "Kennedy", "K000393"),
    "John Thune": ("John", "Thune", "T000250"),
    "Jon Husted": ("Jon", "Husted", "H001104"),
    "Jon Ossoff": ("Jon", "Ossoff", "O000174"),
    "Joni Ernst": ("Joni", "Ernst", "E000295"),
    "Josh Hawley": ("Josh", "Hawley", "H001089"),
    "Katie Britt": ("Katie Boyd", "Britt", "B001319"),
    "Kevin Cramer": ("Kevin", "Cramer", "C001096"),
    "Kirsten Gillibrand": ("Kirsten E.", "Gillibrand", "G000555"),
    "Lindsey Graham": ("Lindsey", "Graham", "G000359"),
    "Lisa Blunt Rochester": ("Lisa", "Blunt Rochester", "B001303"),
    "Lisa Murkowski": ("Lisa", "Murkowski", "M001153"),
    "Margaret Hassan": ("Margaret Wood", "Hassan", "H001076"),
    "Maria Cantwell": ("Maria", "Cantwell", "C000127"),
    "Mark Kelly": ("Mark", "Kelly", "K000377"),
    "Mark Warner": ("Mark R.", "Warner", "W000805"),
    "Markwayne Mullin": ("Markwayne", "Mullin", "M001190"),
    "Marsha Blackburn": ("Marsha", "Blackburn", "B001243"),
    "Martin Heinrich": ("Martin", "Heinrich", "H001046"),
    "Mazie Hirono": ("Mazie K.", "Hirono", "H001042"),
    "Michael Bennet": ("Michael F.", "Bennet", "B001267"),
    "Mike Crapo": ("Mike", "Crapo", "C000880"),
    "Mike Lee": ("Mike", "Lee", "L000577"),
    "Mike Rounds": ("Mike", "Rounds", "R000605"),
    "Mitch McConnell": ("Mitch", "McConnell", "M000355"),
    "Patty Murray": ("Patty", "Murray", "M001111"),
    "Pete Ricketts": ("Pete", "Ricketts", "R000618"),
    "Peter Welch": ("Peter", "Welch", "W000800"),
    "Rand Paul": ("Rand", "Paul", "P000603"),
    "Raphael Warnock": ("Raphael G.", "Warnock", "W000790"),
    "Richard Blumenthal": ("Richard", "Blumenthal", "B001277"),
    "Richard Durbin": ("Richard J.", "Durbin", "D000563"),
    "Rick Scott": ("Rick", "Scott", "S001217"),
    "Roger Marshall": ("Roger", "Marshall", "M001198"),
    "Roger Wicker": ("Roger F.", "Wicker", "W000437"),
    "Ron Johnson": ("Ron", "Johnson", "J000293"),
    "Ron Wyden": ("Ron", "Wyden", "W000779"),
    "Ruben Gallego": ("Ruben", "Gallego", "G000574"),
    "Sheldon Whitehouse": ("Sheldon", "Whitehouse", "W000802"),
    "Shelley Capito": ("Shelley Moore", "Capito", "C001047"),
    "Steve Daines": ("Steve", "Daines", "D000618"),
    "Susan Collins": ("Susan M.", "Collins", "C001035"),
    "Tammy Baldwin": ("Tammy", "Baldwin", "B001230"),
    "Tammy Duckworth": ("Tammy", "Duckworth", "D000622"),
    "Ted Budd": ("Ted", "Budd", "B001305"),
    "Ted Cruz": ("Ted", "Cruz", "C001098"),
    "Thom Tillis": ("Thom", "Tillis", "T000476"),
    "Tim Kaine": ("Tim", "Kaine", "K000384"),
    "Tim Scott": ("Tim", "Scott", "S001184"),
    "Tim Sheehy": ("Tim", "Sheehy", "S001232"),
    "Tina Smith": ("Tina", "Smith", "S001203"),
    "Todd Young": ("Todd", "Young", "Y000064"),
    "Tom Cotton": ("Tom", "Cotton", "C001095"),
    "Tommy Tuberville": ("Tommy", "Tuberville", "T000278"),
}

def make_quiver_url(name):
    if name not in BIOGUIDE_MAP:
        return None
    fn, ln, bio = BIOGUIDE_MAP[name]
    encoded = urllib.parse.quote(f"{fn} {ln}")
    return f"https://www.quiverquant.com/congresstrading/politician/{encoded}-{bio}"

stats = {"updated": 0, "skipped": 0, "no_quiver": 0, "error": 0}

# Gauname visus postus (100 per puslapį)
page = 1
all_posts = []
while True:
    res = requests.get(
        f"{WP_BASE_URL}/wp/v2/posts",
        params={"per_page": 100, "page": page, "status": "any"},
        auth=(WP_USER, WP_PASS)
    )
    if res.status_code != 200 or not res.json():
        break
    all_posts.extend(res.json())
    page += 1

print(f"Rasta {len(all_posts)} postu\n")

for post in all_posts:
    title = post['title']['rendered']
    post_id = post['id']

    # Iš titulo ištraukiame politiko vardą
    name = title.replace(' Net Worth 2026', '').replace(' Net Worth: Beyond the Speaker\'s Gavel', '').strip()

    # Gauname ACF laukus
    acf = post.get('acf', {})
    current_sources = acf.get('sources', '')

    if not current_sources:
        print(f"  [{post_id}] {name}: sources tuščias - praleidžiame")
        stats["skipped"] += 1
        continue

    # Tikriname ar yra neteisingas QuiverQuant URL
    has_bad_quiver = 'quiverquant.com' in current_sources and '/congresstrading/politician/' not in current_sources
    has_no_quiver = 'quiverquant.com' not in current_sources

    correct_url = make_quiver_url(name)

    if not correct_url:
        if has_bad_quiver:
            # Išimame blogą URL
            lines = [l for l in current_sources.split('\n') if 'quiverquant.com' not in l]
            new_sources = '\n'.join(lines)
            print(f"  [{post_id}] {name}: išimamas blogas QuiverQuant (nėra bioguide)")
        else:
            stats["no_quiver"] += 1
            continue
    elif has_bad_quiver:
        # Pakeičiame blogą teisingas
        lines = current_sources.split('\n')
        new_lines = []
        replaced = False
        for line in lines:
            if 'quiverquant.com' in line and not replaced:
                new_lines.append(correct_url)
                replaced = True
            elif 'quiverquant.com' not in line:
                new_lines.append(line)
        new_sources = '\n'.join(new_lines)
        print(f"  [{post_id}] {name}: keičiame QuiverQuant URL")
    elif has_no_quiver:
        # Pridedame teisingą
        new_sources = current_sources.rstrip('\n') + '\n' + correct_url
        print(f"  [{post_id}] {name}: pridedame QuiverQuant URL")
    else:
        stats["skipped"] += 1
        continue

    # Atnaujiname postą
    update_res = requests.post(
        f"{WP_BASE_URL}/wp/v2/posts/{post_id}",
        json={"acf": {"sources": new_sources}},
        auth=(WP_USER, WP_PASS)
    )
    if update_res.status_code == 200:
        stats["updated"] += 1
    else:
        print(f"    KLAIDA {update_res.status_code}: {update_res.text[:100]}")
        stats["error"] += 1

print(f"\n{'='*50}")
print(f"Atnaujinta: {stats['updated']}")
print(f"Praleista:  {stats['skipped']}")
print(f"Be bioguide: {stats['no_quiver']}")
print(f"Klaidos:    {stats['error']}")
