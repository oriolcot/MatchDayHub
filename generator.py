import cloudscraper
import json
import os
import sys
import base64
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

# --- CONFIGURACIÓ GLOBAL ---
API_URL_PPV = "https://api.ppv.to/api/streams"
MEMORY_FILE = "memoria_partits.json"

# Llista de dominis de DaddyLive (l'script triarà el primer que funcioni)
DADDY_DOMAINS = ["https://daddylive.cv", "https://daddylive.top", "https://daddylives.nl"]

# --- LLISTA DE CANALS 24/7 DESITJATS ---
CANALS_DESITJATS = [
    "DAZN 1 Spain", "DAZN 2 Spain", "DAZN 3 Spain", "DAZN 4 Spain",
    "DAZN F1 ES", "DAZN LaLiga", "DAZN LaLiga 2",
    "Movistar Deportes Spain", "Movistar Deportes 2 Spain", "Movistar Deportes 3 Spain", "Movistar Deportes 4 Spain",
    "Movistar Golf Spain", "Movistar Laliga", "Movistar Liga de Campeones", "Movistar Plus+",
    "GOL PLAY Spain", "LALIGA TV Hypermotion",
    "EuroSport 1 Spain", "EuroSport 2 Spain", "Teledeporte Spain (TDP)",
    "Barca TV Spain", "Real Madrid TV Spain",
    "TVE La 1 Spain", "TVE La 2 Spain", "Antena 3 Spain", "Cuatro Spain", "Telecinco Spain", "La Sexta Spain"
]

# --- DICCIONARI DE LOGOS NBA ---
NBA_LOGOS = {
    "atlanta hawks": "atl", "boston celtics": "bos", "brooklyn nets": "bkn", "charlotte hornets": "cha",
    "chicago bulls": "chi", "cleveland cavaliers": "cle", "dallas mavericks": "dal", "denver nuggets": "den",
    "detroit pistons": "det", "golden state warriors": "gs", "houston rockets": "hou", "indiana pacers": "ind",
    "la clippers": "lac", "los angeles clippers": "lac", "los angeles lakers": "lal", "memphis grizzlies": "mem",
    "miami heat": "mia", "milwaukee bucks": "mil", "minnesota timberwolves": "min", "new orleans pelicans": "no",
    "new york knicks": "ny", "oklahoma city thunder": "okc", "orlando magic": "orl", "philadelphia 76ers": "phi",
    "phoenix suns": "phx", "portland trail blazers": "por", "sacramento kings": "sac", "san antonio spurs": "sa",
    "toronto raptors": "tor", "utah jazz": "utah", "washington wizards": "was"
}

INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MatchDay Hub ⚽</title>
<link rel="icon" href="https://fav.farm/⚽">
<style>
    :root { --bg: #111827; --card: #1f2937; --text: #f3f4f6; --accent: #3b82f6; --live: #ef4444; --border: #374151; --vod: #8b5cf6; }
    body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; padding-bottom: 60px; }
    
    .navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; margin-bottom: 30px; scrollbar-width: none; }
    .nav-btn { background: var(--card); color: #9ca3af; padding: 10px 20px; border-radius: 99px; text-decoration: none; border: 1px solid var(--border); white-space: nowrap; font-weight: 600; font-size: 0.9rem; transition: all 0.2s; }
    .nav-btn:hover, .nav-btn.active { background: var(--accent); color: white; border-color: var(--accent); transform: translateY(-2px); }
    
    .sport-section { margin-bottom: 40px; animation: fadeIn 0.5s ease-in; }
    .sport-title { font-size: 1.8rem; font-weight: 800; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; color: white; }
    .sport-icon { background: var(--accent); width: 4px; height: 24px; border-radius: 2px; display: inline-block; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
    .card { background: var(--card); border-radius: 16px; overflow: hidden; border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); transition: transform 0.2s; display: flex; flex-direction: column; }
    .card:hover { transform: translateY(-3px); border-color: #60a5fa; }
    
    .header { padding: 16px; background: rgba(0,0,0,0.2); border-bottom: 1px solid var(--border); }
    .meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .utc-time { font-family: monospace; color: #94a3b8; font-size: 0.85rem; background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 6px; }
    .live-badge { background: var(--live); color: white; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; animation: pulse 2s infinite; display: flex; align-items: center; gap: 4px; }
    .vod-badge { background: var(--vod); color: white; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; display: flex; align-items: center; gap: 4px; }
    .live-dot { width: 6px; height: 6px; background: white; border-radius: 50%; }
    
    .match-info { text-align: center; padding: 5px 0; }
    .teams { font-size: 1.1rem; font-weight: 700; line-height: 1.4; color: white; display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; }
    .versus { color: #6b7280; font-size: 0.9rem; font-weight: 400; }
    .team-logo { width: 28px; height: 28px; object-fit: contain; }

    .channels { padding: 16px; display: flex; flex-wrap: wrap; gap: 10px; background: #1a222e; flex-grow: 1; align-content: flex-start; }
    .btn { background: #374151; color: #e5e7eb; padding: 8px 14px; border-radius: 8px; font-size: 0.9rem; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; user-select: none; border: 1px solid transparent; text-decoration: none; width: 100%; justify-content: flex-start; font-weight:500;}
    .btn:hover { background: var(--accent); color: white; border-color: #93c5fd; }
    .flag-img { width: 20px; height: 15px; object-fit: cover; border-radius: 3px; box-shadow: 0 1px 2px rgba(0,0,0,0.3); }

    .footer { text-align: center; margin-top: 60px; color: #6b7280; font-size: 0.9rem; border-top: 1px solid var(--border); padding-top: 30px; }
    
    /* --- ESTILS DEL REPRODUCTOR FLOTANT --- */
    .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 9999; flex-direction: column; align-items: center; justify-content: center; backdrop-filter: blur(5px); }
    .modal-container { width: 100%; max-width: 1000px; display: flex; flex-direction: column; gap: 10px; padding: 15px; box-sizing: border-box; }
    .modal-header { display: flex; justify-content: flex-end; }
    .close-btn { background: var(--live); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 1rem; transition: transform 0.2s; }
    .close-btn:hover { transform: scale(1.05); }
    .iframe-wrapper { position: relative; width: 100%; padding-bottom: 56.25%; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
    .iframe-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
</style>
</head>
<body>
    <div class="navbar">{{NAVBAR}}</div>
    <div id="content">{{CONTENT}}</div>
    <div class="footer">Última actualització: <span style="color:var(--text); font-weight:bold;">{{DATE}}</span><br><small>Hora local detectada automàticament</small></div>
    
    <div id="playerModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <button class="close-btn" onclick="closePlayer()">TANCAR VÍDEO ✖</button>
            </div>
            <div class="iframe-wrapper">
                <iframe id="playerFrame" src="" allowfullscreen scrolling="no"></iframe>
            </div>
        </div>
    </div>

    <script>
        function openLink(el) { 
            try { 
                const url = atob(el.getAttribute('data-link')); 
                document.getElementById('playerFrame').src = url;
                document.getElementById('playerModal').style.display = 'flex';
                document.body.style.overflow = 'hidden'; 
            } catch(e){ console.error("Error link", e); } 
        }

        function closePlayer() {
            document.getElementById('playerFrame').src = ''; 
            document.getElementById('playerModal').style.display = 'none';
            document.body.style.overflow = ''; 
        }

        document.querySelectorAll('.utc-time').forEach(el => {
            const raw = el.getAttribute('data-ts');
            const txt = el.innerText;
            // Ignorem la conversió d'hora si és un Replay o un Canal 24/7
            if(raw && !txt.includes("Diferit") && !txt.includes("📼") && !txt.includes("Sempre Actiu") && !txt.includes("EN DIRECTE")) {
                try {
                    const d = new Date(raw.replace(' ', 'T')+'Z');
                    if(!isNaN(d.getTime())) el.innerText = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
                } catch(e) {}
            }
        });
    </script>
</body>
</html>"""

def log(msg): sys.stderr.write(f"[LOG] {msg}\n")

def get_working_daddy_domain(scraper):
    log("Verificant dominis mirall de DaddyLive...")
    for dom in DADDY_DOMAINS:
        try:
            resp = scraper.get(dom, timeout=5)
            if resp.status_code == 200:
                log(f"✅ Domini actiu seleccionat: {dom}")
                return dom
        except:
            pass
    log("⚠️ Cap domini principal respon. S'utilitzarà el domini per defecte.")
    return DADDY_DOMAINS[0]

def parse_date(date_str):
    if not date_str: return None
    clean_str = date_str.replace('T', ' ')[:16]
    try:
        return datetime.strptime(clean_str, "%Y-%m-%d %H:%M")
    except:
        return None

def get_nba_logo(team_name):
    low_name = team_name.lower().strip()
    if low_name in NBA_LOGOS:
        return f"https://a.espncdn.com/i/teamlogos/nba/500/{NBA_LOGOS[low_name]}.png"
    return ""

def get_sport_name(key):
    names = { 
        "Soccer": "FUTBOL ⚽", "Football": "FUTBOL ⚽", "Basketball": "BÀSQUET 🏀", "NBA": "BÀSQUET 🏀", 
        "NBA Replays 🏀": "NBA REPLAYS 🏀", "Canals 24/7 📺": "CANALS EN DIRECTE 📺"
    }
    return names.get(key, key.upper())

def clean_string(text):
    if not text: return ""
    garbage = ["fc", "cf", "sc", "ac", "cd", "ud", "ca", "club", "real", "city", "united", "sporting", "athletic", "vs", "-", "."]
    cleaned = text.lower()
    for g in garbage: cleaned = cleaned.replace(f" {g} ", " ").replace(f"{g} ", "")
    return "".join(e for e in cleaned if e.isalnum())

def are_duplicates(m1, m2):
    if m1.get('provider') in ['NBA_REPLAY', 'DADDY_TV'] or m2.get('provider') in ['NBA_REPLAY', 'DADDY_TV']:
        return m1.get('provider') == m2.get('provider') and m1.get('homeTeam') == m2.get('homeTeam')
    
    t1, t2 = parse_date(m1.get('start_raw')), parse_date(m2.get('start_raw'))
    if t1 and t2:
        if abs((t1 - t2).total_seconds()) / 3600 > 2.0: return False
    else: return False

    s1 = clean_string(m1.get('homeTeam', '') + m1.get('awayTeam', ''))
    s2 = clean_string(m2.get('homeTeam', '') + m2.get('awayTeam', ''))
    return SequenceMatcher(None, s1, s2).ratio() > 0.6

def fetch_ppv_to(scraper):
    matches = []
    log("Buscant partits a PPV.to...")
    try:
        resp = scraper.get(API_URL_PPV, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get("streams", [])
            for cat in data:
                cat_name = cat.get("category", "")
                if cat_name in ["Football", "Basketball"]:
                    sport_key = "Soccer" if cat_name == "Football" else "NBA"
                    for s in cat.get("streams", []):
                        name = s.get("name", "")
                        teams = name.split(" vs. ") if " vs. " in name else name.split(" vs ")
                        home = teams[0].split(" (")[0].strip() if len(teams) > 0 else "Event"
                        away = teams[1].split(" (")[0].strip() if len(teams) > 1 else "Unknown"
                        dt = datetime.fromtimestamp(s.get("starts_at"), tz=timezone.utc)
                        start_str = dt.strftime("%Y-%m-%d %H:%M")
                        matches.append({
                            'custom_sport_cat': sport_key, 'homeTeam': home, 'awayTeam': away,
                            'start': start_str, 'start_raw': start_str,
                            'status': 'live' if dt < datetime.now(timezone.utc) else 'upcoming',
                            'provider': 'PPV', 'channels': [{'channel_name': 'PPV Stream', 'url': s.get("iframe"), 'channel_code': 'us'}]
                        })
            log(f"✅ S'han trobat {len(matches)} partits a PPV.to.")
    except Exception as e: log(f"❌ Error PPV.to: {e}")
    return matches

def fetch_daddylive_events(scraper, base_domain):
    matches = []
    log("Buscant partits en directe a DaddyLive (tv2.json)...")
    try:
        resp = scraper.get(f"{base_domain}/cache/tv2/tv2.json", timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            avui_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            for main_category, sub_data in data.items():
                if not isinstance(sub_data, dict): continue
                for sub_category, events_list in sub_data.items():
                    if not isinstance(events_list, list): continue
                    
                    for ev in events_list:
                        event_text = ev.get('event', '')
                        if ' vs ' not in event_text.lower() and ' vs. ' not in event_text.lower(): continue
                        
                        esport = "Other"
                        if 'football' in event_text.lower() or 'soccer' in event_text.lower(): esport = "Soccer"
                        elif 'basketball' in event_text.lower() or 'nba' in event_text.lower(): esport = "NBA"
                        if esport not in ["Soccer", "NBA"]: continue
                            
                        noms_equips = event_text.split(' : ')[-1].strip() if ' : ' in event_text else event_text
                        equips = noms_equips.split(' vs ') if ' vs ' in noms_equips else noms_equips.split(' vs. ')
                        if len(equips) < 2: continue
                        
                        home, away = equips[0].strip(), equips[1].strip()
                        
                        canals_formatats = []
                        for i, ch in enumerate(ev.get('channels', [])):
                            c_name = ch.get('channel_name', f"Opció {i+1}")
                            c_id = ch.get('channel_id', '')
                            if c_id:
                                url_embed = f"{base_domain}/embed/stream.php?id={c_id}&player=1&source=tv2"
                                canals_formatats.append({
                                    'channel_name': f"DaddyLive {c_name.replace('Link -', '').strip()}",
                                    'url': url_embed, 'channel_code': 'us'
                                })
                                
                        if canals_formatats:
                            temps_raw = ev.get('time', 'Live')
                            status = 'live' if 'live' in temps_raw.lower() else 'upcoming'
                            start_real = now_str if status == 'live' else f"{avui_str} {temps_raw}"
                            start_display = "EN DIRECTE 🟢" if status == 'live' else temps_raw
                            
                            matches.append({
                                'custom_sport_cat': esport, 'homeTeam': home, 'awayTeam': away,
                                'start': start_display, 'start_raw': start_real, 'status': status,
                                'provider': 'DADDYLIVE_EVENTS',
                                'channels': canals_formatats
                            })
            log(f"✅ S'han trobat {len(matches)} partits esportius a DaddyLive.")
    except Exception as e: log(f"❌ Error a DaddyLive Events: {e}")
    return matches

def fetch_daddylive_channels(scraper, base_domain):
    matches = []
    log("Buscant canals 24/7 (via guia d'IDs)...")
    try:
        # Utilitzem l'API de lmao NOMÉS com a llibreta de contactes (perquè sabem que l'estructura no canvia)
        # Però generem l'enllaç original de DaddyLive!
        resp = scraper.get("https://lmao.love/channels/index.json", timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            canals_trobats = []
            if isinstance(data, dict):
                for cid, name in data.items():
                    if any(d.lower() in name.lower() for d in CANALS_DESITJATS):
                        nom_net = name.replace(" Spain", "").replace(" (TDP)", "").strip()
                        # Generem l'enllaç ofical de l'API de DaddyLive que obre el seu reproductor net
                        url_final = f"{base_domain}/embed/stream.php?id={cid}&player=1&source=tv"
                        canals_trobats.append({'channel_name': nom_net, 'url': url_final, 'channel_code': 'es'})
            if canals_trobats:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                matches.append({
                    'custom_sport_cat': 'Canals 24/7 📺', 'homeTeam': "Televisió en Directe", 'awayTeam': "Graella Premium", 
                    'start': "Sempre Actiu 🟢", 'start_raw': now, 'status': 'live', 
                    'provider': 'DADDY_TV', 'channels': canals_trobats
                })
                log(f"✅ S'han integrat {len(canals_trobats)} canals 24/7 a la web.")
    except Exception as e: log(f"❌ Error als Canals 24/7: {e}")
    return matches

def fetch_nba_replays(scraper, memory_matches):
    matches = []
    log("Buscant repeticions NBA...")
    partits_coneguts = [m.get('homeTeam') for m in memory_matches if m.get('provider') == 'NBA_REPLAY']
    dominis_directes = ['filemoon', 'vidmoly', 'vk.com', 'ok.ru', 'streamtape', 'voe', 'uqload', 'dood', 'dailymotion']
    try:
        resp = scraper.get("https://basketball-video.com/", timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        partits_a_visitar = []
        for a in soup.find_all('a', href=True):
            link = a['href']
            if ('replay' in link.lower() or 'full-game' in link.lower()) and '/videos/' not in link.lower():
                title = link.split('/')[-1].replace('.html', '').replace('-', ' ').title()
                
                # --- FILTRE WNBA / EXTRAR ---
                t_low = title.lower()
                if any(w in t_low for w in ['wnba', 'aces', 'mercury', 'liberty', 'sun', 'lynx', 'sky']): continue
                
                if ' vs ' in title.lower() or ' vs. ' in title.lower() or any(x in title.lower() for x in ['all star', 'rising stars']):
                    home_t = title.split(' Vs ')[0].strip() if ' Vs ' in title else title.split(' Full ')[0].strip()
                    if home_t not in partits_coneguts: partits_a_visitar.append((link, title))
        
        for link, title in partits_a_visitar[:8]:
            try:
                # Arreglem la separació del títol perquè surtin bé els logos
                home = title
                away = "VOD"
                if ' Vs ' in title or ' vs ' in title.lower():
                    sep = ' Vs ' if ' Vs ' in title else (' vs ' if ' vs ' in title else ' vs. ')
                    parts = title.split(sep, 1)
                    home = parts[0].strip()
                    away = parts[1].split(' Full ')[0].strip()
                else:
                    home = title.split(' Full ')[0].strip()

                art_resp = scraper.get(link if link.startswith('http') else "https://basketball-video.com"+link, timeout=10)
                art_soup = BeautifulSoup(art_resp.text, 'html.parser')
                channels = []
                
                for la in art_soup.find_all('a', href=True):
                    btn_text = la.text.strip()
                    # Condició: Text curt (evitem el menú lateral) i paraula clau
                    if len(btn_text) < 25 and any(x in btn_text.lower() for x in ['watch', 'full game', 'part']):
                        href = la['href']
                        if href.endswith('.html') and 'player' not in href: continue # Ignorem enllaços interns d'articles
                        
                        if not any(d in href.lower() for d in dominis_directes):
                            try:
                                f_r = scraper.get(href, timeout=5)
                                f_s = BeautifulSoup(f_r.text, 'html.parser')
                                iframe = f_s.find('iframe')
                                if iframe: href = iframe.get('src')
                            except: pass
                        
                        c_name = "Veure"
                        if 'part 1' in btn_text.lower() or '1a part' in btn_text.lower(): c_name = '1a Part 🎬'
                        elif 'part 2' in btn_text.lower() or '2a part' in btn_text.lower(): c_name = '2a Part 🎬'
                        elif 'part 3' in btn_text.lower() or '3a part' in btn_text.lower(): c_name = '3a Part 🎬'
                        elif 'full' in btn_text.lower() or 'watch' in btn_text.lower(): c_name = 'Partit Sencer 🍿'
                        
                        channels.append({'channel_name': c_name, 'url': href, 'channel_code': 'us'})
                
                if channels:
                    matches.append({
                        'custom_sport_cat': 'NBA Replays 🏀', 'homeTeam': home, 'awayTeam': away, 
                        'start': "📼 REPLAY", 'start_raw': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), 
                        'status': 'vod', 'provider': 'NBA_REPLAY', 'channels': channels
                    })
            except: pass
        log(f"✅ S'han trobat {len(matches)} repeticions NBA (Sense WNBA i ben formatades).")
    except Exception as e: log(f"❌ Error NBA: {e}")
    return matches

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        memory = load_memory()
        
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        daddy_domain = get_working_daddy_domain(scraper)
        
        daddy_events = fetch_daddylive_events(scraper, daddy_domain)
        daddy_channels = fetch_daddylive_channels(scraper, daddy_domain)
        ppv_events = fetch_ppv_to(scraper)
        nba_replays = fetch_nba_replays(scraper, list(memory.values()))
        
        all_raw = list(memory.values()) + ppv_events + daddy_events + daddy_channels + nba_replays
        unique = {}

        for match in all_raw:
            found = False
            for uid, existing in unique.items():
                if are_duplicates(existing, match):
                    found = True
                    ext_urls = {c['url'] for c in existing.get('channels', [])}
                    for ch in match.get('channels', []):
                        if ch['url'] not in ext_urls: existing['channels'].append(ch)
                    if not existing.get('homeLogo') and match.get('homeLogo'):
                        existing['homeLogo'] = match.get('homeLogo')
                        existing['awayLogo'] = match.get('awayLogo')
                    break
            if not found:
                slug = f"{match.get('homeTeam')}{match.get('start_raw')}{match.get('provider')}"
                gid = str(abs(hash(slug)))
                unique[gid] = match

        clean_mem, display = {}, []
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        for gid, m in unique.items():
            dt = parse_date(m.get('start_raw'))
            if not dt: continue
            diff = (now_utc - dt).total_seconds() / 3600
            
            limit = 96.0 if m.get('provider') == 'NBA_REPLAY' else 5.0
            if m.get('provider') == 'DADDY_TV' or diff < limit:
                clean_mem[gid] = m
                if m.get('provider') == 'DADDY_TV' or diff < 4.0 or m.get('provider') == 'NBA_REPLAY':
                    display.append(m)

        save_memory(clean_mem)
        
        cats = {}
        for m in display:
            c = m.get('custom_sport_cat', 'Other')
            if c not in cats: cats[c] = []
            cats[c].append(m)

        navbar, content = '<a href="#" class="nav-btn active">Inici</a>', ""
        order = sorted(cats.keys(), key=lambda x: (x=='Canals 24/7 📺', x=='NBA Replays 🏀', x))
        
        for sport in order:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title"><span class="sport-icon"></span>{nice}</div><div class="grid">'
            for m in cats[sport]:
                badge = '<span class="live-badge"><div class="live-dot"></div> EN VIU</span>' if m.get('status') == 'live' else ''
                btns = ""
                for ch in m.get('channels', []):
                    b64 = base64.b64encode(ch["url"].encode()).decode()
                    flag = f'<img src="https://flagcdn.com/20x15/{ch["channel_code"]}.png" class="flag-img"> ' if 'channel_code' in ch else ''
                    btns += f'<div class="btn" data-link="{b64}" onclick="openLink(this)">{flag}{ch["channel_name"]}</div>'
                
                h_logo = f'<img src="{get_nba_logo(m["homeTeam"])}" class="team-logo" onerror="this.style.display=\'none\'">' if m.get('provider')=='NBA_REPLAY' else (f'<img src="{m.get("homeLogo")}" class="team-logo">' if m.get('homeLogo') else '')
                a_logo = f'<img src="{get_nba_logo(m["awayTeam"])}" class="team-logo" onerror="this.style.display=\'none\'">' if m.get('provider')=='NBA_REPLAY' else (f'<img src="{m.get("awayLogo")}" class="team-logo">' if m.get('awayLogo') else '')
                
                content += f'<div class="card"><div class="header"><div class="meta"><span class="utc-time" data-ts="{m["start_raw"]}">{m["start"]}</span>{badge}</div><div class="match-info"><div class="teams">{h_logo} {m["homeTeam"]} <span class="versus">vs</span> {m["awayTeam"]} {a_logo}</div></div></div><div class="channels">{btns}</div></div>'
            content += "</div></div>"

        html_final = INTERNAL_TEMPLATE.replace('{{NAVBAR}}', navbar).replace('{{CONTENT}}', content).replace('{{DATE}}', datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
        print(html_final)

    except Exception as e: log(f"CRITICAL ERROR: {e}")

if __name__ == "__main__": main()