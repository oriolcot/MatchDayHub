import requests
import json
import os
from datetime import datetime, timedelta

# MILLORA 8: Seguretat. Llegim la URL de les variables d'entorn
API_URL = os.environ.get("API_URL")
MEMORY_FILE = "memoria_partits.json"

def get_sport_name(api_key):
    names = {
        "Soccer": "FOOTBALL ⚽", 
        "NBA": "BASKETBALL (NBA) 🏀", 
        "NFL": "NFL 🏈",
        "NHL": "HOCKEY (NHL) 🏒", 
        "MLB": "BASEBALL ⚾", 
        "F1": "FORMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️", 
        "Tennis": "TENNIS 🎾", 
        "Boxing": "BOXING 🥊",
        "Rugby": "RUGBY 🏉",
        "Darts": "DARTS 🎯",
        "Snooker": "SNOOKER 🎱"
    }
    return names.get(api_key, api_key.upper())

def fix_time(time_str):
    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        # Ajusta això segons la teva zona horària (Ex: +1h per CET)
        new_time = time_obj + timedelta(hours=1)
        return new_time.strftime("%H:%M")
    except:
        return time_str

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def clean_old_events(events_dict):
    updated_events = {}
    now = datetime.utcnow()

    for game_id, match in events_dict.items():
        # 1. Filtre Status
        if match.get('status', '').lower() == 'finished':
            continue

        # MILLORA 6: Smart Cleaning per esport
        sport = match.get('custom_sport_cat', 'Other')
        # Límits en hores segons l'esport
        limit_hours = 4  # Per defecte
        if sport == 'Soccer': limit_hours = 2.5
        elif sport == 'NBA': limit_hours = 3.5
        elif sport == 'F1': limit_hours = 3
        
        # 2. Filtre de Temps Variable
        start_str = match.get('start') 
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                diff = now - start_dt
                
                # Si ha passat més del límit específic de l'esport
                if diff.total_seconds() > limit_hours * 3600:
                    continue
                
                # Seguretat: Si diu que és de fa 24h (error API), fora.
                if diff.total_seconds() < -24 * 3600:
                    continue

            except ValueError:
                pass 
        
        updated_events[game_id] = match
    
    return updated_events

def main():
    try:
        print("1. Loading memory...")
        memory = load_memory()
        
        print("2. Fetching API data...")
        if not API_URL:
            print("ERROR: No s'ha trobat l'API_URL a les variables d'entorn.")
            # Si vols provar en local sense secrets, descomenta la línia següent:
            # API_URL = "LA_TEVA_URL_AQUI"
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(API_URL, headers=headers, timeout=15)
            data_api = response.json()
            all_sports_api = data_api.get("cdn-live-tv", {})
        except Exception as e:
            print(f"API Error: {e}. Using memory only.")
            all_sports_api = {}

        # 3. MERGE DATA
        for sport, event_list in all_sports_api.items():
            if not isinstance(event_list, list): continue
            for match in event_list:
                game_id = match.get('gameID')
                if game_id:
                    # Si l'API diu que ja ha acabat, no l'actualitzem (o l'esborrem si hi era)
                    if match.get('status', '').lower() == 'finished':
                        if game_id in memory:
                            del memory[game_id]
                        continue
                        
                    match['custom_sport_cat'] = sport 
                    memory[game_id] = match

        # 4. CLEAN DATA
        clean_memory = clean_old_events(memory)
        save_memory(clean_memory)
        
        # 5. PREPARE FOR HTML
        events_by_cat = {}
        for game_id, match in clean_memory.items():
            cat = match.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat:
                events_by_cat[cat] = []
            events_by_cat[cat].append(match)

        # Sort by time
        for cat in events_by_cat:
            events_by_cat[cat].sort(key=lambda x: x.get('time', '00:00'))

        active_sports = list(events_by_cat.keys())

        # -----------------------------------------------------------
        # HTML GENERATION
        # -----------------------------------------------------------
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MatchDay Hub</title>
            <style>
                body { background-color: #1a1a1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; }
                
                /* Navbar */
                .navbar { background-color: #252525; padding: 15px; position: sticky; top: 0; z-index: 1000; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; border-bottom: 1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
                .nav-btn { text-decoration: none; color: #ccc; font-weight: 700; padding: 8px 16px; border-radius: 20px; background-color: #333; transition: all 0.2s; font-size: 0.85em; text-transform: uppercase; }
                .nav-btn:hover { background-color: #007aff; color: white; }
                
                .container { padding: 30px 15px; max-width: 1200px; margin: 0 auto; min-height: 80vh; }
                
                /* Titles */
                .sport-section { scroll-margin-top: 80px; margin-bottom: 50px; }
                .sport-title { font-size: 1.8em; color: #fff; display: flex; align-items: center; gap: 10px; margin-bottom: 20px; font-weight: 800; text-transform: uppercase; border-left: 5px solid #007aff; padding-left: 15px; }
                
                /* Grid */
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
                
                /* Cards */
                .card { background-color: #2a2a2a; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border: 1px solid #333; position: relative; transition: transform 0.2s; }
                .card:hover { transform: translateY(-3px); border-color: #555; }
                
                /* MILLORA 5: LIVE Styles */
                .live-badge { 
                    display: inline-block; background: #ff3b30; color: white; 
                    font-size: 0.7em; font-weight: bold; padding: 2px 8px; 
                    border-radius: 4px; margin-left: 10px; vertical-align: middle;
                    animation: pulse 2s infinite; 
                }
                @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
                
                .header { display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #444; }
                .time { font-size: 1.1em; font-weight: 800; color: #111; background: #fff; padding: 5px 10px; border-radius: 6px; }
                .teams { font-size: 1.1em; font-weight: 600; margin-left: 15px; color: #eee; line-height: 1.3; }
                
                .channels { display: flex; flex-wrap: wrap; gap: 8px; }
                .btn { display: flex; align-items: center; text-decoration: none; color: #ddd; background-color: #383838; padding: 8px 14px; border-radius: 8px; font-size: 0.85em; border: 1px solid #444; transition: background 0.2s; }
                .btn:hover { background-color: #007aff; color: white; border-color: #007aff; }
                .flag-img { width: 20px; height: 14px; margin-right: 8px; border-radius: 2px; }
                
                /* Footer */
                .footer { text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; color: #666; font-size: 0.8em; }
            </style>
        </head>
        <body>
            <div class="navbar">
        """
        
        if not active_sports:
             html_content += '<span style="color:#666;">OFFLINE</span>'
        else:
            for sport in active_sports:
                nice_name = get_sport_name(sport)
                html_content += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'

        html_content += '</div><div class="container">'

        if not active_sports:
            html_content += """
            <div style="text-align:center; margin-top:15vh;">
                <div style="font-size:3em;">😴</div>
                <h3 style="color:#888;">No live events</h3>
            </div>
            """

        for sport in active_sports:
            match_list = events_by_cat[sport]
            nice_name = get_sport_name(sport)
            
            html_content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice_name}</div><div class="grid">'

            for match in match_list:
                home = match.get('homeTeam', 'Home')
                away = match.get('awayTeam', 'Away')
                time = fix_time(match.get('time', '00:00'))
                
                # MILLORA 5: Detectar si és LIVE
                is_live = match.get('status', '').lower() == 'live'
                live_html = '<span class="live-badge">LIVE</span>' if is_live else ''
                
                html_content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time">{time}</span>{live_html}
                        <span class="teams">{home} vs {away}</span>
                    </div>
                    <div class="channels">
                """
                
                for channel in match.get('channels', []):
                    name = channel.get('channel_name', 'Channel')
                    url = channel.get('url', '#')
                    code = channel.get('channel_code', 'xx').lower()
                    flag = f"https://flagcdn.com/24x18/{code}.png"
                    
                    html_content += f"""<a href="{url}" class="btn"><img src="{flag}" class="flag-img" onerror="this.style.display='none'"> {name}</a>"""
                
                html_content += "</div></div>"
            
            html_content += '</div></div>'

        html_content += f"""
            </div>
            <div class="footer">
                Updated: {datetime.now().strftime('%H:%M')}
            </div>
        </body>
        </html>
        """

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("SUCCESS: Web generated.")

    except Exception as e:
        print(f"Error Global: {e}")

if __name__ == "__main__":
    main()