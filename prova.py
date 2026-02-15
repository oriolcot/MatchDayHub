import cloudscraper
import re
from bs4 import BeautifulSoup
from datetime import datetime

print("🌐 Iniciant prova FINAL versió PRO...")

# Diccionari de logos
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

def get_nba_logo(team_name):
    low_name = team_name.lower().strip()
    if low_name in NBA_LOGOS:
        return f"https://a.espncdn.com/i/teamlogos/nba/500/{NBA_LOGOS[low_name]}.png"
    return "❌ No s'ha trobat logo"

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

dominis_directes = ['filemoon', 'vidmoly', 'vk.com', 'ok.ru', 'streamtape', 'voe', 'uqload', 'dood', 'dailymotion']

try:
    print("📥 Llegint la portada de basketball-video.com...")
    resp = scraper.get("https://basketball-video.com/", timeout=15)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    partits_a_visitar = []
    any_passat = str(datetime.utcnow().year - 1)
    mes_actual = datetime.utcnow().month
    
    for a in soup.find_all('a', href=True):
        link = a['href']
        # Filtre WNBA i Videos
        if ('replay' in link.lower() or 'full-game' in link.lower()) and '/videos/' not in link.lower() and 'wnba' not in link.lower():
            # Filtre Any Passat
            if f"-{any_passat}-" in link and mes_actual > 1:
                continue
                
            if link.startswith("/"):
                link = "https://basketball-video.com" + link
                
            raw_title = link.split('/')[-1].replace('.html', '').replace('-', ' ').title()
            
            # EXTRACCIÓ DE DATA
            data_bonica = "Diferit"
            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s+(\d{4})', raw_title, re.IGNORECASE)
            if date_match:
                month = date_match.group(1)[:3]
                day = date_match.group(2)
                year = date_match.group(3)
                data_bonica = f"📼 {day} {month} {year}"
            
            # SEPARACIÓ D'EQUIPS
            equips_split = re.split(r'\s+Vs\.?\s+', raw_title, flags=re.IGNORECASE)
            home_t = ""
            away_t = ""
            
            if len(equips_split) >= 2:
                home_t = equips_split[0].strip()
                resta = equips_split[1]
                tall_away = re.split(r'\s+Full\s+Game|\s+Replay|\s+January|\s+February|\s+March|\s+April|\s+May|\s+June|\s+July|\s+August|\s+September|\s+October|\s+November|\s+December', resta, flags=re.IGNORECASE)
                away_t = tall_away[0].strip()
            else:
                clean_title = raw_title.split(' Full Game')[0].split(' Replay')[0].strip()
                home_t = clean_title[:40]
                away_t = ""
            
            if not any(p[1] == home_t for p in partits_a_visitar):
                partits_a_visitar.append((link, home_t, away_t, data_bonica))

    print(f"🔎 S'han trobat {len(partits_a_visitar)} PARTITS REALS (Sense WNBA ni zombis de l'any passat).")
    
    if not partits_a_visitar:
        print("❌ No hi ha partits per provar.")
        exit()
        
    print("⏳ Entrarem a 1 sol partit per veure com queda tot...\n")
    print("=" * 60)
    
    link, home_t, away_t, data_partit = partits_a_visitar[0]
    
    print(f"📅 DATA DETECTADA: {data_partit}")
    print(f"🏠 EQUIP LOCAL: '{home_t}' -> Logo: {get_nba_logo(home_t)}")
    print(f"✈️ EQUIP VISITANT: '{away_t}' -> Logo: {get_nba_logo(away_t)}")
    print(f"🔗 URL Article: {link}")
    
    art_resp = scraper.get(link, timeout=10)
    art_soup = BeautifulSoup(art_resp.text, 'html.parser')
    
    print("\n🔍 Buscant i traduint botons...")
    for a in art_soup.find_all('a', href=True):
        text_a = a.text.strip().lower()
        href = a['href']
        
        if ('watch' in text_a or 'part' in text_a or 'server' in text_a) and href.startswith('http') and 'basketball-video.com' not in href:
            
            nom_final = ""
            if 'watch' in text_a or 'server 1' in text_a or 'full game' in text_a:
                nom_final = "Partit Sencer 🍿"
            elif 'part 1' in text_a:
                nom_final = "1a Part 🎬"
            elif 'part 2' in text_a:
                nom_final = "2a Part 🎬"
            elif 'part 3' in text_a:
                nom_final = "3a Part 🎬"
            elif 'part 4' in text_a:
                nom_final = "4a Part 🎬"
            else:
                nom_final = a.text.strip() if a.text.strip() else "Veure Vídeo"

            print(f"\n   🔘 Botó Original: '{a.text.strip()}' ---> Ara serà: '{nom_final}'")
            
            final_url = ""
            if not any(d in href.lower() for d in dominis_directes):
                print(f"   ⚠️ Domini sospitós ({href}). Robant iframe...")
                try:
                    fake_resp = scraper.get(href, timeout=8)
                    fake_soup = BeautifulSoup(fake_resp.text, 'html.parser')
                    iframe_trobat = False
                    for iframe in fake_soup.find_all('iframe'):
                        src = iframe.get('src', '')
                        if src and 'http' in src and not any(x in src.lower() for x in ['facebook', 'twitter', 'google']):
                            final_url = src
                            print(f"   ✅ Iframe robat: {final_url}")
                            iframe_trobat = True
                            break
                    if not iframe_trobat:
                        print("   ❌ No hi ha iframe.")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            else:
                final_url = href
                print(f"   ✅ Domini OK. URL Directa: {final_url}")

    print("=" * 60)

except Exception as e:
    print(f"❌ Error global: {e}")