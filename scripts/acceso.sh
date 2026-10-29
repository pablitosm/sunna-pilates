#!/usr/bin/env bash
# Abre o cierra la web con el login, sin tocar el resto del servidor.
# Uso: npm run web:abrir | npm run web:cerrar | npm run web:estado
#
# El Caddyfile importa /etc/caddy/sunna-acceso.caddy en el bloque de SUNNA; este script copia ahí
# servidor/acceso-abierto.caddy o servidor/acceso-cerrado.caddy, valida y recarga Caddy.
# La primera vez adapta el Caddyfile (con copia de seguridad). Si algo falla, lo deja como estaba.
set -euo pipefail
SERVIDOR="${SERVIDOR:-144.91.89.189}"
ACCION="${1:-}"
cd "$(dirname "$0")/.."

case "$ACCION" in
  abrir|cerrar|estado) ;;
  *) echo "Uso: $0 abrir|cerrar|estado" >&2; exit 1 ;;
esac

if [ "$ACCION" != estado ]; then
  scp -q servidor/acceso-abierto.caddy servidor/acceso-cerrado.caddy "$SERVIDOR:/etc/caddy/"
fi

ssh "$SERVIDOR" "bash -s -- $ACCION" <<'REMOTO'
set -euo pipefail
ACCION="$1"
CADDYFILE=/etc/caddy/Caddyfile
ACTIVO=/etc/caddy/sunna-acceso.caddy
IMPORT="import $ACTIVO"

if [ "$ACCION" = estado ]; then
  if ! grep -qF "$IMPORT" "$CADDYFILE"; then
    echo "Cerrada (Caddyfile aún sin adaptar; se adapta con el primer abrir/cerrar)."
  elif grep -q forward_auth "$ACTIVO" 2>/dev/null; then
    echo "Cerrada: hace falta login."
  else
    echo "Abierta al público."
  fi
  exit 0
fi

COPIA_CADDYFILE="$CADDYFILE.antes-acceso-$(date +%Y%m%d%H%M%S)"
cp "$CADDYFILE" "$COPIA_CADDYFILE"
COPIA_ACTIVO=""
if [ -f "$ACTIVO" ]; then
  COPIA_ACTIVO="$(mktemp)"
  cp "$ACTIVO" "$COPIA_ACTIVO"
fi

# Primera vez: el login y el noindex pasan del Caddyfile al archivo importado.
if ! grep -qF "$IMPORT" "$CADDYFILE"; then
  python3 - "$CADDYFILE" "$IMPORT" <<'PY'
import re, sys
ruta, importar = sys.argv[1], sys.argv[2]
s = open(ruta).read()
s, n1 = re.subn(r"\n\t[ \t]*forward_auth 127\.0\.0\.1:8083 \{\n[ \t]*uri /auth/check\n[ \t]*\}\n",
                "\n\t\t\t" + importar + "\n", s, count=1)
s, n2 = re.subn(r"\n\theader X-Robots-Tag \"noindex, nofollow\"\n", "\n", s, count=1)
if n1 != 1 or n2 != 1:
    sys.exit("No encuentro el forward_auth o el X-Robots-Tag de SUNNA en el Caddyfile: adáptalo a mano.")
open(ruta, "w").write(s)
PY
  echo "Caddyfile adaptado (copia: $COPIA_CADDYFILE)."
else
  rm "$COPIA_CADDYFILE"
  COPIA_CADDYFILE=""
fi

if [ "$ACCION" = abrir ]; then
  cp /etc/caddy/acceso-abierto.caddy "$ACTIVO"
else
  cp /etc/caddy/acceso-cerrado.caddy "$ACTIVO"
fi

if caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1; then
  systemctl reload caddy
  [ "$ACCION" = abrir ] && echo "Web abierta al público." || echo "Web cerrada: hace falta login."
else
  [ -n "$COPIA_CADDYFILE" ] && cp "$COPIA_CADDYFILE" "$CADDYFILE"
  if [ -n "$COPIA_ACTIVO" ]; then cp "$COPIA_ACTIVO" "$ACTIVO"; else rm -f "$ACTIVO"; fi
  echo "La configuración nueva no valida; lo he dejado como estaba. Detalle:"
  caddy validate --config "$CADDYFILE" --adapter caddyfile || true
  exit 1
fi
REMOTO
