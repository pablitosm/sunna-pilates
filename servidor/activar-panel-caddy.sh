#!/usr/bin/env bash
# Publica el panel en Caddy: añade /panel* y /api/registro (servidor/panel.caddy)
# al bloque de sunnapilates.es, con copia de seguridad, validación y recarga.
# Uso (desde el repo):  ssh 144.91.89.189 'bash -s' < servidor/activar-panel-caddy.sh
set -euo pipefail
CADDYFILE=/etc/caddy/Caddyfile

if grep -q "127.0.0.1:8084" "$CADDYFILE"; then
  echo "El panel ya está en el Caddyfile."
  exit 0
fi

COPIA="$CADDYFILE.antes-panel-$(date +%Y%m%d%H%M%S)"
cp "$CADDYFILE" "$COPIA"
echo "Copia de seguridad: $COPIA"

python3 - "$CADDYFILE" <<'PY'
import sys
ruta = sys.argv[1]
s = open(ruta).read()
ancla = "\t# Público: la página de login y lo que necesita para verse.\n"
if s.count(ancla) != 1:
    sys.exit("No encuentro el bloque público del Caddyfile: no toco nada.")
bloque = (
    "\t# Panel de administración (su propio login) y formulario público de la web.\n"
    "\thandle /panel* {\n\t\treverse_proxy 127.0.0.1:8084\n\t}\n"
    "\thandle /api/registro {\n\t\treverse_proxy 127.0.0.1:8084\n\t}\n\n"
)
open(ruta, "w").write(s.replace(ancla, bloque + ancla))
PY

if caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1; then
  systemctl reload caddy
  echo "Caddy recargado. Panel en https://sunnapilates.es/panel"
else
  cp "$COPIA" "$CADDYFILE"
  echo "La configuración no es válida: he restaurado la copia y no he recargado Caddy."
  exit 1
fi
