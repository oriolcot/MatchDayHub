import cloudscraper
from bs4 import BeautifulSoup
import re

print("Iniciant Fase 2: Extracció d'enllaços de vídeo de LiveTV...")

LIVETV_DOMAINS = ["https://livetv.sx/enx", "https://livetv873.me/enx", "https://livetv740.me/enx"]

def obtenir_domini_actiu(scraper):
    for dom in LIVETV_DOMAINS:
        try:
            resp = scraper.get(dom, timeout=10)
            if resp.status_code == 200: return dom, resp.text
        except: pass
    return None, None

def test_livetv_fase2():
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    domini, html = obtenir_domini_actiu(scraper)
    if not html:
        print("❌ No s'ha pogut connectar.")
        return

    soup = BeautifulSoup(html, 'html.parser')
    partits_links = soup.find_all('a', href=re.compile(r'/eventinfo/'))
    
    resultats = []
    for a in partits_links:
        text = a.text.strip()
        if text and (' - ' in text or ' – ' in text):
            url_partit = a['href'] if a['href'].startswith('http') else f"{domini.replace('/enx', '')}{a['href']}"
            if url_partit not in [r['url'] for r in resultats]:
                resultats.append({'match': text, 'url': url_partit})

    if not resultats:
        print("No s'han trobat partits.")
        return

    print(f"✅ S'han trobat {len(resultats)} partits. Entrant als primers 3 per extreure els reproductors...\n")
    
    # Analitzem només els primers 3 partits per no trigar gaire
    for partit in resultats[:3]:
        print(f"⚽ Partit: {partit['match']}")
        try:
            r = scraper.get(partit['url'], timeout=10)
            
            # Busquem a l'HTML cru enllaços que continguin "webplayer", "embed", "alieztv" o "bintvs"
            # LiveTV acostuma a posar-los com href="//cdn.livetv873.me/webplayer..."
            links_player = re.findall(r'href="(//[^\s"<>]+(?:webplayer|embed|alieztv|bintvs)[^\s"<>]*)"', r.text)
            links_player += re.findall(r'href="(http[^\s"<>]+(?:webplayer|embed|alieztv|bintvs)[^\s"<>]*)"', r.text)
            
            links_player = list(set(links_player)) # Eliminem duplicats
            
            if links_player:
                for lp in links_player:
                    clean_link = lp if lp.startswith('http') else f"https:{lp}"
                    print(f"   🟢 REPRODUCTOR TROBAT: {clean_link}")
            else:
                print("   ⚠️ No s'han trobat enllaços al reproductor. Potser és massa d'hora o cal buscar amb una altra etiqueta.")
                
        except Exception as e:
            print(f"   ❌ Error descarregant la pàgina: {e}")
        print("-" * 60)

if __name__ == "__main__":
    test_livetv_fase2()