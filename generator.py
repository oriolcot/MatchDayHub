import requests
import cloudscraper
import json
import os
import sys
import base64
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

# --- CONFIGURACIÓ PER A GITHUB ACTIONS ---
API_URL_CDN = os.environ.get("API_URL")
MEMORY_FILE = "memoria_partits.json"

# --- DICCIONARI DE LOGOS NBA (ESPN CDN) ---
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
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
</style>
</head>
<body>
    <div class="navbar">{{NAVBAR}}</div>
    <div id="content">{{CONTENT}}</div>
    <div class="footer">Última actualització: <span style="color:var(--text); font-weight:bold;">{{DATE}}</span><br><small>Hora local detectada automàticament</small></div>
    <script>
        function openLink(el) { try { window.open(atob(el.getAttribute('data-link')), '_blank'); } catch(e){ console.error("Error link", e); } }
        document.querySelectorAll('.utc-time').forEach(el => {
            const raw = el.getAttribute('data-ts');
            if(raw && !raw.includes("Diferit") && !raw.includes("📼")) {
                const d = new Date(raw.replace(' ', 'T')+'Z');
                el.innerText = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
            }
        });
    </script>
</body>
</html>"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def log(msg): sys.stderr.write(f"[LOG] {msg}\n")

# --- FUNCIÓ ANTIBALES PER LA DATA ---
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
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET 🏀", "NFL": "NFL 🏈", "F1": "FÓRMULA 1 🏎️", 
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉",
        "Hockey": "HOQUEI 🏒", "Baseball": "BEISBOL ⚾", "Darts": "DARTS 🎯"
    }
    return names.get(key, key.upper())

def clean_string(text):
    if not text: return ""
    garbage = ["fc", "cf", "sc", "ac", "cd", "ud", "ca", "club", "real", "city", "united", "sporting", "athletic", "vs", "-", "."]
    cleaned = text.lower()
    for g in garbage: cleaned = cleaned.replace(f" {g} ", " ").replace(f"{g} ", "")
    return "".join(e for e in cleaned if e.isalnum())

def are_duplicates(m1, m2):
    if m1.get('provider') != m2.get('provider'): return False
    if m1.get('provider') == 'NBA_REPLAY':
        return m1.get('homeTeam') == m2.get('homeTeam') and m1.get('awayTeam') == m2.get('awayTeam')
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'): return False
    
    t1 = parse_date(m1.get('start_raw'))
    t2 = parse_date(m2.get('start_raw'))
    if t1 and t2:
        if abs((t1 - t2).total_seconds()) / 3600 > 1.0: return False
    else:
        return False
    
    s1, s2 = clean_string(m1.get('homeTeam', '') + m1.get('awayTeam', '')), clean_string(m2.get('homeTeam', '') + m2.get('awayTeam', ''))
    return SequenceMatcher(None, s1, s2).ratio() > 0.55

def fetch_cdn_live():
    matches = []
    log("Buscant partits en directe a la CDN...")
    if not API_URL_CDN: 
        log("❌ ERROR: La URL de la CDN està buida a les variables d'entorn!")
        return matches
        
    try:
        # CANVI: Utilitzem cloudscraper en lloc de requests normal per saltar bloquejos antibot
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        resp = scraper.get(API_URL_CDN, headers={"Referer": "https://cdn-live.tv/"}, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            events_dict = data.get("cdn-live-tv") or data
            
            for sport, event_list in events_dict.items():
                if isinstance(event_list, list):
                    for m in event_list:
                        m['start_raw'] = m.get('start', '')
                        m.update({'custom_sport_cat': sport, 'provider': 'CDN'})
                        matches.append(m)
            
            log(f"✅ S'han trobat {len(matches)} partits a la CDN de diferents esports.")
        else:
            log(f"❌ ERROR: La CDN ha rebutjat la connexió. Codi HTTP: {resp.status_code}")
    except Exception as e:
        log(f"❌ Error greu llegint la API de CDN: {e}")
        
    return matches

def fetch_nba_replays(memory_matches):
    matches = []
    log("Buscant repeticions NBA (PRO: Llista VIP All-Star inclosa)...")
    
    partits_coneguts = [m.get('homeTeam') for m in memory_matches if m.get('provider') == 'NBA_REPLAY']
    dominis_directes = ['filemoon', 'vidmoly', 'vk.com', 'ok.ru', 'streamtape', 'voe', 'uqload', 'dood', 'dailymotion']
    
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        resp = scraper.get("https://basketball-video.com/", timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        partits_a_visitar = []
        now_utc = datetime.now(timezone.utc)
        any_passat = str(now_utc.year - 1)
        mes_actual = now_utc.month
        
        for a in soup.find_all('a', href=True):
            link = a['href']
            
            if ('replay' in link.lower() or 'full-game' in link.lower()) and '/videos/' not in link.lower() and 'wnba' not in link.lower():
                raw_title = link.split('/')[-1].replace('.html', '').replace('-', ' ').title()
                title_lower = raw_title.lower()
                
                is_vs = ' vs ' in title_lower or ' vs. ' in title_lower
                is_all_star = any(kw in title_lower for kw in ['all star', 'rising stars', 'celebrity game', 'hbcu'])
                
                if not is_vs and not is_all_star: continue
                if f"-{any_passat}-" in link and mes_actual > 1 and not is_all_star: continue
                if link.startswith("/"): link = "https://basketball-video.com" + link
                    
                data_bonica = "Diferit"
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s+(\d{4})', raw_title, re.IGNORECASE)
                if date_match:
                    month = date_match.group(1)[:3]
                    day = date_match.group(2)
                    year = date_match.group(3)
                    data_bonica = f"📼 {day} {month} {year}"
                
                equips_split = re.split(r'\s+Vs\.?\s+', raw_title, flags=re.IGNORECASE)
                home_t, away_t = "", ""
                
                if len(equips_split) >= 2:
                    home_t = equips_split[0].strip()
                    resta = equips_split[1]
                    tall_away = re.split(r'\s+Full\s+Game|\s+Replay|\s+January|\s+February|\s+March|\s+April|\s+May|\s+June|\s+July|\s+August|\s+September|\s+October|\s+November|\s+December', resta, flags=re.IGNORECASE)
                    away_t = tall_away[0].strip()
                else:
                    clean_title = raw_title.split(' Full Game')[0].split(' Replay')[0].strip()
                    home_t = clean_title[:40] + "..." if len(clean_title) > 40 else clean_title
                    away_t = "All-Star Event 🌟"
                
                if home_t and not any(p[1] == home_t for p in partits_a_visitar) and home_t not in partits_coneguts:
                    partits_a_visitar.append((link, home_t, away_t, data_bonica))
                    
        log(f"🔎 S'han trobat {len(partits_a_visitar)} partits NOUS per investigar a la NBA.")
        
        for link, h_team, a_team, data_partit in partits_a_visitar[:8]: 
            try:
                art_resp = scraper.get(link, timeout=10)
                art_soup = BeautifulSoup(art_resp.text, 'html.parser')
                
                channels = []
                for a in art_soup.find_all('a', href=True):
                    text_a = a.text.strip().lower()
                    href = a['href']
                    
                    if ('watch' in text_a or 'part' in text_a or 'server' in text_a) and href.startswith('http') and 'basketball-video.com' not in href:
                        nom_final = ""
                        if 'watch' in text_a or 'server 1' in text_a or 'full game' in text_a: nom_final = "Partit Sencer 🍿"
                        elif 'part 1' in text_a: nom_final = "1a Part 🎬"
                        elif 'part 2' in text_a: nom_final = "2a Part 🎬"
                        elif 'part 3' in text_a: nom_final = "3a Part 🎬"
                        elif 'part 4' in text_a: nom_final = "4a Part 🎬"
                        else: nom_final = a.text.strip() if a.text.strip() else "Veure Vídeo"

                        final_url = ""
                        if not any(d in href.lower() for d in dominis_directes):
                            try:
                                fake_resp = scraper.get(href, timeout=8)
                                fake_soup = BeautifulSoup(fake_resp.text, 'html.parser')
                                for iframe in fake_soup.find_all('iframe'):
                                    src = iframe.get('src', '')
                                    if src and 'http' in src and not any(x in src.lower() for x in ['facebook', 'twitter', 'google']):
                                        final_url = src
                                        break
                            except Exception: pass
                        else: final_url = href
                        
                        if final_url and not any(c['url'] == final_url for c in channels):
                            channels.append({'channel_name': nom_final, 'url': final_url, 'channel_code': 'us'})
                
                if channels:
                    hora_actual = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    matches.append({
                        'custom_sport_cat': 'NBA Replays 🏀', 'homeTeam': h_team, 'awayTeam': a_team,
                        'homeLogo': get_nba_logo(h_team), 'awayLogo': get_nba_logo(a_team), 'start': data_partit,
                        'start_raw': hora_actual, 'status': 'vod', 'provider': 'NBA_REPLAY', 'channels': channels
                    })
            except Exception as e:
                pass
    except Exception as e:
        pass
    return matches

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                dades = json.load(f)
                for v in dades.values():
                    if 'start_raw' not in v and 'start' in v: v['start_raw'] = v['start']
                return dades
        except: pass
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')

        memory = load_memory()
        nous_directes = fetch_cdn_live()
        nous_replays = fetch_nba_replays(list(memory.values()))
        
        all_raw_matches = list(memory.values()) + nous_directes + nous_replays
        
        unique_matches = {}
        for match in all_raw_matches:
            if match.get('provider') == 'PPV': continue
            
            is_duplicate = False
            for uid, existing_match in unique_matches.items():
                if are_duplicates(existing_match, match):
                    is_duplicate = True
                    if 'start_raw' in existing_match: match['start_raw'] = existing_match['start_raw']
                    
                    existing_urls = {c['url'] for c in existing_match.get('channels', []) if 'url' in c}
                    for ch in match.get('channels', []):
                        if ch.get('url') not in existing_urls: existing_match['channels'].append(ch)
                    if len(match.get('homeTeam', '')) > len(existing_match.get('homeTeam', '')):
                        existing_match['homeTeam'] = match['homeTeam']
                        existing_match['awayTeam'] = match['awayTeam']
                        existing_match['homeLogo'] = match.get('homeLogo', '')
                        existing_match['awayLogo'] = match.get('awayLogo', '')
                    break
            
            if not is_duplicate:
                slug = f"{match.get('custom_sport_cat')}{match.get('homeTeam')}{match.get('awayTeam')}"
                gid = str(abs(hash(slug)))
                match['gameID'] = gid
                unique_matches[gid] = match

        clean_memory = {}
        display_matches = []
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        for gid, m in unique_matches.items():
            try:
                s_dt = parse_date(m.get('start_raw'))
                if not s_dt: continue
                    
                diff_hours = (now_utc - s_dt).total_seconds() / 3600
                
                if m.get('provider') == 'NBA_REPLAY':
                    if diff_hours < 96.0:
                        clean_memory[gid] = m
                        display_matches.append(m)
                else:
                    if diff_hours < 5.0:
                        clean_memory[gid] = m
                    
                    if diff_hours < 4.0:
                        display_matches.append(m)

            except Exception as e:
                pass
        
        save_memory(clean_memory)

        events_by_cat = {}
        for m in display_matches:
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            if 'channels' in m: m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        navbar_html = '<a href="#" class="nav-btn active">Inici</a>'
        content_html = ""
        
        if not events_by_cat:
            content_html = "<div style='text-align:center; padding:80px; color:#6b7280;'><h2>😴 No hi ha partits disponibles.</h2></div>"
        else:
            sorted_cats = sorted(events_by_cat.keys(), key=lambda x: (x == 'NBA Replays 🏀', x))
            
            for sport in sorted_cats:
                nice_name = sport if '🏀' in sport else get_sport_name(sport)
                navbar_html += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'
                sport_matches = sorted(events_by_cat[sport], key=lambda x: x.get('start_raw', ''))
                
                content_html += f'<div id="{sport}" class="sport-section"><div class="sport-title"><span class="sport-icon"></span>{nice_name}</div><div class="grid">'
                
                for m in sport_matches:
                    utc = m.get('start')
                    
                    if m.get('status') == 'vod': badge_html = '' 
                    elif m.get('status') == 'live': badge_html = '<span class="live-badge"><div class="live-dot"></div> EN VIU</span>'
                    else: badge_html = ''
                        
                    home_logo_html = f"<img src='{m.get('homeLogo')}' class='team-logo' onerror=\"this.style.display='none'\">" if m.get('homeLogo') else ""
                    away_logo_html = f"<img src='{m.get('awayLogo')}' class='team-logo' onerror=\"this.style.display='none'\">" if m.get('awayLogo') else ""
                    
                    if home_logo_html or away_logo_html:
                        teams_display = f"{home_logo_html} {m['homeTeam']} <span class='versus'>vs</span> {m['awayTeam']} {away_logo_html}"
                    else:
                        teams_display = f"{m['homeTeam']} <span class='versus'>vs</span> {m['awayTeam']}"
                    
                    btns_html = ""
                    if not m.get('channels', []):
                        btns_html = """<div class="btn" style="opacity:0.6; cursor:default; justify-content:center;">Sense enllaços encara ⏳</div>"""
                    else:
                        for ch in m.get('channels', []):
                            try: link_b64 = base64.b64encode(ch.get('url', '#').encode()).decode()
                            except: link_b64 = ""
                            code = ch.get('channel_code', 'xx').lower()
                            flag = f"https://flagcdn.com/20x15/{code}.png"
                            name = ch.get('channel_name', 'Link')
                            
                            if m.get('provider') == 'NBA_REPLAY': btns_html += f"""<div class="btn" data-link="{link_b64}" onclick="openLink(this)">{name}</div>"""
                            else: btns_html += f"""<div class="btn" data-link="{link_b64}" onclick="openLink(this)"><img src="{flag}" class="flag-img" onerror="this.style.display='none'"> {name}</div>"""

                    content_html += f"""
                    <div class="card">
                        <div class="header">
                            <div class="meta"><span class="utc-time" data-ts="{utc}">{utc}</span>{badge_html}</div>
                            <div class="match-info"><div class="teams">{teams_display}</div></div>
                        </div>
                        <div class="channels">{btns_html}</div>
                    </div>"""
                content_html += "</div></div>"

        final = INTERNAL_TEMPLATE.replace('{{NAVBAR}}', navbar_html).replace('{{CONTENT}}', content_html).replace('{{DATE}}', datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
        print(final)

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()