import requests
import json
import os
import shutil
import base64  # <--- NOVA IMPORTACIÓ NECESSÀRIA
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# CONFIGURACIÓ
API_URL_CDN = os.environ.get("API_URL")
API_URL_PPV = os.environ.get("API_URL_PPV")

MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"
TEMPLATE_FILE = "template.html"

CAT_MAP_PPV = {
    "Football": "Soccer", "American Football": "NFL", "Basketball": "NBA",
    "Hockey": "NHL", "Baseball": "MLB", "Motor Sports": "F1",
    "Fighting": "Boxing", "Tennis": "Tennis", "Rugby": "Rugby"
}

def get_sport_name(api_key):
    names = {
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈",
        "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊",
        "Rugby": "RUGBI 🏉", "Darts": "DARTS 🎯", "Snooker": "SNOOKER 🎱"
    }
    return names.get(api_key, api_key.upper())

def normalize_name(name):
    if not name: return ""
    garbage = ["fc", "cf", "ud", "ca", "sc", "basketball", "football"]
    clean = name.lower()
    for g in garbage:
        clean = clean.replace(f" {g} ", " ").replace(f"{g} ", "").replace(f" {g}", "")
    return clean.strip()

def are_same_match(m1, m2):
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'): return False
    try:
        t1 = datetime.strptime(m1['start'], "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(m2['start'], "%Y-%m-%d %H:%M")
        if abs((t1 - t2).total_seconds()) / 60 > 45: return False
    except: return False
    
    h1, a1 = normalize_name(m1.get('homeTeam')), normalize_name(m1.get('awayTeam'))
    h2, a2 = normalize_name(m2.get('homeTeam')), normalize_name(m2.get('awayTeam'))
    
    # Comparem noms creuats també (Home1 vs Home2 AND Away1 vs Away2)
    ratio = SequenceMatcher(None, f"{h1}{a1}", f"{h2}{a2}").ratio()
    return ratio > 0.65 # Baixem una mica el llindar per ser més permissius

def fetch_cdn_live():
    print("Fetching CDN-Live...")
    matches = []
    if not API_URL_CDN: 
        print("⚠️ AVIS: No s'ha trobat API_URL (CDN)")
        return matches
    try:
        resp = requests.get(API_URL_CDN, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json().get("cdn-live-tv", {})
        for sport, event_list in data.items():
            if isinstance(event_list, list):
                for m in event_list:
                    m['custom_sport_cat'] = sport
                    m['provider'] = 'CDN'
                    matches.append(m)
        print(f"CDN: {len(matches)} partits trobats.")
    except Exception as e:
        print(f"❌ Error CDN-Live: {e}")
    return matches

def fetch_ppv_to():
    print("Fetching PPV.to...")
    matches = []
    if not API_URL_PPV: 
        print("⚠️ AVIS: No s'ha trobat API_URL_PPV")
        return matches
    try:
        resp = requests.get(API_URL_PPV, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        streams_found = 0
        
        for cat_group in data.get('streams', []):
            cat_name = cat_group.get('category_name', 'Other')
            my_cat = CAT_MAP_PPV.get(cat_name)
            if not my_cat: continue 

            for s in cat_group.get('streams', []):
                ts = s.get('starts_at')
                try:
                    dt = datetime.utcfromtimestamp(int(ts))
                    start_str = dt.strftime("%Y-%m-%d %H:%M")
                    time_str = dt.strftime("%H:%M")
                except: continue

                full_name = s.get('name', '')
                teams = full_name.split(' vs. ')
                if len(teams) < 2: teams = full_name.split(' v ')
                if len(teams) < 2: teams = full_name.split(' - ')
                
                home = teams[0].strip() if len(teams) > 0 else "Unknown"
                away = teams[1].strip() if len(teams) > 1 else "Unknown"

                match = {
                    "gameID": str(s.get('id')),
                    "homeTeam": home, "awayTeam": away,
                    "time": time_str, "start": start_str,
                    "custom_sport_cat": my_cat,
                    "status": "upcoming",
                    "provider": "PPV",
                    "channels": [{
                        "channel_name": f"{s.get('tag', 'Link')} (HD)",
                        "channel_code": "ppv",
                        "url": s.get('iframe', '#'),
                        "priority": 5
                    }]
                }
                matches.append(match)
                streams_found += 1
        print(f"PPV: {streams_found} partits trobats.")
    except Exception as e:
        print(f"❌ Error PPV.to: {e}")
    return matches

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f: return json.load(f)
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
        
        merged_pool = list_cdn
        print(f"Fusionant {len(list_cdn)} (CDN) amb {len(list_ppv)} (PPV)...")
        
        for ppv_match in list_ppv:
            found = False
            for existing in merged_pool:
                if are_same_match(existing, ppv_match):
                    existing['channels'].extend(ppv_match['channels'])
                    found = True
                    break
            if not found: merged_pool.append(ppv_match)

        current_ids = set()
        for m in merged_pool:
            if 'gameID' not in m or m['provider'] == 'PPV':
                slug = f"{m['custom_sport_cat']}{m['homeTeam']}{m['awayTeam']}{m['start']}"
                m['gameID'] = str(abs(hash(slug)))
            gid = m['gameID']
            if m.get('status', '').lower() == 'finished':
                if gid in memory: del memory[gid]
                continue
            memory[gid] = m
            current_ids.add(gid)

        final_memory = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            sport = m.get('custom_sport_cat', 'Other')
            limit = 3.5 if sport == 'NBA' else 2.5
            try:
                start_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                diff = (now - start_dt).total_seconds()
                if diff > limit * 3600: continue
                if diff < -24 * 3600: continue
            except: pass
            final_memory[gid] = m

        save_memory(final_memory)

        # GENERAR HTML
        events_by_cat = {}
        for m in final_memory.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            
            def channel_score(ch):
                code = ch.get('channel_code', '').lower()
                if code in ['es', 'mx', 'ar']: return 10
                if 'ppv' in code: return 5
                return 1
            
            m['channels'].sort(key=channel_score, reverse=True)
            events_by_cat[cat].append(m)

        active_sports = sorted(list(events_by_cat.keys()))
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; margin-top:50px;'>😴 No events</div>"
        
        for sport in active_sports:
            nice_name = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice_name}</div><div class="grid">'
            
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                has_hd = any('ppv' in ch['channel_code'] for ch in m['channels'])
                badges = ""
                if is_live: badges += '<span class="live-badge">LIVE</span> '
                if has_hd: badges += '<span class="live-badge" style="background:#007aff;">HD</span>'

                content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time" data-utc="{utc}">--:--</span>
                        {badges}
                        <span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span>
                    </div>
                    <div class=\"channels\">
                """
                
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    url = ch.get('url')
                    code = ch.get('channel_code', 'xx').lower()
                    
                    if code == 'ppv': img = "https://fav.farm/📺"
                    else: img = f"https://flagcdn.com/24x18/{code}.png"

                    # --- ZONA DE XIFRATGE ---
                    # Convertim la URL a Base64 perquè no es vegi a l'HTML
                    encoded_url = base64.b64encode(url.encode('utf-8')).decode('utf-8')
                    
                    # Fem servir un <span> o <button> enlloc de <a> per no tenir href
                    # I cridem la funció openLink(this)
                    content += f"""
                    <div class="btn" style="cursor:pointer;" data-link="{encoded_url}" onclick="openLink(this)">
                        <img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}
                    </div>
                    """
                
                content += "</div></div>"
            content += "</div></div>"

        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f: template = f.read()
            html = template.replace('', navbar).replace('', content)
            with open("index.html", "w", encoding="utf-8") as f: f.write(html)
            print("Web Generated (Stealth Mode)!")
        else:
            print("Template not found!")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()