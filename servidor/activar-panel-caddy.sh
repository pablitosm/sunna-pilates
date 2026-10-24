#!/usr/bin/env bash
# Publica el panel en Caddy: añade /panel*, /api/registro y /api/evento (servidor/panel.caddy)
# al bloque de sunnapilates.es, con copia de seguridad, validación y recarga.
# Si el panel ya estaba, añade solo lo que falte (la ruta de la analítica).
# Uso (desde el repo):  ssh 144.91.89.189 'bash -s' < servidor/activar-panel-caddy.sh
set -euo pipefail
CADDYFILE=/etc/caddy/Caddyfile

if grep -q "handle /api/evento" "$CADDYFILE"; then
  echo "El panel y la analítica ya están en el Caddyfile."
  exit 0
fi

COPIA="$CADDYFILE.antes-panel-$(date +%Y%m%d%H%M%S)"
cp "$CADDYFILE" "$COPIA"
echo "Copia de seguridad: $COPIA"

python3 - "$CADDYFILE" <<'PY'
import sys
ruta = sys.argv[1]
s = open(ruta).read()
evento = "\thandle /api/evento {\n\t\treverse_proxy 127.0.0.1:8084\n\t}\n"
registro = "\thandle /api/registro {\n\t\treverse_proxy 127.0.0.1:8084\n\t}\n"
if s.count(registro) == 1:
    # El panel ya estaba: la analítica va justo después del formulario
    s = s.replace(registro, registro + evento)
else:
    ancla = "\t# Público: la página de login y lo que necesita para verse.\n"
    if s.count(ancla) != 1:
        sys.exit("No encuentro el bloque público del Caddyfile: no toco nada.")
    bloque = (
        "\t# Panel de administración (su propio login), formulario y analítica públicos de la web.\n"
        "\thandle /panel* {\n\t\treverse_proxy 127.0.0.1:8084\n\t}\n"
        + registro + evento + "\n"
    )
    s = s.replace(ancla, bloque + ancla)
open(ruta, "w").write(s)
PY

if caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1; then
  systemctl reload caddy
  echo "Caddy recargado. Panel en https://sunnapilates.es/panel"
else
  cp "$COPIA" "$CADDYFILE"
  echo "La configuración no es válida: he restaurado la copia y no he recargado Caddy."
  exit 1
fi
