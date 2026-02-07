import requests
import json
import os
import sys
import base64
from datetime import datetime

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")
API_URL_PPV = os.environ.get("API_URL_PPV")
MEMORY_FILE = "memoria_partits.json"

# --- PLANTILLA HTML (ESTIL NET I MODERN) ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Futbol & Esports</title>
<style>
:root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --live: #ef4444; }
body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; }
.navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; scrollbar-width: none; }
.nav-btn { background: var(--card); color: var(--text); padding: 8px 16px; border-radius: 20px; text-decoration: none; border: 1px solid #334155; white-space: nowrap; font-size: 0.9rem; transition: 0.2s; }
.nav-btn:hover { background: var(--accent); border-color: var(--accent); }
.sport-title { font-size: 1.5rem; font-weight: bold; margin: 30px 0 15px 0; border-left: 4px solid var(--accent); padding-left: 10px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
.card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
.header { padding: 15px; background: rgba(0,0,0,0.2); display: flex; justify-content: space-between; align-items: center; }
.utc-time { font-family: monospace; color: #94a3b8; font-size: 0.9rem; }
.live-badge { background: var(--live); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; animation: pulse 2s infinite; }
.teams { font-weight: 600; text-align: right; flex-grow: 1; margin-left: 10px; }
.channels { padding: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
.btn { background: #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; color: white; display: flex; align-items: center; gap: 6px; text-decoration: none; transition: 0.2s; }
.btn:hover { background: var(--accent); }
.footer { margin-top: 40px; text-align: center; color: #64748b; font-size: 0.8rem; border-top: 1px solid #334155; padding-top: 20px; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
</style>
</head>
<body>
<div class="navbar"></div>
<div id="content"></div>
<div class="footer">Última actualització: </div>
<script>
function openLink(el) { try { window.open(atob(el.getAttribute('data-link')), '_blank'); } catch(e){} }
document.querySelectorAll('.utc-time').forEach(el => {
    const d = new Date(el.getAttribute('data-ts').replace(' ', 'T')+'Z');
    el.innerText = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
});
</script>
</body>
</html>"""

def log(msg):
    sys.stderr.write(f"[LOG] {msg}\n")

def get_sport_name(api_key):
    names = { "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈", "F1": "FÓRMULA 1 🏎️", "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾" }
    return names.get(api_key, api_key.upper())

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        
        # 1. Carreguem partits reals
        memory = load_memory()
        matches = []
        now = datetime.utcnow()
        
        # 2. Filtrem: Partits futurs o que hagin començat fa menys de 4 hores
        for m in memory.values():
            try:
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                # Si el partit és futur (s_dt > now) O és recent (diferència < 4 hores)
                diff = (now - s_dt).total_seconds()
                if diff < 4 * 3600: 
                    matches.append(m)
            except: pass

        # 3. Ordenem i Agrupem
        events_by_cat = {}
        for m in matches:
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        navbar_html = ""
        content_html = ""

        if not events_by_cat:
            content_html = "<div style='text-align:center; padding:50px; color:#94a3b8;'>😴 No hi ha partits en viu ara mateix.</div>"

        for sport in sorted(events_by_cat.keys()):
            nice = get_sport_name(sport)
            navbar_html += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            
            # Ordenar partits per hora
            sport_matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content_html += f'<div id="{sport}"><div class="sport-title">{nice}</div><div class="grid">'
            
            for m in sport_matches:
                utc = m.get('start')
                is_live = m.get('status', '').lower() == 'live'
                badges = '<span class="live-badge">LIVE</span> ' if is_live else ''
                
                btns_html = ""
                for ch in m.get('channels', []):
                    try: link = base64.b64encode(ch.get('url').encode()).decode()
                    except: link = ""
                    
                    code = ch.get('channel_code', 'xx').lower()
                    flag = "https://fav.farm/📺" if code == 'ppv' else f"https://flagcdn.com/24x18/{code}.png"
                    
                    btns_html += f"""
                    <div class="btn" data-link="{link}" onclick="openLink(this)">
                        <img src="{flag}" style="width:16px; border-radius:2px;"> {ch.get('channel_name')}
                    </div>"""

                content_html += f"""
                <div class="card">
                    <div class="header">
                        <span class="utc-time" data-ts="{utc}">--:--</span>
                        {badges}
                        <span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span>
                    </div>
                    <div class="channels">{btns_html}</div>
                </div>"""
            content_html += "</div></div>"

        # 4. Imprimim el resultat final (Sense DEBUG matches)
        final_html = INTERNAL_TEMPLATE.replace('', navbar_html)
        final_html = final_html.replace('', content_html)
        final_html = final_html.replace('', datetime.now().strftime("%d/%m/%Y %H:%M UTC"))

        print(final_html)

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        print("<h1>Error generant la web</h1>")

if __name__ == "__main__":
    main()