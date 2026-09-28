#!/usr/bin/env bash
# Despliega la web en el servidor (Apache 443 → Caddy 127.0.0.1:8082 → /var/www/sunnapilates).
# Uso: npm run deploy
set -euo pipefail
SERVIDOR="${SERVIDOR:-144.91.89.189}"
DESTINO="/var/www/sunnapilates/"

SITE_URL=https://sunnapilates.es npx astro build
rsync -az --delete dist/ "$SERVIDOR:$DESTINO"
echo "Publicado en https://sunnapilates.es"
