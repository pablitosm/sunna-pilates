#!/usr/bin/env bash
# Instala o actualiza el panel en el servidor. Se ejecuta en el servidor como root:
#   ssh SERVIDOR 'bash -s' < servidor/instalar-panel.sh
# (antes hay que copiar panel.py, panel.sql, sunnapilates-panel.service y el logo
#  src/assets/brand/sunna-tinta.svg como sunna-logo.svg a /tmp/sunnapilates-panel/).
# Es idempotente: si la base de datos o la configuración ya existen, no las toca.
set -euo pipefail
ORIGEN=/tmp/sunnapilates-panel
ENV=/etc/sunnapilates-panel.env

python3 -c "import psycopg2" 2>/dev/null || apt-get install -y python3-psycopg2

# Base de datos propia (sunna) con un rol propio (sunna_web), solo por 127.0.0.1.
if [ ! -f "$ENV" ]; then
  CLAVE_BD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sunna_web') THEN
    CREATE ROLE sunna_web LOGIN PASSWORD '$CLAVE_BD';
  ELSE
    ALTER ROLE sunna_web PASSWORD '$CLAVE_BD';
  END IF;
END \$\$;
SQL
  sudo -u postgres psql -Atc "SELECT 1 FROM pg_database WHERE datname = 'sunna'" | grep -q 1 \
    || sudo -u postgres createdb -O sunna_web sunna
  umask 077
  cat > "$ENV" <<CONF
PANEL_DSN="host=127.0.0.1 dbname=sunna user=sunna_web password=$CLAVE_BD"
PANEL_SECRETO=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
PANEL_COOKIE_SEGURA=1
PANEL_PUERTO=8084
CONF
fi

install -d /opt/sunnapilates-panel
install -m 644 "$ORIGEN/panel.py" "$ORIGEN/panel.sql" "$ORIGEN/sunna-logo.svg" /opt/sunnapilates-panel/
install -m 644 "$ORIGEN/sunnapilates-panel.service" /etc/systemd/system/

set -a; . "$ENV"; set +a
python3 /opt/sunnapilates-panel/panel.py esquema

systemctl daemon-reload
systemctl enable --now sunnapilates-panel
systemctl restart sunnapilates-panel
echo "Panel instalado. Crea el administrador con:"
echo "  set -a; . $ENV; set +a; python3 /opt/sunnapilates-panel/panel.py crear-admin USUARIO"
