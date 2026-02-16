#!/bin/bash
python generator.py > index.html
git add index.html memoria_partits.json
git commit -m "Actualització manual ⚽🏀"
git push