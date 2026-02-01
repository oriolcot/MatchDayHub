import requests
import json
import os

API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

def main():
    try:
        print("Connectant a l'API...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(API_URL, headers=headers, timeout=10)
        data = response.json()
        matches = data.get("cdn-live-tv", {}).get("Soccer", [])
        
        # ESTRUCTURA HTML AMB ESTILS PER A IMATGES
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Futbol TV</title>
            <style>
                body { background-color: #121212; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }
                h1 { text-align: center; color: #4caf50; margin-bottom: 30px;}
                
                .match-card { 
                    background-color: #1e1e1e; 
                    margin-bottom: 25px; 
                    padding: 20px; 
                    border-radius: 15px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                }

                /* Capçalera del partit amb els escuts */
                .match-header {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 20px;
                    margin-bottom: 20px;
                    background: #252525;
                    padding: 10px;
                    border-radius: 10px;
                }
                .team-logo { width: 60px; height: 60px; object-fit: contain; }
                .vs-text { font-size: 1.2em; font-weight: bold; color: #888; }
                .match-info { text-align: center; color: #aaa; margin-bottom: 5px; font-size: 0.9em; }

                /* Graella de canals */
                .channels-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 10px;
                }

                .btn { 
                    display: flex; 
                    align-items: center; 
                    justify-content: start;
                    gap: 10px;
                    padding: 12px; 
                    background-color: #333; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    transition: background 0.2s;
                    border: 1px solid #444;
                }
                .btn:hover { background-color: #4caf50; border-color: #4caf50; color: white;}
                
                .channel-logo { width: 30px; height: 30px; object-fit: contain; }
                .channel-name { font-weight: 500; }
            </style>
        </head>
        <body>
            <h1>⚽ Partits en Directe</h1>
        """
        
        for match in matches:
            home = match.get('homeTeam', 'Home')
            away = match.get('awayTeam', 'Away')
            time = match.get('time', '')
            
            # Recuperem les imatges dels equips del JSON
            home_img = match.get('homeTeamIMG', '')
            away_img = match.get('awayTeamIMG', '')
            
            # Creem la targeta del partit amb els logos
            html_content += f"""
            <div class="match-card">
                <div class="match-info">⏱ {time}</div>
                <div class="match-header">
                    <img src="{home_img}" class="team-logo" onerror="this.style.display='none'">
                    <span class="vs-text">VS</span>
                    <img src="{away_img}" class="team-logo" onerror="this.style.display='none'">
                </div>
                <div style="text-align:center; font-size: 1.1em; font-weight:bold; margin-bottom:15px;">
                    {home} - {away}
                </div>
                
                <div class="channels-grid">
            """
            
            # Botons per a cada canal amb el seu logo
            for channel in match.get('channels', []):
                name = channel.get('channel_name', 'Canal')
                url = channel.get('url', '#')
                # Recuperem