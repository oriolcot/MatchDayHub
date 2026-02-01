import requests
import json
from datetime import datetime, timedelta

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

# Diccionari per traduir codis a Banderes
BANDERES = {
    "es": "🇪🇸 Espanya", "mx": "🇲🇽 Mèxic", "ar": "🇦🇷 Argentina",
    "gb": "🇬🇧 Anglaterra", "uk": "🇬🇧 Anglaterra", "us": "🇺🇸 USA", "ca": "🇨🇦 Canadà",
    "it": "🇮🇹 Itàlia", "fr": "🇫🇷 França", "de": "🇩🇪 Alemanya",
    "pt": "🇵🇹 Portugal", "br": "🇧🇷 Brasil",
    "nl": "🇳🇱 Països Baixos", "tr": "🇹🇷 Turquia", "pl": "🇵🇱 Polònia",
    "ru": "🇷🇺 Rússia", "ua": "🇺🇦 Ucraïna", "hr": "🇭🇷 Croàcia",
    "rs": "🇷🇸 Sèrbia", "gr": "🇬🇷 Grècia", "ro": "🇷🇴 Romania",
    "cz": "🇨🇿 Txèquia", "se": "🇸🇪 Suècia", "no": "🇳🇴 Noruega",
    "dk": "🇩🇰 Dinamarca", "fi": "🇫🇮 Finlàndia", "bg": "🇧🇬 Bulgària",
    "il": "🇮🇱 Israel"
}

def arreglar_hora(hora_str):
    try:
        # L'API dona l'hora en format HH:MM (Ex: 20:00)
        # Convertim text a objecte de temps
        data_hora = datetime.strptime(hora_str, "%H:%M")
        
        # SUMEM 1 HORA (Canvia l'1 per un 2 si fos horari d'estiu o calgués més)
        nova_hora = data_hora + timedelta(hours=1)
        
        # Tornem a convertir a text
        return nova_hora.strftime("%H:%M")
    except:
        return hora_str # Si falla, tornem l'hora original

def main():
    try:
        print("Connectant a l'API...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(API_URL, headers=headers, timeout=15)
        data = response.json()
        
        # Agafem només futbol (Soccer)
        matches = data.get("cdn-live-tv", {}).get("Soccer", [])
        
        content = "#EXTM3U\n"
        
        for match in matches:
            home = match.get('homeTeam', 'Home')
            away = match.get('awayTeam', 'Away')
            img = match.get('homeTeamIMG', '')
            
            # Arreglem l'hora
            hora_original = match.get('time', '00:00')
            hora_real = arreglar_hora(hora_original)
            
            # Busquem canals
            canals = match.get('channels', [])
            
            for channel in canals:
                name = channel.get('channel_name', 'Canal')
                url = channel.get('url', '')
                code = channel.get('channel_code', '').lower()
                
                # Busquem la bandera (si no la troba, posa el codi en majúscules)
                bandera = BANDERES.get(code, code.upper())
                
                # Creem el títol millorat: [21:00] Equip A vs Equip B | 🇪🇸 Canal
                titol_complet = f"[{hora_real}] {home} vs {away} | {bandera} {name}"
                
                # Afegim a la llista
                content += f'#EXTINF:-1 tvg-logo="{img}" group-title="Futbol Directe", {titol_complet}\n'
                content += f'{url}\n'

        # Guardem l'arxiu
        with open("llista.m3u", "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"ÈXIT: Llista generada amb banderes i hora corregida.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()