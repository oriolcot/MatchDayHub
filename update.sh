#!/bin/bash
echo "--- Iniciant actualització del MatchDayHub ---"
cd /home/ubuntu/MatchDayHub

# 1. Netejar qualsevol conflicte local (l'index.html que crea l'oracle)
git reset --hard origin/main

# 2. Descarregar l'última versió des de GitHub
git pull

# 3. Re-aplicar el parche de la CDN (si no el tens al codi de GitHub)
# sed -i "s/'browser': 'chrome'//g" generator.py

echo "--- Tot a lloc! Executant scraper per provar... ---"
/home/ubuntu/hub_env/bin/python generator.py > index.html
echo "✅ Web actualitzada manualment."
