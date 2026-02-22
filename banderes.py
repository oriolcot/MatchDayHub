import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
import urllib3

# Desactivem els avisos molestos de connexió insegura a la consola
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtenir_totes_les_banderes(url_principal):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    print(f"Buscant partits a: {url_principal}")
    try:
        # AFEGIT: verify=False
        response = requests.get(url_principal, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
    except Exception as e:
        print(f"Error al connectar a la pàgina principal: {e}")
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Busquem tots els enllaços que portin a la pàgina d'un partit
    enllacos = soup.find_all('a', href=re.compile(r'/eventinfo/\d+'))
    
    urls_partits = set()
    for a in enllacos:
        url_completa = urljoin(url_principal, a['href'])
        urls_partits.add(url_completa)
        
    print(f"S'han trobat {len(urls_partits)} partits únics. Començant l'extracció...")
    
    diccionari_mestre = {}
    
    for i, url in enumerate(urls_partits, 1):
        print(f"[{i}/{len(urls_partits)}] Analitzant: {url}")
        try:
            # AFEGIT: verify=False
            res_partit = requests.get(url, headers=headers, timeout=10, verify=False)
            soup_partit = BeautifulSoup(res_partit.text, 'html.parser')
            
            banderes = soup_partit.find_all('img', src=re.compile(r'/img/linkflag/(\d+)\.png'))
            
            for bandera in banderes:
                match = re.search(r'/img/linkflag/(\d+)\.png', bandera['src'])
                if match:
                    id_bandera = match.group(1)
                    
                    if id_bandera in diccionari_mestre:
                        continue
                        
                    idioma = bandera.get('title') or bandera.get('alt')
                    
                    if not idioma:
                        pare = bandera.find_parent('td')
                        if pare:
                            idioma = pare.get_text(strip=True)
                            
                    if idioma:
                        idioma_net = re.sub(r'[^a-zA-ZÀ-ÿ0-9\s]', '', idioma).strip()
                        diccionari_mestre[id_bandera] = idioma_net
                        print(f"   >>> Nova bandera trobada! ID: {id_bandera} -> {idioma_net}")
                        
        except Exception as e:
            print(f"   [!] Error analitzant aquest partit: {e}")
            
        time.sleep(1)
        
    return diccionari_mestre

# Prova d'executar-ho ara:
url_livetv = "https://livetv.sx/enx/" 
mapa_definitiu = obtenir_totes_les_banderes(url_livetv)

print("\n\n" + "="*40)
print("DICCIONARI FINAL EXTREU")
print("="*40)
print("{")
for k, v in sorted(mapa_definitiu.items(), key=lambda item: int(item[0])):
    print(f'    "{k}": "{v}",')
print("}")