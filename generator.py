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
        if abs((t1 - t2).total_seconds()) / 60 > 60: return False
    except: return False
    
    h1, a1 = normalize_name(m1.get('homeTeam')), normalize_name(m1.get('awayTeam'))
    h2, a2 = normalize_name(m2.get('homeTeam')), normalize_name(m2.get('awayTeam'))
    
    ratio = SequenceMatcher(None, f"{h1}{a1}", f"{h2}{a2}").ratio()
    return ratio > 0.60

def fetch_cdn_live():
    print("Fetching CDN-Live...")
    matches = []
    if not API_URL_CDN: return matches
    try:
        resp = requests.get(API_URL_CDN, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json().get("cdn-live-tv", {})
        for sport, event_list in data.items():
            if isinstance(event_list, list):
                for m in event_list:
                    m['custom_sport_cat'] = sport
                    m['provider'] = 'CDN'
                    matches.append(m)
    except Exception as e:
        print(f"Error CDN: {e}")
    return matches

def fetch_ppv_to():
    print("Fetching PPV.to...")
    matches = []
    if not API_URL_PPV: 
        print("AVIS: Falta API_URL_PPV als secrets.")
        return matches
    try:
        resp = requests.get(API_URL_PPV, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        
        for cat_group in data.get('streams', []):
            cat_name = cat_group.get('category_name', 'Other')
            my_cat = CAT_MAP_PPV.get(cat_name)
            if not my_cat: continue 

            for s in cat_group.get('streams', []):
                try:
                    ts = s.get('starts_at')
                    dt = datetime.utcfromtimestamp(int(ts))
                    start_str = dt.strftime("%Y-%m-%d %H:%M")
                    time_str = dt.strftime("%H:%M")
                except: continue

                full_name = s.get('name', '')
                parts = full_name.split(' vs. ')
                if len(parts) < 2: parts = full_name.split(' v ')
                if len(parts) < 2: parts = full_name.split(' - ')
                
                h = parts[0].strip() if len(parts) > 0 else "Unknown"
                a = parts[1].strip() if len(parts) > 1 else "Unknown"

                match = {
                    "gameID": str(s.get('id')),
                    "homeTeam": h, "awayTeam": a,
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
    except Exception as e:
        print(f"Error PPV: {e}")
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
        
        merged = list_cdn
        print(f"Fusionant: {len(list_cdn)} CDN + {len(list_ppv)} PPV")

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
                slug = f"{m['custom_sport_cat']}{m['homeTeam']}{m['awayTeam']}{m['start']}"
                m['gameID'] = str(abs(hash(slug)))
            
            gid = m['gameID']
            if m.get('status', '').lower() == 'finished':
                if gid in memory: del memory[gid]
                continue
            memory[gid] = m

        final_mem = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            limit = 3.5 if m.get('custom_sport_cat') == 'NBA' else 2.5
            try:
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                if (now - s_dt).total_seconds() < limit * 3600:
                    final_mem[gid] = m
            except: pass
        
        save_memory(final_mem)

        events_by_cat = {}
        for m in final_mem.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            
            m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else (5 if 'ppv' in x.get('channel_code','') else 1), reverse=True)
            events_by_cat[cat].append(m)

        active_sports = sorted(list(events_by_cat.keys()))
        
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; margin-top:50px;'>😴 No events found</div>"
        
        for sport in active_sports:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice}</div><div class="grid">'
            
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                badges = '<span class="live-badge">LIVE</span> ' if is_live else ''
                
                content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time" data-utc="{utc}">--:--</span>
                        {badges}
                        <span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span>
                    </div>
                    <div class="channels">
                """
                
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    url = ch.get('url', '#')
                    code = ch.get('channel_code', 'xx').lower()
                    img = "https://fav.farm/📺" if code == 'ppv' else f"https://flagcdn.com/24x18/{code}.png"
                    
                    try:
                        enc_url = base64.b64encode(url.encode('utf-8')).decode('utf-8')
                    except:
                        enc_url = ""
                    
                    content += f"""
                    <div class="btn" style="cursor:pointer;" data-link="{enc_url}" onclick="openLink(this)">
                        <img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}
                    </div>
                    """
                content += "</div></div>"
            content += "</div></div>"

        # CORRECCIÓ CLAU AQUÍ BAIX:
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f: template = f.read()
            html = template.replace('', navbar) # CORREGIT
            html = html.replace('', content)   # CORREGIT
            
            with open("index.html", "w", encoding="utf-8") as f: f.write(html)
            print("Web Generated Successfully.")
        else:
            print("ERROR: template.html no trobat.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()