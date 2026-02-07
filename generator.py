import requests
import json
import os
import shutil
import base64
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")
API_URL_PPV = os.environ.get("API_URL_PPV")

MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"
TEMPLATE_FILE = "template.html"

# PLANTILLA D'EMERGÈNCIA (Per si falla el template.html)
DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Schedule</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --live: #ef4444; }
        body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; margin: 0; padding: 20px; }
        .navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; margin-bottom: 20px; }
        .nav-btn { background: var(--card); color: var(--text); padding: 8px 16px; border-radius: 20px; text-decoration: none; border: 1px solid #334155; }
        .nav-btn:hover { background: var(--accent); }
        .sport-title { font-size: 1.5rem; font-weight: bold; margin: 30px 0 15px 0; border-left: 4px solid var(--accent); padding-left: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; }
        .header { padding: 15px; background: rgba(0,0,0,0.2); display: flex; justify-content: space-between; align-items: center; }
        .live-badge { background: var(--live); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; }
        .channels { padding: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
        .btn { background: #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 6px; }
        .btn:hover { background: var(--accent); }
        .flag-img { width: 16px; height: 12px; object-fit: cover; }
    </style>
</head>
<body>
    <div class="navbar" id="navbar"></div>
    <div id="content"></div>
    <script>
        document.querySelectorAll('.time').forEach(el => {
            const utc = el.getAttribute('data-utc');
            if(utc) el.textContent = new Date(utc.replace(' ', 'T')+'Z').toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        });
        function openLink(el) {
            const raw = el.getAttribute('data-link');
            if(raw) window.open(atob(raw), '_blank');
        }
    </script>
</body>
</html>"""

# HEADERS REALS - Intentem imitar Chrome al màxim
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

CAT_MAP_PPV = {
    "Football": "Soccer", "American Football": "NFL", "Basketball": "NBA",
    "Hockey": "NHL", "Baseball": "MLB", "Motor Sports": "F1",
    "Fighting": "Boxing", "Tennis": "Tennis", "Rugby": "Rugby"
}

def get_sport_name(api_key):
    names = { "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈", "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️", "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉" }
    return names.get(api_key, api_key.upper())

def normalize_name(name):
    if not name: return ""
    garbage = ["fc", "cf", "ud", "ca", "sc", "basketball", "football"]
    clean = name.lower()
    for g in garbage: clean = clean.replace(f" {g} ", " ").replace(f"{g} ", "").replace(f" {g}", "")
    return clean.strip()

def are_same_match(m1, m2):
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'): return False
    try:
        t1 = datetime.strptime(m1['start'], "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(m2['start'], "%Y-%m-%d %H:%M")
        if abs((t1 - t2).total_seconds()) / 60 > 60: return False
    except: return False
    h1, a1 = normalize_name(m1.get('homeTeam')), normalize_name(m1.get('awayTeam'))
    h2, a2 = normalize_name(m2.get('homeTeam')), normalize_name(m2.get('awayTeam'))
    return SequenceMatcher(None, f"{h1}{a1}", f"{h2}{a2}").ratio() > 0.60

def fetch_cdn_live():
    print("Fetching CDN-Live...")
    matches = []
    if not API_URL_CDN:
        print("❌ ERROR: La variable API_URL està buida!")
        return matches
        
    try:
        resp = requests.get(API_URL_CDN, headers=HEADERS, timeout=25)
        print(f"📡 CDN Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json().get("cdn-live-tv", {})
                for sport, event_list in data.items():
                    if isinstance(event_list, list):
                        for m in event_list:
                            m['custom_sport_cat'] = sport
                            m['provider'] = 'CDN'
                            matches.append(m)
                if len(matches) == 0:
                    print(f"⚠️ CDN OK però buit. Resposta parcial: {str(resp.text)[:200]}")
            except json.JSONDecodeError:
                print(f"❌ CDN Error JSON. Resposta rebuda: {str(resp.text)[:200]}")
        else:
            print(f"❌ CDN Error HTTP {resp.status_code}. Resposta: {str(resp.text)[:200]}")
    except Exception as e: print(f"❌ Error CRÍTIC CDN: {e}")
    return matches

def fetch_ppv_to():
    print("Fetching PPV.to...")
    matches = []
    if not API_URL_PPV:
        print("❌ ERROR: La variable API_URL_PPV està buida!")
        return matches

    try:
        resp = requests.get(API_URL_PPV, headers=HEADERS, timeout=25)
        print(f"📡 PPV Status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                for cat_group in data.get('streams', []):
                    cat_name = cat_group.get('category_name', 'Other')
                    my_cat = CAT_MAP_PPV.get(cat_name)
                    if not my_cat: continue 
                    for s in cat_group.get('streams', []):
                        try:
                            dt = datetime.utcfromtimestamp(int(s.get('starts_at')))
                            start_str = dt.strftime("%Y-%m-%d %H:%M")
                            time_str = dt.strftime("%H:%M")
                        except: continue
                        
                        full_name = s.get('name', '')
                        parts = full_name.split(' vs. ') if ' vs. ' in full_name else (full_name.split(' v ') if ' v ' in full_name else full_name.split(' - '))
                        h, a = (parts[0].strip(), parts[1].strip()) if len(parts) > 1 else (full_name, "Unknown")
                        matches.append({
                            "gameID": str(s.get('id')), "homeTeam": h, "awayTeam": a, "time": time_str, "start": start_str,
                            "custom_sport_cat": my_cat, "status": "upcoming", "provider": "PPV",
                            "channels": [{"channel_name": f"{s.get('tag', 'Link')} (HD)", "channel_code": "ppv", "url": s.get('iframe', '#'), "priority": 5}]
                        })
                if len(matches) == 0:
                    print(f"⚠️ PPV OK però buit. Resposta parcial: {str(resp.text)[:200]}")
            except json.JSONDecodeError:
                 print(f"❌ PPV Error JSON. Resposta rebuda: {str(resp.text)[:200]}")
        else:
             print(f"❌ PPV Error HTTP {resp.status_code}. Resposta: {str(resp.text)[:200]}")
    except Exception as e: print(f"❌ Error CRÍTIC PPV: {e}")
    return matches

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def save_memory(data):
    if os.path.exists(MEMORY_FILE):
        try: shutil.copy(MEMORY_FILE, BACKUP_FILE)
        except: pass
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def main():
    try:
        memory = load_memory()
        list_cdn = fetch_cdn_live()
        list_ppv = fetch_ppv_to()
        
        merged = list_cdn
        print(f"🔄 Fusionant: CDN({len(list_cdn)}) + PPV({len(list_ppv)})")

        for p_match in list_ppv:
            found = False
            for existing in merged:
                if are_same_match(existing, p_match):
                    existing['channels'].extend(p_match['channels'])
                    found = True
                    break
            if not found: merged.append(p_match)

        for m in merged:
            if 'gameID' not in m or m['provider'] == 'PPV':
                m['gameID'] = str(abs(hash(f"{m['custom_sport_cat']}{m['homeTeam']}{m['awayTeam']}{m['start']}")))
            gid = m['gameID']
            if m.get('status', '').lower() == 'finished':
                if gid in memory: del memory[gid]
                continue
            memory[gid] = m

        final_mem = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            try:
                # Augmentem el temps de vida dels partits a 5 hores per seguretat
                if (now - datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")).total_seconds() < 5 * 3600:
                    final_mem[gid] = m
            except: pass
        
        save_memory(final_mem)

        events_by_cat = {}
        for m in final_mem.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        active_sports = sorted(list(events_by_cat.keys()))
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; padding:50px; color:#94a3b8;'>😴 No s'han trobat partits en viu.<br><small>Revisa els logs per veure l'error API</small></div>"
        
        for sport in active_sports:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice}</div><div class="grid">'
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                badges = '<span class="live-badge">LIVE</span> ' if is_live else ''
                content += f"""<div class="card"><div class="header"><span class="time" data-utc="{utc}">--:--</span>{badges}<span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span></div><div class="channels">"""
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    try: enc = base64.b64encode(ch.get('url', '#').encode('utf-8')).decode('utf-8')
                    except: enc = ""
                    code = ch.get('channel_code', 'xx').lower()
                    img = "https://fav.farm/📺" if code == 'ppv' else f"https://flagcdn.com/24x18/{code}.png"
                    content += f"""<div class="btn" data-link="{enc}" onclick="openLink(this)"><img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}</div>"""
                content += "</div></div>"
            content += "</div></div>"

        # --- GENERACIÓ FINAL ---
        template_content = DEFAULT_TEMPLATE
        if os.path.exists(TEMPLATE_FILE):
            try:
                with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    # CORRECCIÓ: Verifiquem si té les marques
                    if "" in file_content:
                        template_content = file_content
                        print("✅ Usant template.html extern.")
                    else:
                        print("⚠️ template.html trobat però sense marques (PLACEHOLDER). Ignorant-lo i usant plantilla per defecte.")
            except: pass
        else:
            print("⚠️ template.html NO trobat. Usant plantilla d'emergència.")

        html = template_content.replace('', navbar)
        html = html.replace('', content)
        
        with open("index.html", "w", encoding="utf-8") as f: f.write(html)
        print("✅ Web generada correctament! (Ara cal que l'Action la pugi)")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()