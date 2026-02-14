import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

print("🌐 Connectant a basketball-video.com...")
try:
    resp = requests.get("https://basketball-video.com/", headers=HEADERS, timeout=10)
    print(f"📩 Codi de resposta: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    enllacos = soup.find_all('a', href=True)
    
    trobats = 0
    print("\n🔍 Buscant enllaços...")
    for a in enllacos:
        href = a['href']
        # Busquem la paraula replay o full-game a la URL
        if 'replay' in href.lower() or 'full-game' in href.lower():
            print(f"🔗 TROBAT: {href}")
            trobats += 1
            
    print(f"\n✅ Total d'enllaços de partits: {trobats}")
    
    if trobats == 0:
        print("\n⚠️ AVÍS: No s'ha trobat res. Et mostro què ens ha retornat la web en realitat:")
        print("-" * 50)
        print(resp.text[:800]) # Mostrem les primeres línies del codi web
        print("-" * 50)

except Exception as e:
    print(f"❌ Error greu: {e}")