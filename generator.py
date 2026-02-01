import requests
import json
import os
from datetime import datetime, timedelta

# API URL
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"
MEMORY_FILE = "memoria_partits.json"

def get_sport_name(api_key):
    # Translation to English & Icons
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
        # Add 1 Hour (Adjust based on your timezone needs)
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
        # 1. Status Filter
        if match.get('status', '').lower() == 'finished':
            continue

        # 2. Time Filter (Updated to 4 HOURS)
        start_str = match.get('start') 
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                diff = now - start_dt
                
                # If started more than 4 hours ago (4 * 3600 seconds), remove it.
                if diff.total_seconds() > 4 * 3600:
                    continue
                
                # Safety: If it's from 24h ago (API error), remove it.
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
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(API_URL, headers=headers, timeout=15)
            data_api = response.json()
            all_sports_api = data_api.get("cdn-live-tv", {})
        except:
            print("API Error. Using memory only.")
            all_sports_api = {}

        # 3. MERGE DATA
        for sport, event_list in all_sports_api.items():
            if not isinstance(event_list, list): continue
            for match in event_list:
                game_id = match.get('gameID')
                if game_id:
                    match['custom_sport_cat'] = sport 
                    memory[game_id] = match

        # 4. CLEAN DATA (4h Limit)
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
        # HTML GENERATION (ENGLISH & PRO STYLE)
        # -----------------------------------------------------------
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MatchDay Hub</title>
            <style>
                body { background-color: #f4f6f8; color: #333; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif; margin: 0; padding: 0; }
                
                /* Navbar */
                .navbar { background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 15px; position: sticky; top: 0; z-index: 1000; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid #eaeaea; }
                .nav-btn { text-decoration: none; color: #555; font-weight: 700; padding: 10px 20px; border-radius: 30px; background-color: #f0f2f5; transition: all 0.2s ease; text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.5px; }
                .nav-btn:hover { background-color: #000; color: white; transform: translateY(-2px); }
                
                .container { padding: 40px 20px; max-width: 1200px; margin: 0 auto; min-height: 80vh; }
                
                /* Section Titles */
                .sport-section { scroll-margin-top: 100px; margin-bottom: 60px; }
                .sport-title { font-size: 2em; color: #111; display: flex; align-items: center; gap: 10px; margin-bottom: 25px; font-weight: 900; letter-spacing: -1px; text-transform: uppercase; }
                .sport-title::after { content: ""; flex-grow: 1; height: 2px; background: #eaeaea; margin-left: 20px; }

                /* Grid */
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }
                
                /* Cards */
                .card { background-color: #fff; border-radius: 16px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); border: 1px solid #fff; transition: transform 0.2s, box-shadow 0.2s; position: relative; overflow: hidden; }
                .card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.08); border-color: #eaeaea; }
                
                .header { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #f0f0f0; }
                .time { font-size: 1.1em; font-weight: 800; color: #fff; background: #000; padding: 6px 12px; border-radius: 8px; }
                .teams { font-size: 1.2em; font-weight: 700; margin-left: 15px; color: #222; line-height: 1.3; }
                
                .channels { display: flex; flex-wrap: wrap; gap: 10px; }
                .btn { display: flex; align-items: center; text-decoration: none; color: #333; background-color: #f9f9f9; padding: 10px 16px; border-radius: 10px; font-size: 0.9em; border: 1px solid #eee; font-weight: 600; transition: all 0.2s; }
                .btn:hover { background-color: #007aff; color: white; border-color: #007aff; box-shadow: 0 4px 10px rgba(0,122,255,0.3); }
                .flag-img { width: 22px; height: 16px; margin-right: 10px; border-radius: 3px; object-fit: cover; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                
                /* Footer / About */
                .footer { text-align: center; margin-top: 80px; padding-top: 40px; border-top: 1px solid #eaeaea; color: #888; }
                .about-box { max-width: 600px; margin: 0 auto 30px auto; background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); }
                .about-title { font-weight: 800; color: #000; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
                .about-text { font-size: 0.9em; line-height: 1.6; color: #666; }
                .update-badge { display: inline-block; background: #e1f5fe; color: #0288d1; padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="navbar">
        """
        
        if not active_sports:
             html_content += '<span style="color:#999; font-weight:600;">OFFLINE</span>'
        else:
            for sport in active_sports:
                nice_name = get_sport_name(sport)
                html_content += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'

        html_content += '</div><div class="container">'

        if not active_sports:
            html_content += """
            <div style="text-align:center; margin-top:15vh;">
                <div style="font-size:4em;">😴</div>
                <h2 style="color:#333; margin-top:20px;">No live events right now</h2>
                <p style="color:#888;">The system is scanning... check back later.</p>
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
                
                html_content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time">{time}</span>
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

        # FOOTER AMB "ABOUT"
        html_content += f"""
            </div>
            <div class="footer">
                <div class="about-box">
                    <div class="about-title">About MatchDay Hub</div>
                    <div class="about-text">
                        This is a personal, automated aggregator for live sports events. 
                        It runs on GitHub Actions, fetching real-time data and maintaining a 
                        persistent schedule for better reliability on Smart TVs.
                        <br><br>
                        <em>Developed with ❤️ for personal use.</em>
                    </div>
                    <div class="update-badge">Last Update: {datetime.now().strftime('%H:%M')}</div>
                </div>
            </div>
        </body>
        </html>
        """

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("SUCCESS: Web generated (English + 4h Limit + About).")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()