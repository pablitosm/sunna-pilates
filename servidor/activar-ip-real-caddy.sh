#!/usr/bin/env bash
# Hace que Caddy se fíe de Apache para la IP del visitante (servidor/ip-real.caddy): añade
# `servers { trusted_proxies … }` a las opciones globales del Caddyfile, con copia de seguridad,
# validación y recarga. Si algo falla, deja el Caddyfile como estaba.
# Uso (desde el repo):  ssh 144.91.89.189 'bash -s' < servidor/activar-ip-real-caddy.sh
# Después, sube acceso.py y panel.py nuevos y reinicia sunnapilates-acceso y sunnapilates-panel.
set -euo pipefail
CADDYFILE=/etc/caddy/Caddyfile

if grep -q "trusted_proxies" "$CADDYFILE"; then
  echo "El Caddyfile ya tiene trusted_proxies: no toco nada."
  grep -n "trusted_proxies" "$CADDYFILE"
  exit 0
fi

COPIA="$CADDYFILE.antes-ip-real-$(date +%Y%m%d%H%M%S)"
cp "$CADDYFILE" "$COPIA"
echo "Copia de seguridad: $COPIA"

python3 - "$CADDYFILE" <<'PY'
import re, sys
ruta = sys.argv[1]
s = open(ruta).read()
bloque = "\tservers {\n\t\ttrusted_proxies static 127.0.0.1/32 ::1/128\n\t}\n"
# Opciones globales: un bloque { … } sin dirección al principio del archivo (tras comentarios)
m = re.match(r"((?:\s*#[^\n]*\n|\s*\n)*)\{\s*\n", s)
if m:
    if re.search(r"^\s*servers\b", s[m.end():s.find("\n}", m.end())], re.M):
        sys.exit("Ya hay un bloque servers en las opciones globales: añade trusted_proxies a mano.")
    s = s[:m.end()] + bloque + s[m.end():]
else:
    s = "{\n" + bloque + "}\n\n" + s
open(ruta, "w").write(s)
PY

if caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1; then
  systemctl reload caddy
  echo "Caddy recargado: ya conserva la IP real de los visitantes."
else
  cp "$COPIA" "$CADDYFILE"
  echo "El Caddyfile nuevo no valida; he dejado el anterior. Detalle:"
  caddy validate --config "$CADDYFILE" --adapter caddyfile || true
  exit 1
fi
