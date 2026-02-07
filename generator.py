import json
import os
import sys
import base64
from datetime import datetime

MEMORY_FILE = "memoria_partits.json"

# --- PLANTILLA HTML (DISSENY FINAL - FOSC I MODERN) ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MatchDay Hub ⚽</title>
<style>
    :root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --live: #ef4444; }
    body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; }
    
    /* Navbar */
    .navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; margin-bottom: 20px; scrollbar-width: none; }
    .nav-btn { background: var(--card); color: var(--text); padding: 8px 16px; border-radius: 20px; text-decoration: none; border: 1px solid #334155; white-space: nowrap; font-size: 0.9rem; transition: 0.2s; }
    .nav-btn:hover { background: var(--accent); border-color: var(--accent); color: white; }
    
    /* Seccions */
    .sport-section { margin-bottom: 40px; }
    .sport-title { font-size: 1.5rem; font-weight: bold; margin-bottom: 15px; border-left: 4px solid var(--accent); padding-left: 10px; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Graella */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }
    
    /* Targeta */
    .card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); }
    
    .header { padding: 15px; background: rgba(0,0,0,0.2); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
    .utc-time { font-family: monospace; color: #94a3b8; font-size: 0.9rem; background: #0f172a; padding: 2px 6px; border-radius: 4px; }
    .live-badge { background: var(--live); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; animation: pulse 2s infinite; display: inline-block; margin-left: 5px; }
    .teams { font-weight: 600; text-align: right; flex-grow: 1; margin-left: 10px; font-size: 0.95rem; }
    
    /* Botons */
    .channels { padding: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
    .btn { 
        background: #334155; color: white; padding: 8px 12px; border-radius: 6px; 
        font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 8px; 
        transition: all 0.2s; user-select: none; border: 1px solid transparent; text-decoration: none;
    }
    .btn:hover { background: var(--accent); transform: translateY(-1px); border-color: #60a5fa; }
    .flag-img { width: 18px; height: 13px; object-fit: cover; border-radius: 2px; }

    .footer { margin-top: 50px; text-align: center; color: #64748b; font-size: 0.8rem; border-top: 1px solid #334155; padding-top: 20px; }
    
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
</style>
</head>
<body>
    <div class="navbar"></div>
    <div id="content"></div>
    <div class="footer">Última actualització: </div>

    <script>
        function openLink(el) { 
            try { 
                const raw = el.getAttribute('data-link');
                const url = atob(raw);
                window.open(url, '_blank'); 
            } catch(e){ console.error("Error link", e); } 
        }

        document.querySelectorAll('.utc-time').forEach(el => {
            const raw = el.getAttribute('data-ts');
            if(raw) {
                const d = new Date(raw.replace(' ', 'T')+'Z');
                el.innerText = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
            }
        });
    </script>
</body>
</html>"""

def get_sport_name(key):
    names = { 
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈", "F1": "FÓRMULA 1 🏎️", 
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉",
        "Darts": "DARTS 🎯", "Snooker": "SNOOKER 🎱", "Hockey": "HOQUEI 🏒", "Baseball": "BEISBOL ⚾"
    }
    return names.get(key, key.upper())

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        
        # 1. Carregar dades
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
        else:
            print("<h1>⚠️ Error: No s'ha trobat memoria_partits.json</h1>")
            return

        # 2. FILTRATGE INTEL·LIGENT
        matches = []
        now = datetime.utcnow()
        for m in memory.values():
            try:
                # A. FILTRE DE PROVEÏDOR: Si és PPV, l'ignorem
                if m.get('provider') == 'PPV': 
                    continue

                # B. FILTRE DE TEMPS: Futur o menys de 4h
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                diff_hours = (now - s_dt).total_seconds() / 3600
                
                if diff_hours < 4.0: 
                    matches.append(m)
            except: pass

        # 3. Organitzar per esport
        events_by_cat = {}
        for m in matches:
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            
            # Ordenar canals: Espanyol primer
            if 'channels' in m:
                m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        # 4. Generar HTML
        navbar_html = ""
        content_html = ""

        if not events_by_cat:
            content_html = "<div style='text-align:center; padding:50px; color:#94a3b8;'>😴 No hi ha partits (CDN) en viu ara mateix.</div>"

        for sport in sorted(events_by_cat.keys()):
            nice_name = get_sport_name(sport)
            navbar_html += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'
            
            # Ordenar per hora
            sport_matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content_html += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice_name}</div><div class="grid">'
            
            for m in sport_matches:
                utc = m.get('start')
                is_live = m.get('status', '').lower() == 'live'
                live_tag = '<span class="live-badge">EN VIU</span>' if is_live else ''
                
                btns_html = ""
                for ch in m.get('channels', []):
                    try: 
                        link_b64 = base64.b64encode(ch.get('url', '#').encode()).decode()
                    except: link_b64 = ""
                    
                    code = ch.get('channel_code', 'xx').lower()
                    flag = f"https://flagcdn.com/24x18/{code}.png"
                    name = ch.get('channel_name', 'Link')

                    btns_html += f"""
                    <div class="btn" data-link="{link_b64}" onclick="openLink(this)">
                        <img src="{flag}" class="flag-img" onerror="this.style.display='none'"> 
                        {name}
                    </div>"""

                content_html += f"""
                <div class="card">
                    <div class="header">
                        <div>
                            <span class="utc-time" data-ts="{utc}">{utc}</span>
                            {live_tag}
                        </div>
                        <span class="teams">{m['homeTeam']} <span style="color:#64748b">vs</span> {m['awayTeam']}</span>
                    </div>
                    <div class="channels">{btns_html}</div>
                </div>"""
            content_html += "</div></div>"

        # 5. Imprimir Resultat
        final = INTERNAL_TEMPLATE.replace('', navbar_html)
        final = final.replace('', content_html)
        final = final.replace('', datetime.now().strftime("%d/%m/%Y %H:%M UTC"))
        
        print(final)

    except Exception as e:
        print(f"<h1>CRITICAL ERROR</h1><pre>{e}</pre>")

if __name__ == "__main__":
    main()