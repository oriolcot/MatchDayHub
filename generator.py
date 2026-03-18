import cloudscraper
import json
import os
import sys
import base64
import re
import time
import concurrent.futures
from datetime import datetime, timezone
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import xml.etree.ElementTree as ET

# Evitem que peti a GitHub Actions si no existeix la llibreria dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURACIÓ GLOBAL ---
API_URL_PPV = "https://api.ppv.to/api/streams"
API_URL_CDN = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"
MEMORY_FILE = "memoria_partits.json"

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

    /* ESTILS DEL REPRODUCTOR OPTIMITZAT PER A TV */
    .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000000; z-index: 9999; flex-direction: column; align-items: center; justify-content: center; }
    .modal-container { width: 100%; max-width: 1000px; display: flex; flex-direction: column; gap: 10px; padding: 10px; box-sizing: border-box; position: relative; }
    
    /* El botó de tancar flota per sobre i s'amaga sol */
    .modal-header { position: absolute; top: -50px; right: 10px; z-index: 10000; transition: opacity 0.5s ease; opacity: 1; }
    .modal-header.hidden { opacity: 0; pointer-events: none; }
    .close-btn { background: var(--live); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }
    
    .iframe-wrapper { position: relative; width: 100%; padding-bottom: 56.25%; background: #000; overflow: hidden; transform: translateZ(0); }
    .iframe-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
</style>
</head>
<body>
    <div id="main-ui">
        <div class="navbar">{{NAVBAR}}</div>
        <div id="content">{{CONTENT}}</div>
        <div class="footer">Última actualització: <span style="color:var(--text); font-weight:bold;">{{DATE}}</span><br><small>Hora local detectada automàticament</small></div>
    </div>
    
    <div id="playerModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header" id="playerHeader">
                <button class="close-btn" onclick="closePlayer()">TORNAR A LA LLISTA ✖</button>
            </div>
            <div class="iframe-wrapper" id="videoContainer"></div>
        </div>
    </div>

    <script>
        let hideTimeout;
        
        function resetHideTimeout() {
            const header = document.getElementById('playerHeader');
            if(!header) return;
            header.classList.remove('hidden');
            clearTimeout(hideTimeout);
            
            if(document.getElementById('playerModal').style.display === 'flex') {
                hideTimeout = setTimeout(() => {
                    header.classList.add('hidden');
                }, 3000);
            }
        }

        document.addEventListener('mousemove', resetHideTimeout);
        document.addEventListener('keydown', resetHideTimeout);
        document.addEventListener('touchstart', resetHideTimeout);

        function openLink(el) { 
            try { 
                const url = atob(el.getAttribute('data-link')); 
                const container = document.getElementById('videoContainer');
                
                document.getElementById('main-ui').style.display = 'none';
                container.innerHTML = ''; 
                
                const iframe = document.createElement('iframe');
                iframe.src = url;
                iframe.setAttribute('allowfullscreen', 'true');
                iframe.setAttribute('scrolling', 'no');
                iframe.setAttribute('frameborder', '0');
                iframe.setAttribute('allow', 'autoplay; fullscreen');
                iframe.removeAttribute('sandbox'); 
                
                container.appendChild(iframe);
                
                document.getElementById('playerModal').style.display = 'flex';
                document.body.style.overflow = 'hidden'; 
                window.scrollTo(0,0);
                
                resetHideTimeout();
            } catch(e){ console.error("Error link", e); } 
        }

        function closePlayer() {
            clearTimeout(hideTimeout);
            document.getElementById('videoContainer').innerHTML = ''; 
            document.getElementById('playerModal').style.display = 'none';
            document.getElementById('main-ui').style.display = 'block';
            document.body.style.overflow = ''; 
        }

        document.querySelectorAll('.utc-time').forEach(el => {
            const raw = el.getAttribute('data-ts');
            const txt = el.innerText;
            if(raw && !txt.includes("Diferit") && !txt.includes("📼") && !txt.includes("Sempre Actiu")) {
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
        "NBA Replays 🏀": "NBA REPLAYS 🏀", "NFL": "NFL 🏈", "Tennis": "TENNIS 🎾", "Motorsport": "MOTOR 🏎️"
    }
    return names.get(key, key.upper())

def clean_string(text):
    if not text: return ""
    garbage = ["fc", "cf", "sc", "ac", "cd", "ud", "ca", "club", "real", "city", "united", "sporting", "athletic", "vs", "-", "."]
    cleaned = text.lower()
    for g in garbage: cleaned = cleaned.replace(f" {g} ", " ").replace(f"{g} ", "")
    return "".join(e for e in cleaned if e.isalnum())

def are_duplicates(m1, m2):
    if m1.get('provider') in ['NBA_REPLAY'] or m2.get('provider') in ['NBA_REPLAY']:
        return m1.get('provider') == m2.get('provider') and m1.get('homeTeam') == m2.get('homeTeam')
    
    t1, t2 = parse_date(m1.get('start_raw')), parse_date(m2.get('start_raw'))
    if t1 and t2:
        if abs((t1 - t2).total_seconds()) / 3600 > 4.0: return False
    else: return False

    t1_m1 = clean_string(m1.get('homeTeam', ''))
    t2_m1 = clean_string(m1.get('awayTeam', ''))
    
    t1_m2 = clean_string(m2.get('homeTeam', ''))
    t2_m2 = clean_string(m2.get('awayTeam', ''))
    
    score_direct = SequenceMatcher(None, t1_m1+t2_m1, t1_m2+t2_m2).ratio()
    score_crossed = SequenceMatcher(None, t1_m1+t2_m1, t2_m2+t1_m2).ratio()
    
    return max(score_direct, score_crossed) > 0.65

# =====================================================================
# AUTO-HEAL DE MEMÒRIA (Purgador d'errors vells catxetjats)
# =====================================================================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                clean_data = {}
                for gid, m in data.items():
                    # 1. Purgar el text vell i redundant d'"EN DIRECTE"
                    if m.get('start') == 'EN DIRECTE 🟢':
                        m['start'] = m.get('start_raw')
                    
                    valid_channels = []
                    for ch in m.get('channels', []):
                        url = ch.get('url', '')
                        # 2. Curar l'Error 404: Reescriure els dominis cdn.livetv trencats cap al principal
                        url = re.sub(r'https?://(?:cdn\.)?livetv[0-9]*\.[a-z]+', 'https://livetv.sx', url)
                        ch['url'] = url
                        
                        # 3. Purgar els enllaços brossa de bàsquet vells 
                        if 'basketball-video.com' in url and not url.endswith('.html'):
                            continue
                            
                        valid_channels.append(ch)
                    m['channels'] = valid_channels
                    
                    # 4. Purgar Motor/Tennis trencats perquè es tornin a raspar de zero amb el nom arreglat
                    nom = m.get('homeTeam') or m.get('name') or m.get('title') or m.get('event') or ""
                    if (nom == "Esdeveniment" or nom == "") and not m.get('awayTeam'):
                        continue
                    
                    clean_data[gid] = m
                return clean_data
        except Exception as e: 
            log(f"⚠ No s'ha pogut carregar la memòria correctament: {e}")
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def obtenir_partits_livetv_rss():
    url_rss = "https://cdn.livetv873.me/rss/upcoming_en.xml"
    
    # La teva llista blanca de competicions (en minúscules per evitar errors)
    LLISTA_BLANCA = [
        # Futbol
        "spanish primera division", "english premier league", 
        "german bundesliga", "italian serie a", 
        "uefa champions league", "uefa europa league", 
        "copa del rey", "supercopa", "fa cup", "dfb pokal", "coppa italia",
        # Bàsquet
        "nba", "euroleague", "spain. liga acb",
        # Motor
        "motogp", "moto gp", "formula 1"
    ]
    
    partits_filtrats = []
    
    try:
        # Baixem l'XML com si fóssim un navegador normal
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url_rss, headers=headers, timeout=15)
        response.raise_for_status() # Comprova que no hi hagi errors 404/500
        
        # Llegim l'XML
        root = ET.fromstring(response.content)
        
        # Busquem tots els <item> dins del <channel>
        for item in root.findall('./channel/item'):
            # Extraiem les dades, posant un text buit si per casualitat falta alguna etiqueta
            titol = item.find('title').text if item.find('title') is not None else ""
            enllac = item.find('link').text if item.find('link') is not None else ""
            descripcio = item.find('description').text if item.find('description') is not None else ""
            hora = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            desc_minusc = descripcio.lower()
            
            # FILTRE MÀGIC: Comprovem si alguna paraula de la llista blanca està a la descripció
            if any(lliga in desc_minusc for lliga in LLISTA_BLANCA):
                partit = {
                    "titol": titol,
                    "enllac": enllac,
                    "competicio": descripcio,
                    "hora": hora
                }
                partits_filtrats.append(partit)
                
        print(f"[LOG] ✅ S'han filtrat {len(partits_filtrats)} partits prèmium de l'RSS de LiveTV.")
        return partits_filtrats

    except Exception as e:
        print(f"[LOG] ❌ Error llegint l'RSS de LiveTV: {e}")
        return []

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
                        
                        nl = name.lower()
                        if "unknown" in nl or "tbd" in nl or "simulcast" in nl or "golazo" in nl:
                            continue
                            
                        teams = name.split(" vs. ") if " vs. " in name else name.split(" vs ")
                        home = teams[0].split(" (")[0].strip() if len(teams) > 0 else name
                        away = teams[1].split(" (")[0].strip() if len(teams) > 1 else ""
                        dt = datetime.fromtimestamp(s.get("starts_at"), tz=timezone.utc)
                        start_str = dt.strftime("%Y-%m-%d %H:%M")
                        matches.append({
                            'custom_sport_cat': sport_key, 'homeTeam': home, 'awayTeam': away,
                            'start': start_str, 'start_raw': start_str, 'name': name,
                            'status': 'live' if dt < datetime.now(timezone.utc) else 'upcoming',
                            'provider': 'PPV', 'channels': [{'channel_name': 'PPV Stream', 'url': s.get("iframe"), 'channel_code': 'us'}]
                        })
            log(f"✅ S'han trobat {len(matches)} partits a PPV.to.")
    except Exception as e: log(f"❌ Error PPV.to: {e}")
    return matches

def processar_partit_livetv(item, scraper):
    url_partit, text, esport = item
    try:
        r_ev = scraper.get(url_partit, timeout=8)
        art_soup = BeautifulSoup(r_ev.text, 'html.parser')
        
        canals_formatats = []
        c = 1
        urls_processades = set()
        
        mapa_banderes_linkflag = {
            "1": "ru", "2": "gb", "3": "ua", "4": "nl", "5": "sa", 
            "7": "es", "8": "pl", "9": "pt", "10": "tr", "11": "fr", 
            "12": "it", "13": "de", "16": "bg", "17": "rs", "21": "fi", 
            "22": "se", "23": "az", "28": "gr", "29": "hr"
        }
        
        for a in art_soup.find_all('a', href=True):
            href = a['href']
            
            if any(x in href for x in ['webplayer', 'embed', 'alieztv', 'bintvs']):
                if 'acestream' in href.lower(): continue
                
                clean_link = urljoin(url_partit, href)
                if clean_link.startswith('http:'):
                    clean_link = clean_link.replace('http:', 'https:')
                
                # REPARACIÓ ERROR 404: Reescrivim dominis fraudulents a l'oficial
                clean_link = re.sub(r'https?://(?:cdn\.)?livetv[0-9]*\.[a-z]+', 'https://livetv.sx', clean_link)
                
                if clean_link in urls_processades: continue
                urls_processades.add(clean_link)
                
                lang_code = 'un' 
                
                parent_row = a.find_parent('tr')
                img_tag = None
                
                if parent_row:
                    img_tag = parent_row.find('img', src=re.compile(r'/img/linkflag/|/fl/'))
                
                if not img_tag:
                    img_tag = a.find_previous('img')
                    
                if img_tag and img_tag.get('src'):
                    src_img = img_tag['src']
                    
                    if '/linkflag/' in src_img:
                        match_linkflag = re.search(r'/img/linkflag/(\d+)\.png', src_img)
                        if match_linkflag:
                            id_bandera = match_linkflag.group(1)
                            lang_code = mapa_banderes_linkflag.get(id_bandera, "un")
                            
                    elif '/fl/' in src_img:
                        match_fl = re.search(r'/fl/([a-z]{2,3})\.gif', src_img)
                        if match_fl:
                            l = match_fl.group(1)
                            map_flags_antic = {
                                'en': 'gb', 'sp': 'es', 'ru': 'ru', 'rs': 'rs', 
                                'bg': 'bg', 'fr': 'fr', 'de': 'de', 'it': 'it', 
                                'pt': 'pt', 'nl': 'nl', 'pl': 'pl', 'ro': 'ro', 
                                'tr': 'tr', 'gr': 'gr', 'cz': 'cz', 'hr': 'hr', 
                                'ar': 'ar', 'ua': 'ua'
                            }
                            lang_code = map_flags_antic.get(l, l)
                
                nom_canal = "Opció"
                if 'alieztv' in clean_link: nom_canal = "AliezTV"
                elif 'ifr' in clean_link: nom_canal = "Live Stream"
                elif 'bintvs' in clean_link: nom_canal = "BinTVs"
                
                canals_formatats.append({
                    'channel_name': f"LiveTV ({nom_canal} {c})", 
                    'url': clean_link, 
                    'channel_code': lang_code
                })
                c += 1
                
        if canals_formatats:
            return (text, esport, canals_formatats)
    except Exception as e: 
        log(f"⚠ Ignorant error al processar partit a LiveTV: {e}")
    return None

def fetch_livetv(scraper):
    matches = []
    log("Buscant partits en paral·lel a LiveTV.sx (Filtre Futbol/Bàsquet)...")
    LIVETV_DOMAINS = ["https://livetv.sx/enx", "https://livetv873.me/enx", "https://livetv740.me/enx"]
    
    domini = None
    html = ""
    for dom in LIVETV_DOMAINS:
        try:
            r = scraper.get(dom, timeout=10)
            if r.status_code == 200:
                domini = dom
                html = r.text
                break
        except Exception as e: 
            log(f"⚠ Fallada intentant domini {dom}: {e}")
        
    if not domini:
        log("❌ No s'ha pogut connectar a LiveTV.")
        return matches

    soup = BeautifulSoup(html, 'html.parser')
    partits_links = soup.find_all('a', href=re.compile(r'/eventinfo/'))
    
    links_a_processar = []
    urls_vistes = set()
    bad_words = ['hockey', 'tennis', 'volleyball', 'handball', 'table tennis', 'snooker', 'darts', 'rugby', 'cricket', 'futsal', 'badminton', 'ahl', 'atp', 'wta', 'nfl', 'mlb']
    
    for a in partits_links:
        text = a.text.strip()
        if text and (' - ' in text or ' – ' in text):
            url_partit = urljoin(domini, a['href'])
            
            if url_partit in urls_vistes: continue
            
            esport = None
            img = a.find_previous('img')
            if img and img.get('src'):
                if '1.gif' in img['src'] or 'soccer' in img.get('title', '').lower(): esport = 'Soccer'
                elif '3.gif' in img['src'] or 'basket' in img.get('title', '').lower(): esport = 'NBA'
            
            if not esport:
                text_lower = text.lower()
                parent_text = a.parent.text.lower() if a.parent else ""
                if any(bw in text_lower or bw in parent_text for bw in bad_words):
                    continue
                is_nba = any(nba_t in text_lower for nba_t in NBA_LOGOS.keys())
                esport = 'NBA' if is_nba else 'Soccer' 

            links_a_processar.append((url_partit, text, esport))
            urls_vistes.add(url_partit)

    links_a_processar = links_a_processar[:35]
    log(f"🔎 Processant {len(links_a_processar)} partits amb exploració de banderes...")
    
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(processar_partit_livetv, item, scraper) for item in links_a_processar]
        resultats = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    for res in resultats:
        if res:
            text, esport, channels = res
            sep = ' – ' if ' – ' in text else ' - '
            parts = text.split(sep, 1)
            home = parts[0].strip()
            away = parts[1].strip() if len(parts) > 1 else ""
            
            matches.append({
                'custom_sport_cat': esport, 'homeTeam': home, 'awayTeam': away,
                'start': now_str, 'start_raw': now_str, 'status': 'live',
                'provider': 'LIVETV', 'channels': channels
            })
            
    log(f"✅ S'han extret amb èxit {len(matches)} partits de LiveTV.")
    return matches

def fetch_nba_replays(scraper, memory_matches):
    matches = []
    log("Buscant repeticions NBA...")
    partits_coneguts = [m.get('homeTeam') for m in memory_matches if m.get('provider') == 'NBA_REPLAY']
    dominis_directes = ['filemoon', 'vidmoly', 'vk.com', 'ok.ru', 'streamtape', 'voe', 'uqload', 'dood', 'dailymotion']
    try:
        base_domain = "https://basketball-video.com/"
        resp = scraper.get(base_domain, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        partits_a_visitar = []
        for a in soup.find_all('a', href=True):
            link = a['href']
            if 'replay' in link.lower() or 'full-game' in link.lower():
                title = link.split('/')[-1].replace('.html', '').replace('-', ' ').title()
                
                t_low = title.lower()
                if any(w in t_low for w in ['wnba', 'aces', 'mercury', 'liberty', 'sun', 'lynx', 'sky']): continue
                
                if ' vs ' in title.lower() or ' vs. ' in title.lower() or any(x in title.lower() for x in ['all star', 'rising stars']):
                    home_t = title.split(' Vs ')[0].strip() if ' Vs ' in title else title.split(' Full ')[0].strip()
                    if home_t not in partits_coneguts: partits_a_visitar.append((link, title))
        
        for link, title in partits_a_visitar[:8]:
            try:
                home = title
                away = ""
                if ' Vs ' in title or ' vs ' in title.lower():
                    sep = ' Vs ' if ' Vs ' in title else (' vs ' if ' vs ' in title else ' vs. ')
                    parts = title.split(sep, 1)
                    home = parts[0].strip()
                    away = parts[1].split(' Full ')[0].strip()
                else:
                    home = title.split(' Full ')[0].strip()

                url_visita = urljoin(base_domain, link)
                art_resp = scraper.get(url_visita, timeout=10)
                art_soup = BeautifulSoup(art_resp.text, 'html.parser')
                channels = []
                
                for la in art_soup.find_all('a', href=True):
                    btn_text = la.text.strip().lower()
                    
                    # PROHIBIM caçar enllaços al menú de navegació ("NBA Archives")
                    if 'archive' in btn_text or 'classic' in btn_text:
                        continue
                        
                    if len(btn_text) < 25 and any(x in btn_text for x in ['watch', 'full game', 'part']):
                        raw_href = la['href']
                        if raw_href.endswith('.html') and 'player' not in raw_href: continue 
                        
                        href = urljoin(base_domain, raw_href)
                        
                        if not any(d in href.lower() for d in dominis_directes):
                            try:
                                f_r = scraper.get(href, timeout=5)
                                f_s = BeautifulSoup(f_r.text, 'html.parser')
                                iframe = f_s.find('iframe')
                                if iframe and iframe.get('src'): 
                                    href = iframe.get('src')
                                else:
                                    continue # Salta l'enllaç perquè és només text, no hi ha vídeo
                            except Exception as e:
                                continue
                        
                        c_name = "Veure"
                        if 'part 1' in btn_text or '1a part' in btn_text: c_name = '1a Part 🎬'
                        elif 'part 2' in btn_text or '2a part' in btn_text: c_name = '2a Part 🎬'
                        elif 'part 3' in btn_text or '3a part' in btn_text: c_name = '3a Part 🎬'
                        elif 'full' in btn_text or 'watch' in btn_text: c_name = 'Partit Sencer 🍿'
                        
                        channels.append({'channel_name': c_name, 'url': href, 'channel_code': 'us'})
                
                if channels:
                    matches.append({
                        'custom_sport_cat': 'NBA Replays 🏀', 'homeTeam': home, 'awayTeam': away, 
                        'start': "📼 REPLAY", 'start_raw': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), 
                        'status': 'vod', 'provider': 'NBA_REPLAY', 'channels': channels
                    })
            except Exception as e: 
                log(f"⚠ Ignorant error processant un replay: {e}")
        log(f"✅ S'han trobat {len(matches)} repeticions NBA netes.")
    except Exception as e: log(f"❌ Error NBA: {e}")
    return matches

def render_card(m):
    badge = '<span class="live-badge"><div class="live-dot"></div> EN VIU</span>' if m.get('status') == 'live' else ''
    btns = ""
    for ch in m.get('channels', []):
        b64 = base64.b64encode(ch["url"].encode()).decode()
        flag = f'<img src="https://flagcdn.com/20x15/{ch["channel_code"]}.png" class="flag-img" onerror="this.style.display=\'none\'"> ' if 'channel_code' in ch else ''
        btns += f'<div class="btn" data-link="{b64}" onclick="openLink(this)">{flag}{ch["channel_name"]}</div>'
    
    is_nba = m.get('custom_sport_cat') in ['NBA', 'NBA Replays 🏀']
    
    # Ara raspa bé el nom per als esports de Motor des de qualsevol de les claus
    nom_local = m.get("homeTeam") or m.get("title") or m.get("name") or m.get("event") or "Esdeveniment"
    nom_visitant = m.get("awayTeam") or ""
    
    home_logo_url = get_nba_logo(nom_local) if is_nba else m.get("homeLogo", "")
    away_logo_url = get_nba_logo(nom_visitant) if is_nba else m.get("awayLogo", "")
    
    h_logo = f'<img src="{home_logo_url}" class="team-logo" onerror="this.style.display=\'none\'">' if home_logo_url else ''
    a_logo = f'<img src="{away_logo_url}" class="team-logo" onerror="this.style.display=\'none\'">' if away_logo_url else ''
    
    vs_html = ' <span class="versus">vs</span> ' if nom_visitant else ''
    
    return f'<div class="card"><div class="header"><div class="meta"><span class="utc-time" data-ts="{m.get("start_raw", "")}">{m.get("start", "")}</span>{badge}</div><div class="match-info"><div class="teams">{h_logo} {nom_local}{vs_html}{nom_visitant} {a_logo}</div></div></div><div class="channels">{btns}</div></div>'

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        memory = load_memory()
        
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        
        cdn_events = []
        ppv_events = []
        livetv_events = []
        nba_replays = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            fut_cdn = executor.submit(fetch_cdn_live)
            fut_ppv = executor.submit(fetch_ppv_to, scraper)
            fut_livetv = executor.submit(fetch_livetv, scraper)
            fut_replays = executor.submit(fetch_nba_replays, scraper, list(memory.values()))
            
            cdn_events = fut_cdn.result()
            ppv_events = fut_ppv.result()
            livetv_events = fut_livetv.result()
            nba_replays = fut_replays.result()
        
        all_raw = list(memory.values()) + cdn_events + ppv_events + livetv_events + nba_replays
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
            
            is_nba_replay = m.get('provider') == 'NBA_REPLAY'
            is_soccer = m.get('custom_sport_cat') == 'Soccer'
            
            if not is_nba_replay and diff < -24.0:
                continue
                
            if not m.get('awayTeam') and m.get('custom_sport_cat') not in ['Motorsport', 'NFL', 'NBA Replays 🏀']:
                continue
            
            limit = 96.0 if is_nba_replay else 5.0
            if diff < limit:
                clean_mem[gid] = m
                
                display_limit = 2.25 if is_soccer else 4.0
                if is_nba_replay or diff < display_limit:
                    display.append(m)

        save_memory(clean_mem)
        
        cats = {}
        for m in display:
            c = m.get('custom_sport_cat', 'Other')
            if c not in cats: cats[c] = []
            cats[c].append(m)

        # -------------------------------------------------------------------
        # FILTRE D'IDIOMES I DIVERSITAT D'OPCIONS
        # -------------------------------------------------------------------
        banned_langs = {
            'se', 'gr', 'dk', 'pl', 'bg', 'cz', 'nl', 'ru', 'il', 'ua', 'un', 'de', 'he', 'ch', 'no',
            'rs', 'hr', 'ro', 'sa', 'ar', 'lt', 'tr', 'hu'
        }
        filtered_cats = {}
        
        for sport, matches_list in cats.items():
            valid_matches = []
            for m in matches_list:
                langs_dict = {}
                for ch in m.get('channels', []):
                    code = ch.get('channel_code', 'un')
                    
                    if code in banned_langs: continue
                    
                    if code not in langs_dict: langs_dict[code] = []
                    langs_dict[code].append(ch)
                    
                final_channels = []
                for code, ch_list in langs_dict.items():
                    picked = []
                    seen_types = set()
                    
                    for ch in ch_list:
                        cname = ch['channel_name'].lower()
                        ctype = "alieztv" if "alieztv" in cname else ("stream" if "stream" in cname else "other")
                        if ctype not in seen_types and len(picked) < 3:
                            picked.append(ch)
                            seen_types.add(ctype)
                            
                    for ch in ch_list:
                        if len(picked) < 3 and ch not in picked:
                            picked.append(ch)
                            
                    final_channels.extend(picked)
                    
                livetv_count = 1
                for ch in final_channels:
                    cname = ch.get('channel_name', '')
                    if cname.startswith("LiveTV ("):
                        base = "Opció"
                        if "AliezTV" in cname: base = "AliezTV"
                        elif "Live Stream" in cname: base = "Live Stream"
                        elif "BinTVs" in cname: base = "BinTVs"
                        ch['channel_name'] = f"LiveTV ({base} {livetv_count})"
                        livetv_count += 1
                
                if final_channels:
                    m['channels'] = final_channels
                    valid_matches.append(m)
            
            if valid_matches:
                filtered_cats[sport] = valid_matches

        # -------------------------------------------------------------------
        # GENERACIÓ HTML
        # -------------------------------------------------------------------
        navbar, content = '<a href="#" class="nav-btn active">Inici</a>', ""
        order_weights = {'Soccer': 1, 'NBA': 2, 'Tennis': 3, 'Motorsport': 4, 'NFL': 5, 'NBA Replays 🏀': 6}
        order = sorted(filtered_cats.keys(), key=lambda x: order_weights.get(x, 99))
        
        for sport in order:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title"><span class="sport-icon"></span>{nice}</div><div class="grid">'
            
            partits_ordenats = sorted(filtered_cats[sport], key=lambda x: (0 if x.get('status') == 'live' else 1, x.get('start_raw', '')))
            
            for m in partits_ordenats:
                content += render_card(m)
            content += "</div></div>"

        html_final = INTERNAL_TEMPLATE.replace('{{NAVBAR}}', navbar).replace('{{CONTENT}}', content).replace('{{DATE}}', datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
        print(html_final)

    except Exception as e: log(f"CRITICAL ERROR: {e}")

if __name__ == "__main__": 
    main()